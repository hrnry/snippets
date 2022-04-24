#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from selenium.webdriver.firefox.firefox_binary import FirefoxBinary


import os, re, subprocess, sys, textwrap, signal
import os.path

## sanitize input string
def sanitize(s):
    s = re.sub(r'[\s\|\[\]\\/:;,.?\'"`~^$%&*+()={}<>]', '_', s)
    s = re.sub(r'_+', '_', s)
    s = s.lstrip('-')
    return 'OUTPUT' if len(s) == 0 else s

## make inject JS
def mkInjectJS(element_id):
    return textwrap.dedent('''
      (function (){
        "use strict";
        let elm = document.createElement("div");
        elm.id = "''' + element_id + '''";
        //elm.style.display = "none";//Can't use "text_to_be_present_in_element" and "find_element_by_*(*).text" when "style.display" is "none"
        document.body.appendChild(elm);
        const xhrOpen = window.XMLHttpRequest.prototype.open;
        window.XMLHttpRequest.prototype.open = function (method, url, async, user, pass){
          elm.innerHTML += url + " ";
          return xhrOpen.apply(this, arguments);
        };
      })();
    ''').strip()


if __name__ == '__main__':
    args = sys.argv
    if len(args) != 2:
        print('e.g.: ' + os.path.basename(args[0]) + ' https://tver.jp/series/sr5rbukl21')
        sys.exit(1)

    print('[*] Start')
    target_url = args[1]
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--safe-mode')
    opts.add_argument('--new-instance')
    opts.add_argument('--no-remote')

    #driver = webdriver.Firefox(executable_path='geckodriver', options=opts)
    bin = FirefoxBinary(os.path.expanduser('~') + '/Development/firefox-dev/firefox')
    with webdriver.Firefox(firefox_binary=bin, options=opts) as driver:

        driver.implicitly_wait(15)
        driver.get(target_url)
        title = driver.title
        print('[*] PageTitle: ' + title)
        ua = driver.execute_script('return navigator.userAgent')

        elm_id = 'div_xhr_data'
        driver.execute_script(mkInjectJS(elm_id))

########## TVer
        def elm_click(xpath: str):
            try:
                print(f'[*] {xpath}')
                #WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                print('[.] click')
                driver.find_element_by_xpath(xpath).click()
            except:
                print('[!] Except')
                driver.close()
                driver.quit()
                sys.exit(1)

        # 利用規約・プライバシーポリシー [同意する]
        elm_click('//button[contains(@class, "terms-modal_done__")]')

        #driver.execute_script(mkInjectJS(elm_id))

        # アンケート [スキップ]
        elm_click('//button[contains(@class, "questionnaire-modal_skip__")]')

        # 右カラム エピソード
        if target_url.startswith('https://tver.jp/series/'):
            elm_click('//div[contains(@class, "episode-pattern-b-layout_mainTitle__")]')
            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located)
            print(f'[*] {driver.current_url}')
        title = driver.title

        try:
            xpath = '//span[starts-with(@class, "titles_title__")]'
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, xpath)))
            title = driver.find_element_by_xpath(xpath).text
            title = sanitize(title)
            print(f'[*] title: {title}')
            #driver.switch_to.default_content()
        except TimeoutException:
            print('[!] TimeoutException')

        m3u8 = 'master.m3u8'
        isFound = False
        print(f'[.] Waiting {m3u8} ...')
        try:
            WebDriverWait(driver, 15).until(EC.text_to_be_present_in_element((By.ID, elm_id), m3u8))
            xhr_urls = driver.find_element_by_id(elm_id).get_attribute('textContent')
            for url in xhr_urls.split():
                if url.find(m3u8) != -1:
                    isFound = True
                    break
        except TimeoutException:
            print(f'[!] TimeoutException: {m3u8} not found')
        finally:
            print('[*] WebDriver Quit')
            driver.close()
            driver.quit()
##########

    if isFound:
        cwd_dir = '/tmp'
        print(f'[*] {cwd_dir}')
        cmd = ['curl', '-sS', '--user-agent', ua, '-o', m3u8, url]
        print(f"[+] m3u8: {' '.join(cmd)}")
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, cwd=cwd_dir)
        cmd = ['ffmpeg', '-y', '-protocol_whitelist', 'file,http,https,tcp,tls,crypto', '-i', m3u8, '-movflags', 'faststart', '-c', 'copy', title + '.mp4']
        # ffmpeg -user-agent
        print(f"[+] mp4: {' '.join(cmd)}")
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=cwd_dir)
        print('[*] Done')
