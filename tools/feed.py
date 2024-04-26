from feedgen.feed import FeedGenerator
import pytz
from datetime import datetime
import re, os
from html import unescape


class Feed:

    def __init__(self, config, web):
        self.config = config
        self.web = web

        self.feeds_dir = os.path.join(self.config['export'],self.config['feeds_dir'].lstrip("/"))
        os.makedirs(self.feeds_dir, exist_ok=True)


    def striptags(self, html_text):
        return re.sub(r'<[^>]+>', '', html_text)


    def builder(self, posts, filename, description):
        
        rssname = f"{filename}.xml"

        tz = pytz.timezone('Europe/Paris')
        date = datetime.now(tz)

        fg = FeedGenerator()
        fg.id(f'{self.config['domain']}{rssname}')
        fg.title(f'{filename} - {self.config['title']}')
        fg.author({'name': f'{self.config['author']}', 'email': f'{self.config['email']}'})
        fg.link(href=f"{self.config['domain']}{rssname}", rel='self')
        fg.language("fr")
        fg.description(self.striptags(description))
        fg.lastBuildDate(date)

        # Add post to flux
        #print(len(posts))
        #posts = list(reversed(posts))
        #posts.sort(key=lambda x: x['pub_date'], reverse=True)

        for post in reversed(posts[:5]):
        # for i, post in enumerate(posts):
        #     if i == 5:
        #         break
            
            fe = fg.add_entry()

            post = self.web.supercharge_post(post)
            #print(post['title'])

            fe.id(str(post['id']))
            fe.title(post['title'])
            fe.link(href=self.config["domain"]+post['url'])
            fe.content(post['html'].strip(), type='CDATA')

            fe.author(name=self.config["author"])

            article_date = datetime.fromtimestamp(post['pub_date'], tz)
            fe.pubDate(article_date)
            # if post['thumb']:
            #     fe.enclosure(url=post['thumb']['url'], length=str(post['thum']['size']), type=post['thumb']['mime'])

        # Générer et enregistrer le flux RSS
        fg.rss_str(pretty=True)
        fg.rss_file(os.path.join(self.feeds_dir, rssname))