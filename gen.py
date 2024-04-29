import yaml
import os, sys
from tqdm import tqdm
import tools.db
import tools.layout
import tools.web
import tools.logs
import tools.sitemap
import tools.feed
import json
from datetime import datetime

sys.stdout = tools.logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

os.system('clear')

with open('site.yml', 'r') as file:
    config = yaml.safe_load(file)

db = tools.db.Db(config)
web = tools.web.Web(config, db)
layout = tools.layout.Layout(config)
sitemap = tools.sitemap.Sitemap(config)
feed = tools.feed.Feed(config, web)

if config['build'] == 1:
    #Load new posts only
    new_posts = db.db_builder(config['vault'],False)
elif config['build'] == 2:
     #Rebuild all
    new_posts = db.db_builder(config['vault'],True)
print(new_posts, "new posts")

#db.list_posts_updated()

#POSTS
posts = db.get_posts_updated()
total = len(posts)
pbar = tqdm(total=total, desc='Posts:')
used_tags = []
for post in posts:
    #db.list_object(post)
    used_tags.extend( json.loads(post['tags']))
    supercharged = web.supercharge_post(post)
    #print(supercharged)
    if not supercharged:
        continue
    layout.single_gen( supercharged )
    db.updated(post)
    pbar.update(1)
pbar.close()
db.db_commit()
print(total, "posts updated")
used_tags = list(set(used_tags))


#SITEMAP POSTS
if new_posts>0:
    sitemap.open("sitemap-posts")
    posts = db.get_all_posts()
    for post in posts:
        supercharge = web.supercharge_post(post)
        sitemap.add_post( supercharge )
        if not supercharged:
            print("need to delete", web.url(post))

    sitemap.save()
    print("Sitemap posts done")


#SERIES
sitemap.open("sitemap-main")
exclude = ("invisible","iacontent","book","page","le_jardin_de_leternite")
tags = db.get_tags("p.pub_date DESC",exclude)
series = {
    "tag": "series",
    "pub_update": tags[0]['pub_update'],
    "thumb_path": tags[0]['thumb_path'],
    "thumb_legend": tags[0]['thumb_legend'],
    "post_md": "series/",
    "url": "series/",
}
series = web.supercharge_tag(series,tags)
layout.tag_gen( series )
sitemap.add_post( series )
print("Series done")


#BLOG
exclude = ("invisible", "carnets", "velo", "retroblogging")
posts = db.get_blog_posts(exclude)
#tools.db.list_object(posts)
series = {
    "tag": "blog",
    "pub_update": posts[0]['pub_update'],
    "thumb_path": posts[0]['thumb_path'],
    "thumb_legend": posts[0]['thumb_legend'],
    "post_md": "blog/",
    "url": "blog/",
}
blog = web.supercharge_tag(series, posts)
layout.tag_gen( blog )
sitemap.add_post(blog)
feed.builder(posts,"feed", "Derniers articles de Thierry Crouzet")
print("Blog done")


#HOME
last_post=posts[0]
last_carnet = db.get_posts_by_tag("carnets", 1)
last_bile = db.get_posts_by_tag("velo", 1)
home = web.supercharge_post(last_post, False)
home['carnet'] = web.supercharge_post(last_carnet, False)
home['bike'] = web.supercharge_post(last_bile, False)
layout.home_gen( home )
sitemap.add_post({"url": "index.html", "pub_update_str": home['pub_update_str'], "thumb": home["thumb"]["url"] })
print("Home done")
sitemap.add_page("archives/index.html", home['pub_update_str'])
sitemap.save()


#TAGS
sitemap.open("sitemap-tags")
tags = db.get_tags()
total = len(tags)
pbar = tqdm(total=total, desc='Tags:')
for tag in tags:
    tag = web.supercharge_tag(tag)
    sitemap.add_post(tag)
    if tag['tag'] in used_tags:

        if tag['tag']=="carnets":
            feed.builder(tag['posts'],"carnet-de-route", "Derniers carnets de Thierry Crouzet")
        if tag['tag']=="velo":
            feed.builder(tag['posts'],"borntobike", "Derniers articles sur le vélo de Thierry Crouzet")
        if tag['tag']=="ecriture":
            feed.builder(tag['posts'],"ecriture", "Derniers textes en construction de Thierry Crouzet")
        if tag['tag']=="mailing":
            feed.builder(tag['posts'],"mailing", "Autopromotion de Thierry Crouzet")

        layout.tag_gen(tag)

    pbar.update(1)
pbar.close()
sitemap.save()
print(total, "tags updated")


#YEARS
sitemap.open("sitemap-years")
years_archive = ""
exclude = ("invisible","book","page")
years = db.get_years()
for iy, year in enumerate(years):

    posts = db.get_posts_by_year(year, exclude)
    if posts:

        if iy<len(years)-1:
            prev_year =  years[iy+1]
        else:
            prev_year =  years[0]

        if iy>0:
            next_year =  years[iy-1]
        else:
            next_year =  years[-1]

        series = {
            "tag": str(year),
            "title_date": f'<a href="/{str(prev_year)}">&lt;</a> {str(year)} <a href="/{str(next_year)}">&gt;</a>',
            "pub_update": posts[0]['pub_update'],
            "thumb_path": posts[0]['thumb_path'],
            "thumb_legend": posts[0]['thumb_legend'],
            "post_md": f"{str(year)}/",
            "url": f"{str(year)}/",
        }
        superyear= web.supercharge_tag(series, posts)
        sitemap.add_post(superyear)
        layout.tag_gen( superyear )
        years_archive += f'<p><a href="{str(year)}/">{year}</a></p>'

sitemap.save()
print("Years done")


#ARCHIVES
posts_archive = ""
exclude = ("invisible")
posts = db.get_blog_posts(exclude)
for post in posts:
    url = web.url(post)
    posts_archive += f'<p><a href="{url}">' + datetime.fromtimestamp(post['pub_date']).strftime('%Y/%m/%d').replace('/0','/') + f' {post['title']}</a></p>'
layout.archives_gen( f"<h3>Années</h3>{years_archive}<h3>Billets</h3>{posts_archive}" )
print("Archives done")

#ERROR
layout.e404_gen()

#END SITEMAP
sitemap.save_index()
