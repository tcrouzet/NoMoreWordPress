import yaml
import os, sys
from tqdm import tqdm
import tools.db
import tools.layout
import tools.web
import tools.logs

sys.stdout = tools.logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

os.system('clear')

with open('site.yml', 'r') as file:
    config = yaml.safe_load(file)

db = tools.db.Db(config)
web = tools.web.Web(config, db)
layout = tools.layout.Layout(config)

if config['build'] == 1:
    #Load new posts only
    new_pots = db.db_builder(config['vault'],False)
elif config['build'] == 2:
     #Rebuild all
    new_pots = db.db_builder(config['vault'],True)
print(new_pots, "new posts")

#db.list_posts_updated()

#POSTS
posts = db.get_posts_updated()
total = len(posts)
pbar = tqdm(total=total, desc='Posts:')
for post in posts:
    supercharged = web.supercharge_post(post)
    layout.single_gen( supercharged )
    #db.updated(post)
    pbar.update(1)
pbar.close()
db.db_commit()
print(total, "posts updated")
exit()


#SERIES
exclude = ("invisible","iacontent","book","page","le_jardin_de_leternite")
tags = db.get_tags("p.pub_update DESC",exclude)
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
print("Blog done")


#HOME
last_post=posts[0]
last_carnet = db.get_posts_by_tag("carnets", 1)
last_bile = db.get_posts_by_tag("velo", 1)
home = web.supercharge_post(last_post, False)
test = web.supercharge_post(last_carnet, False)
home['carnet'] = web.supercharge_post(last_carnet, False)
#tools.db.list_object(home['carnet'])
home['bike'] = web.supercharge_post(last_bile, False)
layout.home_gen( home )
print("Home done")


#TAGS
tags = db.get_tags()
total = len(tags)
pbar = tqdm(total=total, desc='Tags:')
for tag in tags:
    #tools.db.list_object(tag,False)
    tag = web.supercharge_tag(tag)
    layout.tag_gen(tag)
    pbar.update(1)
pbar.close()
print(total, "tags updated")
