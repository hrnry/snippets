#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.options import Options
from time import sleep
import requests
import re
import os
import sys

if __name__ == '__main__':
    args = sys.argv
    if len(args) != 2:
        print('e.g.: ' + os.path.basename(args[0]) + ' https://abema.tv/video/episode/171-21_s1_p1')
        sys.exit(1)
    target = re.sub('.*/', '', args[1])

    bin = FirefoxBinary(os.path.expanduser('~') + '/Development/firefox-dev/firefox')
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--safe-mode')
    opts.add_argument('--new-instance')
    opts.add_argument('--no-remote')

    KEY_FILE = '/tmp/key.bin'
    M3U8_FILE = '/tmp/playlist.m3u8'

    with webdriver.Firefox(firefox_binary=bin, options=opts) as driver:
        #driver.get("https://abema.tv/now-on-air/abema-news")
        driver.get(f"https://abema.tv/video/episode/{target}")

        ua = driver.execute_script('return navigator.userAgent;')
        title = driver.title
        print(f"# PageTitle: {title}")
        xpath = '//div[@class="com-video-EpisodeTitleBlock"]/h1[@class="com-video-EpisodeTitleBlock__title"]'
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
            title = driver.find_element_by_xpath(xpath).text
        except TimeoutException:
            print('# TimeoutException')
        title = re.sub(r'[\s\|\[\]\\/:;,.?\'"`~^$%&*+()={}<>]', '_', title)
        title = re.sub(r'_+', '_', title)
        title = title.lstrip('-')
        print(f"# Title: {title}")
        sleep(2)
        #pl = requests.get(f"https://ds-vod-abematv.akamaized.net/program/{target}/playlist.m3u8").text
        #pl = requests.get('https://linear-abematv.akamaized.net/channel/abema-news/1080/playlist.m3u8').text
        pl = requests.get(f"https://ds-vod-abematv.akamaized.net/program/{target}/1080/playlist.m3u8").text

        key_url = re.search(u'URI="([^"]*)"', pl).group(1)
        #print(f"### key_url: {key_url}")
        driver.execute_script('''
            var xhr = new XMLHttpRequest();
            xhr.onreadystatechange = function() {
                if (xhr.readyState == 4 && xhr.status == 200) {
                    window.key = new Uint8Array(xhr.response);
                }
            }
            xhr.open("GET", "%s");
            xhr.send();
        ''' % key_url)
        sleep(8)
        key = driver.execute_script('return window.key;')

        driver.close()
        driver.quit()

    k = []
    for i in range(len(key)):
        k.append(key[str(i)])
    print(f"### key({KEY_FILE}): " + ','.join([str(i) for i in k]))
    with open(KEY_FILE, 'wb') as f:
        f.write(bytes(k))

    mod_pl = re.sub('URI=.*?,', f'URI="{KEY_FILE}",', pl)
    mod_pl = re.sub('^/', 'https://ds-vod-abematv.akamaized.net/', mod_pl, flags=re.MULTILINE)
    with open(M3U8_FILE, 'w') as f:
        f.write(mod_pl)

    ff_opts = '-hide_banner'
    ff_opts += ' -loglevel warning'
    #ff_opts += f" -headers 'User-Agent: \"{ua}\"'"
    ff_opts += ' -protocol_whitelist file,http,https,tcp,tls,crypto -allowed_extensions ALL'

    cmd = f"ffplay {ff_opts} -i {M3U8_FILE}"
    #print(cmd)
    #os.system(cmd)

    cmd = f"ffmpeg {ff_opts} -i {M3U8_FILE} -movflags faststart -c copy '{title}.mp4'"
    print(cmd)
