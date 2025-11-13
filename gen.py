"""Changer site.yml si mise à jour template"""
# gen.py

import os, sys
from datetime import datetime
# from sqlite3 import Row

import tools.tools
import tools.db
import tools.layout
import tools.web
import tools.logs
import tools.sitemap
import tools.feed

#Force updating home screen
new_home_template = True
force = False

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

version = int(config['version'])
db = tools.db.Db(config)
web = tools.web.Web(config, db)
layout = tools.layout.Layout(config, web)
layout.web = web
sitemap = tools.sitemap.Sitemap(config, web)
feed = tools.feed.Feed(config, web)

if config['build'] > 0:

    print(f"Updating data status: {config['build']}")
    if config['build'] == 1 or config['build'] == 2:
        #Load new posts only
        print("Just new/updated posts")
        db.db_builder(config['vault'],reset=False)
    elif config['build'] == 3:
        #Rebuild all
        db.db_builder(config['vault'],reset=True)

    print("Media and navigation")
    posts = db.get_posts_updated()
    total = len(posts)
    if total >0:
        pbar = tools.logs.DualOutput.dual_tqdm(total=total, desc='Posts:')
        for post in posts:

            navigation = web.navigation(post)
            db.update_fields( post['id'], navigation)

            web.media_production(config['templates'], post)
            pbar.update(1)
        pbar.close()

#POSTS
print("Post generation")
if config['build'] == 2:
    posts = db.get_posts()
else:
    posts = db.get_posts_updated()
total = len(posts)
if total >0:
    pbar = tools.logs.DualOutput.dual_tqdm(total=total, desc='Posts:')
    for post in posts:
        layout.single_gen( post )
        db.updated(post)
        pbar.update(1)
    pbar.close()

#SITEMAP POSTS
if db.new_posts > 0 or config['build'] == 2:
    sitemap.open("sitemap-posts")
    posts = db.get_all_posts_and_pages()
    pbar = tools.logs.DualOutput.dual_tqdm(total=len(posts), desc='Sitemap-posts:')
    for post in posts:
        sitemap.add_post( post )
        pbar.update(1)
    sitemap.save()
    pbar.close()
    print("Sitemap posts done")


sitemap.open("sitemap-main")

#SERIES
if db.new_tags + db.updated_tags > 0 or config['build'] == 2:
    exclude_slugs = ("invisible","iacontent","book","page","le_jardin_de_leternite")
    tags = db.get_tags_with_lastpost(exclude_slugs)
    series = {
        "tag_slug": "series",
        "tag_title": "Séries",
        "description": f"Les thématiques de {config['title']}",
        "tag_url": "series/",
        "is_tag": True,
        "frontmatter": None
    }
    layout.tag_gen_serie( series, tags )
    sitemap.add_post( series, tags[0] )
    print("Series done")


#BLOG
if db.new_posts >0 or db.updated_posts > 0 or config['build'] == 2 or force:
    exclude = tuple(config['home_exclude'])
    blog_posts = db.get_posts("type=0", exclude)
    series = {
        "tag_slug": "blog",
        "tag_title": "Digression",
        "description": f"Tous les articles de {config['title']}",
        "tag_url": "/blog",
        "is_tag": True,
        "frontmatter": None
    }
    layout.tag_gen( series, blog_posts )
    sitemap.add_post( series, blog_posts[0] )
    feed.builder(blog_posts,"blog", "Derniers articles de Thierry Crouzet")
    print(f"Blog done {len(blog_posts)}")

#HOME
if  db.new_posts >0 or db.updated_posts > 0 or config['build'] == 2:
    if posts:
        print("Starting home")
        last_carnet = db.get_posts_by_tag("carnets", 1)
        last_bike = db.get_posts_by_tag("velo", 1)
        last_digest = db.get_posts_by_tag("digest", 1)
        layout.home_gen( blog_posts[0], last_carnet[0], last_bike[0], last_digest[0] )

        sitemap.add_post({"url": "index.html", "pub_update_str": tools.tools.now_datetime_str(), "thumb": None }, blog_posts[0])

        print("Home done")

sitemap.add_page("archives/index.html")
sitemap.save()


