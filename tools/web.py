import datetime
import os

def url(post):
    date = datetime.datetime.fromtimestamp(post['pub_date'])
    path = date.strftime("/%Y/%m/%d")
    file_name_without_extension = os.path.splitext(os.path.basename(post['path_md']))[0]
    url = '/'.join([path.strip('/'), file_name_without_extension]) + "/"
    return url
