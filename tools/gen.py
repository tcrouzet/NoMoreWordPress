"""Changer site.yml si mise à jour template"""
# gen.py

import os, sys
from datetime import datetime
from bs4 import BeautifulSoup
# from sqlite3 import Row

import tools
import db
import layout
import web
import logs
import sitemap
import feed
import static_sync

#Force updating home screen
new_home_template = True
force = False

sys.stdout = logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

os.system('clear')

if len(sys.argv) < 2 or not sys.argv[1].strip():
    exit('Usage: python3 ./tools/gen.py "nom_du_site"')

site = sys.argv[1].strip()
config = tools.site_yml(site)
config['site'] = site
full_build = int(config.get('build', 0)) >= 2

if config.get('diaporamas'):
    if not tools.run_script('tools/diaporama.py', site):
        exit('Échec de la génération des diaporamas')

# Parcourir et filtrer les templates
filtered_templates = []
for template in config['templates']:
    if not template.get('skip', False):  # Garde si skip est False ou absent
        filtered_templates.append(template)
config['templates'] = filtered_templates

version = int(config['version'])
db = db.Db(config)
web = web.Web(config, db)
layout = layout.Layout(config, web)
layout.web = web
template_changed = bool(layout.new_assets)
sitemap = sitemap.Sitemap(config, web)
feed = feed.Feed(config, web)

# testing
# db.un_updated_by_path("2025/11/social-et-toxique.md")
# db.un_updated(462)

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
        pbar = logs.DualOutput.dual_tqdm(total=total, desc='Posts:')
        for post in posts:

            navigation = web.navigation(post)
            db.update_fields( post['id'], navigation)

            web.media_production(config['templates'], post)
            pbar.update(1)
        pbar.close()

# Le menu du pied est entièrement défini par footer.md dans le vault.
footer_post = db.get_post_by_path('footer.md')
config['footer_content'] = footer_post['content'] if footer_post else ''
config['header_menu'] = []
if config['footer_content']:
    footer_soup = BeautifulSoup(config['footer_content'], 'html.parser')
    for link in footer_soup.find_all('a', href=True):
        href = link['href'].strip()
        if href and not href.startswith(('/', '#', 'http://', 'https://', 'mailto:', 'tel:')):
            link['href'] = '/' + href
    header_links = footer_soup.find_all('a', href=True)
    if config.get('header_menu_filter') == 'bold':
        header_links = [
            link for link in header_links
            if link.find_parent(['strong', 'b']) or link.find(['strong', 'b'])
        ]
    config['header_menu'] = [
        {'title': link.get_text(strip=True), 'url': link.get('href')}
        for link in header_links
        if link.get_text(strip=True)
    ]
    if config.get('header_menu_filter') == 'bold':
        for emphasis in footer_soup.find_all(['strong', 'b']):
            emphasis.unwrap()
    config['footer_content'] = str(footer_soup)

#POSTS
print("Post generation")
if full_build or template_changed:
    posts = db.get_posts()
else:
    posts = db.get_posts_updated()
total = len(posts)
if total >0:
    pbar = logs.DualOutput.dual_tqdm(total=total, desc='Posts:')
    for post in posts:
        if post['path_md'] not in ('home.md', 'footer.md'):
            layout.single_gen(post)
        db.updated(post)
        pbar.update(1)
    pbar.close()

if db.new_posts + db.updated_posts + db.deleted_posts > 0 or full_build:
    sitemap.open("sitemap-posts")
    posts = db.get_posts(condition="type<5", exclude_tags=["private","invisible"])
    # posts = db.get_all_posts_and_pages()
    pbar = logs.DualOutput.dual_tqdm(total=len(posts), desc='Sitemap-posts:')
    for post in posts:
        if post['path_md'] in ('home.md', 'footer.md'):
            continue
        sitemap.add_post( post )
        pbar.update(1)
    sitemap.save()
    pbar.close()
    print("Sitemap posts done")


