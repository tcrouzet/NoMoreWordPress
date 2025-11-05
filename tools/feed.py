from feedgen.feed import FeedGenerator
import re, os
from html import unescape
from bs4 import BeautifulSoup
import tools.tools as tools

class Feed:

    def __init__(self, config, web):
        self.config = config
        self.web = web


    def striptags(self, html_text):
        return re.sub(r'<[^>]+>', '', html_text)


    def add_domains(self, template, html):
        soup = BeautifulSoup(html, 'html.parser')
        # Modifier les liens des images
        for img in soup.find_all('img'):
            if img['src'].startswith('/'):
                img['src'] = template['domain'] + img['src'].lstrip("/")
        # Modifier les liens des pages
        for link in soup.find_all('a'):
            if link['href'].startswith('/'):
                link['href'] = template['domain'] + link['href'].lstrip("/")
        return str(soup)


    def clean_content(self, content):
        """Supprimer les caractères de contrôle et les octets NULL"""
        return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', content)


    def builder(self, posts, filename, description, last_posts=5):
        
        rssname = f"{filename}.xml"
        date = tools.now_datetime()

        for template in self.config['templates']:

            fg = FeedGenerator()
            fg.id(f'{template['domain']}{rssname}')
            fg.title(f'{filename} - {self.config['title']}')
            fg.author({'name': f'{self.config['author']}', 'email': f'{self.config['email']}'})
            # fg.link(href=f"{self.config['domain']}{rssname}", rel='self')
            fg.link(href=f"{template['domain'].rstrip('/')}/{self.config['feeds_dir'].strip("/")}/{rssname}", rel='self')

            fg.language("fr")
            fg.description(self.striptags(description))
            fg.lastBuildDate(date)

            # If last_post is None, take all posts
            limit = last_posts or len(posts)

            # Add post to flux
            for post in reversed(posts[:limit]):
                
                post = self.web.supercharge_post(template, post)
                if not post:
                    continue

                fe = fg.add_entry()

                #print(post['title'])

                fe.id(f"{template['domain']}{post['url']}")  # Utiliser l'URL complète comme GUID

                fe.title(post['title'])
                fe.link(href=template["domain"]+post['url'])

                # Ajouter l'image en haut du contenu si disponible
                content_html = post['content'].strip()
                if post.get('thumb'):
                    thumb_url = post['thumb']['url']
                    if thumb_url.startswith('/'):
                        thumb_url = template['domain'] + thumb_url.lstrip("/")
                    
                    img_tag = f'<img src="{thumb_url}" alt="{post["title"]}" />'
                    content_html = img_tag + content_html


                cleaned_content = self.clean_content(self.add_domains(template, content_html.strip()))
                fe.content( cleaned_content, type='CDATA')

                fe.author(name=self.config["author"])

                article_date = tools.timestamp_to_paris_datetime(post['pub_date'])
                fe.pubDate(article_date)

                if post.get('thumb'):
                    thumb_url = post['thumb']['url']
                    if thumb_url.startswith('/'):
                        thumb_url = template['domain'] + thumb_url.lstrip("/")
                    fe.enclosure(url=thumb_url, length=str(post['thumb'].get('size', 0)), type=post['thumb'].get('mime', 'image/webp'))

            # Générer et enregistrer le flux RSS
            
            feeds_dir = os.path.join(template['export'],self.config['feeds_dir'].lstrip("/"))
            os.makedirs(feeds_dir, exist_ok=True)

            fg.rss_file( os.path.join(feeds_dir, rssname) , pretty=True )