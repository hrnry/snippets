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
        print('e.g.: ' + os.path.basename(args[0]) + ' https://tver.jp/corner/f0063833')
        #print('e.g.: ' + os.path.basename(args[0]) + ' https://tver.jp/corner/f0045834')
        #print('e.g.: ' + args[0] + ' https://tver.jp/lp/c0498920')
        #print('      ' + args[0] + ' https://tver.jp/episode/54356614')
        sys.exit(1)

    print('# Start')
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
        print('# PageTitle: ' + title)
        ua = driver.execute_script('return navigator.userAgent')

        elm_id = 'div_xhr_data'
        driver.execute_script(mkInjectJS(elm_id))

########## TVer
        try:
            xpath = '//div[@id="end-alert"]/div/a'
            print('# end-alert: ' + driver.find_element_by_xpath(xpath).get_attribute('href'))
            driver.find_element_by_xpath(xpath).click()
            driver.execute_script(mkInjectJS(elm_id))
        except:
            pass

        try:
            xpath = '//section[@class="video-section"]/div[@class="title"]/div[@class="inner"]'
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
            title = driver.find_element_by_xpath(xpath + '/h1').text
            #summary = driver.find_element_by_xpath(xpath + '/p/span[@class="summary"]').text
            summary = driver.find_element_by_xpath(xpath + '/p/span[@class="summary "]').text
            title = sanitize(title + '_' + summary)
            xpath = '//div[@id="enquete"]/div[@class="eqform"]/iframe'
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
            driver.switch_to.frame(driver.find_element_by_xpath(xpath))
            xpath = '//div[@id="container"]/div[@class="exit"]/a[@class="cancel"]'
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
            driver.find_element_by_xpath(xpath).click()
            driver.switch_to.default_content()
        except TimeoutException:
            print('# TimeoutException: Close Enquete')

        m3u8 = 'master.m3u8'
        isFound = False
        print('# Waiting ' + m3u8 + '  ...')
        try:
            WebDriverWait(driver, 15).until(EC.text_to_be_present_in_element((By.ID, elm_id), m3u8))
            xhr_urls = driver.find_element_by_id(elm_id).get_attribute('textContent')
            for url in xhr_urls.split():
                if url.find(m3u8) != -1:
                    isFound = True
                    break
        except TimeoutException:
            print('# TimeoutException: ' + m3u8 + ' not found')
        finally:
            print('# Quit')
            driver.close()
            driver.quit()
## FIXME: sys:1: ResourceWarning: unclosed file <_io.BufferedWriter name='/dev/null'>
##########

    if isFound:
        cwd_dir = '/tmp'
        cmd = ['curl', '-sS', '--user-agent', ua, '-o', m3u8, url]
        print(cwd_dir, cmd)
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, cwd=cwd_dir)
        cmd = ['ffmpeg', '-y', '-protocol_whitelist', 'file,http,https,tcp,tls,crypto', '-i', m3u8, '-movflags', 'faststart', '-c', 'copy', title + '.mp4']
        # ffmpeg -user-agent
        print(cwd_dir, cmd)
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=cwd_dir)
        print('# Done')
