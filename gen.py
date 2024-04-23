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

if config['build'] == 1:
    #Load new posts only
    tools.db.db_builder(config['vault'],False)
elif config['build'] == 2:
     #Rebuild all
    tools.db.db_builder(config['vault'],True)

#tools.db.list_tags()

layout = tools.layout.Layout(config)
web = tools.web.Web(config)

#TAGS

tags = tools.db.get_tags()
pbar = tqdm(total=len(tags), desc='Tags:')
for tag in tags:
    tag = web.supercharge_tag(tag)
    #print(tag)
    layout.tag_gen(tag)
    pbar.update(1)
    exit()


#POSTS

#posts = tools.db.get_posts_updated()
posts = tools.db.get_all_posts()
#posts = tools.db.get_all_pages()
#posts = tools.db.get_posts()

pbar = tqdm(total=len(posts), desc='Posts:')
for post in posts:
    #print(dict(post))
    #exit()
    layout.single_gen( web.supercharge_post(post) )
    pbar.update(1)

