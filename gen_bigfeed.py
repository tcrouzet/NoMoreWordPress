"""Changer site.yml si mise à jour template"""

import os, sys

import tools.tools
import tools.db
import tools.web
import tools.logs
import tools.feed


sys.stdout = tools.logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

os.system('clear')

config = tools.tools.site_yml('site.yml')

db = tools.db.Db(config)
web = tools.web.Web(config, db)
feed = tools.feed.Feed(config, web)

#Blog feed
exclude = ("invisible", "carnets", "velo", "retroblogging","ecriture")
posts = db.get_blog_posts(exclude)
feed.builder(posts,"blog-all", "Derniers articles de Thierry Crouzet", None)
print("Blog done")


#TAGS
tags = db.get_tags()
for tag in tags:
    tag = web.supercharge_tag(tag)
    if tag['tag']=="carnets":
        feed.builder(tag['posts'],"carnet-de-route-all", "Derniers carnets de Thierry Crouzet", None)
    if tag['tag']=="velo":
        feed.builder(tag['posts'],"borntobike-all", "Derniers articles sur le vélo de Thierry Crouzet", None)
    if tag['tag']=="ecriture":
        feed.builder(tag['posts'],"ecriture-all", "Derniers textes en construction de Thierry Crouzet", None)