if (
    db.new_posts
    + db.updated_posts
    + db.deleted_posts
    + db.new_tags
    + db.updated_tags > 0
    or template_changed
    or new_home_template
    or full_build
):

    sitemap.open("sitemap-main")

    #SERIES
    exclude_slugs = ("invisible","iacontent","book","page","le_jardin_de_leternite","private")
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
    exclude = tuple(config['home_exclude'])
    blog_posts = db.get_posts("type=0", exclude)
    blog_tag = db.tag_2_dict("blog")
    blog_tag.update({
        "description": config.get('tags', {}).get('blog', {}).get(
            'description', f"Tous les articles de {config['title']}"
        ),
        "is_tag": True,
        "frontmatter": None
    })
    layout.tag_gen(blog_tag, blog_posts)
    sitemap.add_post(blog_tag, blog_posts[0])
    feed.builder(
        blog_posts,
        blog_tag['tag_url'].strip('/'),
        f"Derniers articles de {config['title']}"
    )
    print(f"Blog done {len(blog_posts)}")

    #HOME
    home_post = db.get_post_by_path('home.md')
    if home_post or blog_posts:
        print("Starting home")
        home_posts = {}
        for section, tag_slug in config.get('home_tags', {}).items():
            tagged_posts = db.get_posts_by_tag(tag_slug, 1)
            if tagged_posts:
                home_posts[section] = tagged_posts[0]
        last_post = blog_posts[0] if blog_posts else None
        layout.home_gen(last_post, home_posts, home_post)

        sitemap.add_post(
            {"url": "index.html", "pub_update_str": tools.now_datetime_str(), "thumb": None},
            home_post or last_post
        )

        print("Home done")

    sitemap.add_page("archives/index.html")
    sitemap.add_page("menu.html")
    sitemap.add_page("search.html")
    sitemap.save()


#MAIN FEED
if db.new_posts + db.updated_posts + db.deleted_posts > 0 or full_build:
    exclude_slugs = ("invisible","private")
    posts = db.get_blog_posts( exclude_tags=exclude_slugs)
    feed.builder(posts,"feed", "Derniers articles de Thierry Crouzet")
    print("Main feed done")


#TAGS
exclude = tuple(["page","blog","private","invisible"])
if db.new_tags + db.updated_tags > 0 or template_changed or full_build:

    if full_build:
        # Tous les tags
        tags = db.get_tags(exclude_slugs=exclude)
    else:
        # Ceux utilisés
        tags = db.get_tags_used(exclude_slugs=exclude)
    if full_build:
        layout.clean_stale_tag_exports(tags)
    total = len(tags)
    pbar = logs.DualOutput.dual_tqdm(total=total, desc='Tags:')
    for tag in tags:
        tag=dict(tag)
        tag_posts = db.get_posts_by_tag(tag['tag_slug'], exclude_tags=["private","invisible"])
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

if db.new_tags + db.updated_tags > 0 or template_changed or full_build:
    sitemap.open("sitemap-tags")
    tags = db.get_tags(exclude_slugs=exclude)
    for tag in tags:
        tag=dict(tag)
        sitemap.add_post(tag)
    sitemap.save()


#YEARS
if db.new_posts + db.updated_posts + db.deleted_posts > 0 or template_changed or full_build:

    print("Year gen")
    sitemap.open("sitemap-years")
    years_archive = ""
    exclude = ("invisible","book","page","private")
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
if db.new_posts + db.updated_posts + db.deleted_posts > 0 or template_changed or full_build:

    posts_archive = ""
    exclude = ("invisible","private")
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
if full_build:
    sitemap.save_index('sitemap')

print("Gen ended")

#STATIC FILES
updated_static_files = static_sync.StaticSync(config).run()

#EXPORT
site_changed = (
    db.new_posts
    + db.updated_posts
    + db.deleted_posts
    + updated_static_files > 0
    or template_changed
    or full_build
)

if version > 0 and site_changed:
    for template in config['templates']:

        sync = template['sync'][0]
        sync['export'] = template['export']

        if sync['name'] == "aws":
            import sync_aws as aws
            run_aws = aws.SyncAWS(sync)
            run_aws.sync()

        elif sync['name'] == "github":
            import publish_git
            publish_git.publish_export(template['export'])

    if config.get('export_github_md'):
        tools.run_script('tools/sync_md.py', site)

    if config.get('export_github_md') and config.get('gemini_export'):
        tools.run_script('tools/sync_gmi.py', site)
else:
    print("No export")
