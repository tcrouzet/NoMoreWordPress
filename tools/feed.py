from feedgen.feed import FeedGenerator
import pytz
from datetime import datetime
import re, os
from html import unescape
from bs4 import BeautifulSoup



class Feed:

    def __init__(self, config, web):
        self.config = config
        self.web = web

        self.feeds_dir = os.path.join(self.config['export'],self.config['feeds_dir'].lstrip("/"))
        os.makedirs(self.feeds_dir, exist_ok=True)


    def striptags(self, html_text):
        return re.sub(r'<[^>]+>', '', html_text)


    def add_domains(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        # Modifier les liens des images
        for img in soup.find_all('img'):
            if img['src'].startswith('/'):
                img['src'] = self.config['domain'] + img['src'].lstrip("/")
        # Modifier les liens des pages
        for link in soup.find_all('a'):
            if link['href'].startswith('/'):
                link['href'] = self.config['domain'] + link['href'].lstrip("/")
        return str(soup)


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
        for post in reversed(posts[:5]):
            
            post = self.web.supercharge_post(post)
            if not post:
                continue

            fe = fg.add_entry()

            #print(post['title'])

            fe.id(str(post['id']))
            fe.title(post['title'])
            fe.link(href=self.config["domain"]+post['url'])
            fe.content( self.add_domains(post['html'].strip()), type='CDATA')

            fe.author(name=self.config["author"])

            article_date = datetime.fromtimestamp(post['pub_date'], tz)
            fe.pubDate(article_date)
            # if post['thumb']:
            #     fe.enclosure(url=post['thumb']['url'], length=str(post['thum']['size']), type=post['thumb']['mime'])

        # Générer et enregistrer le flux RSS
        fg.rss_str(pretty=True)
        fg.rss_file(os.path.join(self.feeds_dir, rssname))