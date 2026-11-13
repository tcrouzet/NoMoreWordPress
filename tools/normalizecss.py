# https://github.com/sindresorhus/modern-normalize

import requests
import csscompressor
import os

os.system('clear')

def update_normalize_css(url):
    response = requests.get(url)
    if response.status_code == 200:
        compressed_css = csscompressor.compress(response.text)
        print(compressed_css)
    else:
        print("Failed to download the file.")

url = "https://raw.githubusercontent.com/sindresorhus/modern-normalize/main/modern-normalize.css"
update_normalize_css(url)