import yaml
import os
import tools.db
import tools.layout
import tools.web

os.system('clear')

with open('site.yml', 'r') as file:
    config = yaml.safe_load(file)

#Load new posts if False (all post if True)
#tools.db.db_builder(config['vault'],False)

posts = tools.db.get_posts_updated()

layout = tools.layout.Layout(config)

for post in posts:
    layout.single( tools.web.supercharge_post(post, config) )
