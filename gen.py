"""Changer site.yml si mise à jour template"""
# gen.py

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

# Parcourir et filtrer les templates
filtered_templates = []
for template in config['templates']:
    if not template.get('skip', False):  # Garde si skip est False ou absent
        filtered_templates.append(template)
config['templates'] = filtered_templates

# print(config)
# exit()

version = int(config['version'])
db = tools.db.Db(config)
web = tools.web.Web(config, db)
layout = tools.layout.Layout(config, web)
layout.web = web
sitemap = tools.sitemap.Sitemap(config, web)
feed = tools.feed.Feed(config, web)

if config['build'] == 1:
    #Load new posts only
    db.db_builder(config['vault'],False)
elif config['build'] == 2:
     #Rebuild all
    db.db_builder(config['vault'],True)
print(db.new_posts, "new posts")
print(db.updated_posts, "updated posts")

#Menu
layout.menu_gen()

#Search
layout.search_gen()

#POSTS
posts = db.get_posts_updated()
total = len(posts)
if total >0:
    pbar = tools.logs.DualOutput.dual_tqdm(total=total, desc='Posts:')
    for post in posts:
        layout.single_gen( post )
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
        sitemap.add_post( post )
        pbar.update(1)
    sitemap.save()
    pbar.close()
    print("Sitemap posts done")

sitemap.open("sitemap-main")

#SERIES
if len(db.used_tags) > 0:
    exclude = ("invisible","iacontent","book","page","le_jardin_de_leternite")
    tags = db.get_tags("p.pub_date DESC",exclude)
    # print(dict(tags[0]))
    series = {
        "tag": "series",
        "pub_update": tags[0]['pub_update'],
        "thumb_path": tags[0]['thumb_path'],
        "thumb_legend": tags[0]['thumb_legend'],
        "post_md": tags[0]['post_md'],
        "url": "series/"
    }
    layout.tag_gen( series, tags )
    sitemap.add_post( series )
    print("Series done")

#BLOG
# layout.setDebug()
if  db.new_posts >0 or db.updated_posts > 0:
    exclude = tuple(config['home_exclude'])
    blog_posts = db.get_blog_posts(exclude)
    first_post = dict(blog_posts[0])
    series = {
        "tag": "blog",
        "pub_update": first_post['pub_update'],
        "thumb_path": first_post['thumb_path'],
        "thumb_legend": first_post['thumb_legend'],
        "post_md": first_post['path_md'],
        "url": "blog/",
    }
    layout.tag_gen( series, blog_posts )
    sitemap.add_post( series )
    feed.builder(posts,"blog", "Derniers articles de Thierry Crouzet")
    print(f"Blog done {len(blog_posts)}")
# layout.setDebug()

#HOME
if  db.new_posts >0 or db.updated_posts > 0 or new_home_template:
    if posts:
        print("Starting home")
        last_post=blog_posts[0]
        last_carnet = db.get_posts_by_tag("carnets", 1)
        last_bike = db.get_posts_by_tag("velo", 1)
        last_digest = db.get_posts_by_tag("digest", 1)
        layout.home_gen( last_post, last_carnet, last_bike, last_digest )

        sitemap.add_post({"url": "index.html", "pub_update_str": tools.tools.now_datetime_str(), "thumb": None }, False)

        print("Home done")

sitemap.add_page("archives/index.html", supercharge=False)
sitemap.save()


#MAIN FEED
if  db.new_posts >0 or db.updated_posts > 0:
    posts = db.get_all_posts()
    feed.builder(posts,"feed", "Derniers articles de Thierry Crouzet")
    print("Main feed done")


#TAGS
if len(db.used_tags) > 0:

    if config['build'] == 2:
        # Tous les tags
        sitemap.open("sitemap-tags")
        tags = db.get_tags()
    else:
        # Ceux utilisés
        tags = db.get_used_tags()
    total = len(tags)
    pbar = tools.logs.DualOutput.dual_tqdm(total=total, desc='Tags:')
    for tag in tags:
        sitemap.add_post(tag)
        if tag['tag'] in db.used_tags:

            if tag['tag']=="carnets":
                tag_posts = db.get_posts_by_tag(tag['tag'])
                feed.builder(tag_posts,"carnet-de-route", "Derniers carnets de Thierry Crouzet")
            if tag['tag']=="velo":
                tag_posts = db.get_posts_by_tag(tag['tag'])
                feed.builder(tag_posts,"borntobike", "Derniers articles sur le vélo de Thierry Crouzet")
            if tag['tag']=="ecriture":
                tag_posts = db.get_posts_by_tag(tag['tag'])
                feed.builder(tag_posts,"ecriture", "Derniers textes en construction de Thierry Crouzet")
            if tag['tag']=="mailing":
                tag_posts = db.get_posts_by_tag(tag['tag'])
                feed.builder(tag_posts,"mailing", "Autopromotion de Thierry Crouzet")
            if tag['tag']=="digest":
                tag_posts = db.get_posts_by_tag(tag['tag'])
                feed.builder(tag_posts,"digest", "De ma terrasse de Thierry Crouzet")

        layout.tag_gen(tag)

        pbar.update(1)
    pbar.close()
    if config['build'] == 2:
        # Tous les tags
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
                "type": 5,
                "title_date": f'<a href="/{str(prev_year)}">&lt;</a> {str(year)} <a href="/{str(next_year)}">&gt;</a>',
                "pub_update": posts[0]['pub_update'],
                "thumb_path": posts[0]['thumb_path'],
                "thumb_legend": posts[0]['thumb_legend'],
                "post_md": posts[0]['path_md'],
                "url": f"{str(year)}/",
            }
            sitemap.add_post(series)
            layout.tag_gen( series, posts )
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
sitemap.save_index('sitemap')

print("Gen ended")

#EXPORT
if version>0:
    for template in config['templates']:

        sync = template['sync'][0]
        sync['export'] = template['export']

        if sync['name'] == "aws":
            import tools.sync_aws as aws
            run_aws = aws.SyncAWS(sync)
            run_aws.sync()

        elif sync['name'] == "github":

            import subprocess

            dossier = template['export']
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            subprocess.run(["git", "add", "."], cwd=dossier)
            subprocess.run(["git", "commit", "-m", f"sync {current_date}"], cwd=dossier)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=dossier)

    # tools.tools.run_script('sync_md.py')
    # tools.tools.run_script('sync_gmi.py')
else:
    print("No export")