#MAIN FEED
if  db.new_posts + db.updated_posts > 0 or config['build'] == 2:
    posts = db.get_blog_posts()
    feed.builder(posts,"feed", "Derniers articles de Thierry Crouzet")
    print("Main feed done")


#TAGS
if db.new_tags > 0 or config['build'] == 2 or force:

    # exclude = tuple(config['pages'])
    exclude = tuple(["page","blog"])

    if config['build'] > 1:
        # Tous les tags
        sitemap.open("sitemap-tags")
        tags = db.get_tags(exclude_slugs=exclude)
    else:
        # Ceux utilisés
        tags = db.get_tags_used(exclude_slugs=exclude)
    total = len(tags)
    pbar = tools.logs.DualOutput.dual_tqdm(total=total, desc='Tags:')
    for tag in tags:
        tag=dict(tag)
        sitemap.add_post(tag)
        tag_posts = db.get_posts_by_tag(tag['tag_slug'])
        if len(tag_posts)==0:
            continue
        layout.tag_gen( tag, tag_posts )

        if tag['tag_slug']=="carnets":
            feed.builder(tag_posts,"carnet-de-route", "Derniers carnets de Thierry Crouzet")
        if tag['tag_slug']=="velo":
            feed.builder(tag_posts,"borntobike", "Derniers articles sur le vélo de Thierry Crouzet")
        if tag['tag_slug']=="ecriture":
            feed.builder(tag_posts,"ecriture", "Derniers textes en construction de Thierry Crouzet")
        if tag['tag_slug']=="mailing":
            feed.builder(tag_posts,"mailing", "Autopromotion de Thierry Crouzet")
        if tag['tag_slug']=="digest":
            feed.builder(tag_posts,"digest", "De ma terrasse de Thierry Crouzet")

        db.updated_tag(tag)
        pbar.update(1)
    pbar.close()
    if config['build'] > 1:
        # Tous les tags
        sitemap.save()


#YEARS
if db.new_posts > 0 or config['build'] == 2:

    print("Year gen")
    sitemap.open("sitemap-years")
    years_archive = ""
    exclude = ("invisible","book","page")
    years = db.get_years()
    for iy, year in enumerate(years):

        posts = db.get_posts_by_year(year, exclude)
        if len(posts)>0:

            if iy<len(years)-1:
                prev_year =  years[iy+1]
            else:
                prev_year =  years[0]

            if iy>0:
                next_year =  years[iy-1]
            else:
                next_year =  years[-1]

            year_tag = {
                "tag_slug": str(year),
                "tag_title_date": f'<a href="/{str(prev_year)}">&lt;</a> {str(year)} <a href="/{str(next_year)}">&gt;</a>',
                "pub_update": posts[0]['pub_update'],
                "thumb_path": posts[0]['thumb_path'],
                "thumb_legend": posts[0]['thumb_legend'],
                "path_md": posts[0]['path_md'],
                "tag_url": f"/{str(year)}/",
                "url": f"/{str(year)}/",
                "is_tag": True,
                "frontmatter": None
            }
            layout.year_gen( year_tag, posts )
            sitemap.add_post(year_tag)
            years_archive += f'<p><a href="/{str(year)}/">{year}</a></p>'

    sitemap.save()
    print("Years done")


#ARCHIVES
if db.new_posts > 0 or config['build'] == 2:

    posts_archive = ""
    exclude = ("invisible")
    posts = db.get_blog_posts(exclude)
    for post in posts:
        posts_archive += f'<p><a href="{post['url']}">' + datetime.fromtimestamp(post['pub_date']).strftime('%Y/%m/%d').replace('/0','/') + f' {post['title']}</a></p>'
    layout.archives_gen( f"<h3>Années</h3>{years_archive}<h3>Billets</h3>{posts_archive}" )
    print("Archives done")


#Menu
layout.menu_gen()


#Search
layout.search_gen()


#ERROR
layout.e404_gen()


#END SITEMAP
sitemap.save_index('sitemap')

print("Gen ended")

#EXPORT
if version>0 and db.new_posts + db.updated_posts > 0:
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

    tools.tools.run_script('tools/sync_md.py')
    tools.tools.run_script('tools/sync_gmi.py')
else:
    print("No export")
