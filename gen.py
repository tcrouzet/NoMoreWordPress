"""Changer site.yml si mise à jour template"""

import os, sys
from datetime import datetime

import tools.tools
import tools.db
import tools.layout
import tools.web
import tools.logs
import tools.sitemap
import tools.feed


#Force updating home screen
new_home_template = True

sys.stdout = tools.logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

os.system('clear')

config = tools.tools.site_yml('site.yml')
# print(config)
# exit()

version = int(config['version'])
db = tools.db.Db(config)
web = tools.web.Web(config, db)
layout = tools.layout.Layout(config)
sitemap = tools.sitemap.Sitemap(config)
feed = tools.feed.Feed(config, web)

if config['build'] == 1:
    #Load new posts only
    db.db_builder(config['vault'],False)
elif config['build'] == 2:
     #Rebuild all
    db.db_builder(config['vault'],True)
print(db.new_posts, "new posts")
print(db.updated_posts, "updated posts")


#POSTS
posts = db.get_posts_updated()
total = len(posts)
if total >0:
    pbar = tools.logs.DualOutput.dual_tqdm(total=total, desc='Posts:')
    for post in posts:
        supercharged = web.supercharge_post(post)
        if not supercharged:
            continue
        layout.single_gen( supercharged )
        db.updated(post)
        pbar.update(1)
    pbar.close()
    db.db_commit()


#SITEMAP POSTS
if db.new_posts > 0:
    sitemap.open("sitemap-posts")
    posts = db.get_all_posts()
    pbar = tools.logs.DualOutput.dual_tqdm(total=len(posts), desc='Sitemap-posts:')
    for post in posts:
        supercharge = web.supercharge_post(post)
        sitemap.add_post( supercharge )
        if not supercharged:
            print("need to delete", web.url(post))
        pbar.update(1)
    sitemap.save()
    pbar.close()
    print("Sitemap posts done")


sitemap.open("sitemap-main")

#SERIES
if len(db.used_tags) > 0:
    exclude = ("invisible","iacontent","book","page","le_jardin_de_leternite")
    tags = db.get_tags("p.pub_date DESC",exclude)
    series = {
        "tag": "series",
        "pub_update": tags[0]['pub_update'],
        "thumb_path": tags[0]['thumb_path'],
        "thumb_legend": tags[0]['thumb_legend'],
        "post_md": tags[0]['post_md'],
        "url": "series/"
    }
    series = web.supercharge_tag(series, tags)
    layout.tag_gen( series )
    sitemap.add_post( series )
    print("Series done")


#BLOG
if  db.new_posts >0 or db.updated_posts > 0:
    exclude = tuple(config['home_exclude'])
    posts = db.get_blog_posts(exclude)
    first_post = dict(posts[0])
    series = {
        "tag": "blog",
        "pub_update": first_post['pub_update'],
        "thumb_path": first_post['thumb_path'],
        "thumb_legend": first_post['thumb_legend'],
        "post_md": first_post['path_md'],
        "url": "blog/",
    }
    blog = web.supercharge_tag(series, posts)
    layout.tag_gen( blog )
    sitemap.add_post( blog )
    feed.builder(posts,"blog", "Derniers articles de Thierry Crouzet")
    print("Blog done")


#HOME
if  db.new_posts >0 or db.updated_posts > 0 or new_home_template:
    if posts:
        last_post=posts[0]
        last_carnet = db.get_posts_by_tag("carnets", 1)
        last_bike = db.get_posts_by_tag("velo", 1)
        last_digest = db.get_posts_by_tag("digest", 1)

        home = {}
        home['digressions'] = web.supercharge_post(last_post, False)
        home['carnet'] = web.supercharge_post(last_carnet, False)
        home['bike'] = web.supercharge_post(last_bike, False)
        home['digest'] = web.supercharge_post(last_digest, False)

        home['canonical'] = config['domain']
        home['description'] = config['description']
        home['title'] = config['home_title']
        home['pub_update_str'] = home['digressions']['pub_update_str']
        home['pub_update'] = home['digressions']['pub_update']
        home['thumb'] = home['digressions']['thumb']
        home['thumb_path'] = home['digressions']['thumb_path']
        home['thumb_legend'] = home['digressions']['thumb_legend']
        home['on_home'] = 1

        layout.home_gen( home )
        sitemap.add_post({"url": "index.html", "pub_update_str": home['pub_update_str'], "thumb": home["thumb"]["url"] })
        print("Home done")


sitemap.add_page("archives/index.html")
sitemap.save(4)


#MAIN FEED
if  db.new_posts >0 or db.updated_posts > 0:
    posts = db.get_all_posts()
    feed.builder(posts,"feed", "Derniers articles de Thierry Crouzet")
    print("Main feed done")


#TAGS
if len(db.used_tags) > 0:

    sitemap.open("sitemap-tags")
    tags = db.get_tags()
    total = len(tags)
    pbar = tools.logs.DualOutput.dual_tqdm(total=total, desc='Tags:')
    for tag in tags:
        tag = web.supercharge_tag(tag)
        sitemap.add_post(tag)
        if tag['tag'] in db.used_tags:

            if tag['tag']=="carnets":
                feed.builder(tag['posts'],"carnet-de-route", "Derniers carnets de Thierry Crouzet")
            if tag['tag']=="velo":
                feed.builder(tag['posts'],"borntobike", "Derniers articles sur le vélo de Thierry Crouzet")
            if tag['tag']=="ecriture":
                feed.builder(tag['posts'],"ecriture", "Derniers textes en construction de Thierry Crouzet")
            if tag['tag']=="mailing":
                feed.builder(tag['posts'],"mailing", "Autopromotion de Thierry Crouzet")
            if tag['tag']=="digest":
                feed.builder(tag['posts'],"digest", "De ma terrasse de Thierry Crouzet")

            layout.tag_gen(tag)

        pbar.update(1)
    pbar.close()
    sitemap.save()
    print(total, "tags updated")


#YEARS
if len(db.used_years) > 0:

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
                "post_md": posts[0]['path_md'],
                "url": f"{str(year)}/",
            }
            superyear= web.supercharge_tag(series, posts)
            sitemap.add_post(superyear)
            layout.tag_gen( superyear )
            years_archive += f'<p><a href="{str(year)}/">{year}</a></p>'

    sitemap.save()
    print("Years done")


#ARCHIVES
if len(db.used_years) > 0:

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
sitemap.save_index('sitemap',4)

print("Gen ended")

#EXPORT
if version>0:
    tools.tools.run_script('sync_aws.py')
    tools.tools.run_script('sync_github.py')
    tools.tools.run_script('sync_md.py')
    tools.tools.run_script('sync_gmi.py')
else:
    print("No export")
