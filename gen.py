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

#tools.db.list_test()

#Load new posts if False (all post if True)
tools.db.db_builder(config['vault'],False)
#tools.db.db_builder(config['vault'],True)

#posts = tools.db.get_posts_updated()
posts = tools.db.get_all_posts()
layout = tools.layout.Layout(config)
web = tools.web.Web(config)

pbar = tqdm(total=len(posts), desc='Gen:')
for post in posts:
    #print(dict(post))
    #exit()
    layout.single_gen( web.supercharge_post(post) )
    pbar.update(1)

