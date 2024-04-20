import yaml
import os
import tools.db
import tools.layout
import tools.web

os.system('clear')

with open('site.yml', 'r') as file:
    data = yaml.safe_load(file)

#Load new posts if False (all post if True)
#tools.db.db_builder(data['vault'],False)

posts = tools.db.get_posts_updated()

layout = tools.layout.Layout(data)

for post in posts:
    post = dict(post)
    post['url'] = tools.web.url(post)
    layout.single(post)
