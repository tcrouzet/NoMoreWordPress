import os
from datetime import datetime, timezone
import time
import locale
import pytz
from PIL import Image
import markdown
import shutil
from bs4 import BeautifulSoup
import json
import yaml


class Web:

    def __init__(self, config, db):
        self.config = config
        self.db = db

        # script_dir = os.path.dirname(os.path.abspath(__file__))
        # parent_dir = os.path.dirname(script_dir) + os.sep
        # script_dir = parent_dir

        # self.template_dir = os.path.join(parent_dir, "templates", self.config['template'])


    def format_timestamp_to_paris_time(self, timestamp):
        utc_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        paris_time = utc_time.astimezone(pytz.timezone('Europe/Paris'))
        return  paris_time.isoformat()


    def url(self, post):

        if not post:
            return None

        if "url" in post:
            return post['url']
                
        base = os.path.basename(post['path_md'])        
        file_name_without_extension = os.path.splitext(base)[0]
        if post['type'] == 0:

            #POST
            date = datetime.fromtimestamp(post['pub_date'])
            path = date.strftime("/%Y/%m/%d")
            url = '/'.join([path.strip('/'), file_name_without_extension]) + "/"
        
        elif post['type'] == 1:

            #PAGES
            url = file_name_without_extension + "/"

        elif post['type'] == 5:

            #TAGS
            url = "tag/" + post['main'].get('url',post['path_md'])

        # print(url)
        # exit()
        return url


    def url_image(self, src, post):
        date = datetime.fromtimestamp(post['pub_date'])
        path = date.strftime("%Y/%m/")
        url = self.config['images_dir'] + path + src.replace(self.config['vault_img'],"")
        return url

    def add_before_extension(self, url, text):
        return f"{os.path.splitext(url)[0]}-{text}{os.path.splitext(url)[1]}"

    def source_image(self, src, post):
        if not src:
            return None
        if post['type'] == 5:
            #Tags
            path = os.path.join( self.config['vault'], os.path.dirname(post['post_md']), src )
        else:
            path = os.path.join( self.config['vault'], os.path.dirname(post['path_md']), src )
        #print(path)
        try:
            with Image.open(path) as img:
                (width, height) = img.size
                url = self.url_image(src, post)
                url_aboslute = os.path.join( self.config['export'], url.strip("/"))
                sizes = {'1024': None, '250': None}

                if not os.path.exists(url_aboslute):
                    destination_dir = os.path.dirname(url_aboslute)
                    os.makedirs(destination_dir, exist_ok=True)
                    shutil.copy2(path, url_aboslute)

                    # Création des versions redimensionnées de l'image
                    for size in sizes.keys():
                        new_width = int(size)
                        ratio = (new_width / float(width))
                        new_height = int((float(height) * float(ratio)))
                        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        resized_path = os.path.join(destination_dir, self.add_before_extension(url,size))
                        save_path = os.path.join(self.config['export'],resized_path.strip("/"))
                        img_resized.save(save_path)
                        sizes[size] = resized_path

                else:
                    for size in sizes.keys():
                        sizes[size] = self.add_before_extension(url,size)
                
                return {"path": path,
                        "width": width,
                        "height": height,
                        "format": "image/"+img.format.lower(),
                        "url": url,
                        "url_1024": sizes['1024'],
                        "url_250": sizes['250']
                    }

        except Exception as e:
            #print("bug",e)
            return None


    def resume_paragraph(self, paragraph):
        # Longueur maximale du résumé
        max_length = 160
        
        # Si le paragraphe est déjà assez court, le retourner entier
        if len(paragraph) <= max_length:
            return paragraph
        
        # Couper le paragraphe aux 160 premiers caractères pour trouver un point
        end_index = paragraph.rfind('.', 0, max_length)
        
        # Si un point est trouvé dans la limite, retourner jusqu'au point inclus
        if end_index != -1:
            return paragraph[:end_index + 1]
        
        # Si aucun point n'est trouvé, couper à 157 caractères et ajouter "..."
        return paragraph[:157] + "..."

    def get_post_content(self, post):
        path = os.path.join(self.config['vault'], post['path_md'])
        try:
            frontmatter_start = False
            frontmatter_lines = []
            with open(path, "r", encoding="utf-8") as file:
                lines = file.readlines()

            for i, line in enumerate(lines):

                if i==0 and line.strip().startswith('---'):
                    #print("FrontStart")
                    frontmatter_start = True
                    continue

                if frontmatter_start:
                    if line.strip().startswith('---'):
                        frontmatter_start = False
                        frontmatter = yaml.safe_load('\n'.join(frontmatter_lines))
                    else:
                        frontmatter_lines.append(line)
                    continue

                if line.strip().startswith('#'):
                    # Supprimer tout jusqu'à la ligne après le titre trouvé
                    lines = lines[i + 1:]

                    # Ignorer les lignes vides après le titre
                    while lines and lines[0].strip() == '':
                        lines.pop(0)

                    # Vérifier si la première ligne non vide est une balise d'image et la supprimer
                    if lines and lines[0].strip().startswith('!['):
                        lines.pop(0)

                    # Ignorer les lignes vides après le titre
                    while lines and lines[0].strip() == '':
                        lines.pop(0)

                    break

            # Supprimer la ligne de tags à la fin si elle existe
            if lines and all(part.startswith('#') for part in lines[-1].strip().split()):
                lines.pop()            

            md = ''.join(lines)
            if len(frontmatter_lines) == 0:
                frontmatter = None
            return {"content": md.strip(), "description":self.resume_paragraph(lines[0].strip()), "frontmatter": frontmatter}

        except Exception as e:
            #print(e)
            return {"content": "", "description":"", "frontmatter": None}
        
    def image_manager(self, html, post):

        soup = BeautifulSoup(html, 'html.parser')
        images = soup.find_all('p')
        
        index = 0
        for p in images:
            
            img = p.find('img')
            if img:
                index +=1
                img_data = self.source_image(img['src'], post)
                if img_data:
                    alt_text = img.get('alt','')

                    new_div = soup.new_tag('div', id=f"image-{post['id']}-{index}", **{'class': 'image'})
                    new_img = soup.new_tag('img', src=f"{img_data['url']}",
                        **{'class': 'alignnone size-full paysage',
                        'alt': alt_text, 'width': img_data['width'], 'height': img_data['height'],
                        'loading': 'lazy', 'decoding': 'async',
                        'srcset': f'{img_data['url']} 1600w, {img_data['url_1024']} 1024w, {img_data['url_250']} 250w',
                        'sizes': '(max-width: 1600px) 100vw, 1600px'})
                    
                    new_div.append(new_img)
                    new_legend = soup.new_tag('div', **{'class': 'legend'})
                    new_legend.string = alt_text
                    new_div.append(new_legend)
                    p.replace_with(new_div)
                else:
                    p.decompose()

        return str(soup)

    def img_tag(self, img):
        return f'''<img width="{img['width']}" height="{img['height']}" src="{img['url']}" class="poster-img poster-img-full"
            alt="{img['alt']}" loading="lazy" decoding="async"
            srcset="{img['url_250']} 250w, {img['url_1024']} 1024w, {img['url']} 1600w"
            sizes="(max-width: 768px) 100vw, 768px" />'''


    def extract_tags(self, post):
        if "tags" in post:
            tags = json.loads(post['tags'])
        else:
            tags = ["None"]
        #if "serie" in tags:
        #    tags.remove("serie")
        return tags
        
    def main_tag(self, tagslist):
        if not tagslist:
            return None
        first_tag = ""
        for tag in tagslist:
            first_tag = tag
            if tag in self.config['tags']:
                response = {'slug': tag, "title":self.config['tags'][tag]['title']}
                turl = self.config['tags'][tag].get("url",None)
                if turl:
                    response['url'] = turl
                else:
                    response['url'] = first_tag
                return response
        return {'slug': first_tag, "title": self.title_formater(first_tag), "url": first_tag}
    
    def title_formater(self, title):
        return title.capitalize().replace("-"," ").replace("_"," ")

    def date_html(self,post):
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
        current_time = datetime.fromtimestamp(post['pub_date'])
        date_iso = current_time.strftime('%Y-%m-%dT%H:%M:00')
        time_published = current_time.strftime('%H:%M')
        date_link = current_time.strftime('/%Y/%m/')
        year_link = current_time.strftime('/%Y/')
        
        day_month = current_time.strftime('%d %B')
        
        msg = f'<span itemprop="datePublished" content="{date_iso}" title="Publié à {time_published}">'
        msg += f' <a href="{date_link}">{day_month}</a>'
        msg += f' <a href="{year_link}">{current_time.year}</a>'
        msg += '</span>'
        
        return msg

    def navigation(self, post):

        main_tag =  self.main_tag(post['tagslist'])

        if post["type"]==5:
            return {"maintag": main_tag}

        tag_posts = self.db.get_posts_by_tag(main_tag['slug'])

        prev_post = None
        next_post = None
        total_posts = len(tag_posts)
        #print(total_posts, main_tag['slug'], post['tagslist'])

        for i, tag_post in enumerate(tag_posts):
            #post_dict = dict(post)
            if post['id'] == tag_post['id']:
                if i-1>=0:
                    next_post = tag_posts[i-1]
                else:
                    next_post = tag_posts[-1]
                if i==total_posts-1:
                    prev_post = tag_posts[0]
                else:
                    prev_post = tag_posts[i+1]
                break

        return {"maintag": main_tag,
                "total_posts": total_posts,
                "prev_post": prev_post,
                "prev_url": "/"+self.url(prev_post),
                "next_post": next_post,
                "next_url": "/"+self.url(next_post),
                "order": total_posts-i
                }


    def tag_2_post(self, post):
        post = dict(post)
        post['main'] = self.main_tag([post['tag']])
        post['pub_date'] = time.time()
        post['pub_update'] = post['pub_date']
        post['title'] = self.title_formater(post['main']['title'])
        post['url'] = "tag/"+post['tag']
        return post

        
    def supercharge_post(self, post, maximal=True):

        if isinstance(post, self.db.get_row_factory()):
            post = dict(post)
        elif isinstance(post, list):
            post = dict(post[0])

        post['url'] = self.url(post)
        #print(post)
 
        if maximal:
            content = self.get_post_content(post)
            post['content'] = content['content']
            html = markdown.markdown(content['content'])
            post['html'] = self.image_manager(html, post)
            post['description'] = content['description']
            post['frontmatter'] = content['frontmatter']
            #print(post['frontmatter'])
        
        post['canonical'] = self.config['domain'] + post['url']
        post['pub_date_str'] = self.format_timestamp_to_paris_time(post['pub_date'])
        post['pub_update_str'] = self.format_timestamp_to_paris_time(post['pub_update'])
        post['thumb'] = self.source_image(post['thumb_path'], post)
        #print(post)
        # if post['thumb']:
        #     post['thumb']["alt"] = post['thumb_legend']
        #     post['thumb']['tag'] = self.img_tag(post['thumb'])

        post['tagslist'] = self.extract_tags(post)
        post['navigation'] = self.navigation(post)
        post['navigation']['datelink'] = self.date_html(post)
        # print(post['navigation'])
        # print(post['navigation']['maintag'])
        # exit()

        return post

    def supercharge_tag(self, tag, posts=None):

        if isinstance(tag, self.db.get_row_factory()):
            tag = dict(tag)
        elif isinstance(tag, list):
            print("Tag list")

        tag['type'] = 5
        tag['main'] = self.main_tag([tag['tag']])
        tag['path_md'] = tag['tag'] + "/"
        tag['url'] = self.url(tag)
        tag['title'] = tag['main']['title']
        tag['pub_date'] = tag['pub_update']

        tag['description'] = tag['title']
        tag['canonical'] = self.config['domain'] + tag['url']
        tag['pub_date_str'] = self.format_timestamp_to_paris_time(tag['pub_date'])
        tag['pub_update_str'] = self.format_timestamp_to_paris_time(tag['pub_update'])
        tag['thumb'] = self.source_image(tag['thumb_path'], tag)
        if tag['thumb']:
            tag['thumb']["alt"] = tag['thumb_legend']
            tag['thumb']['tag'] = self.img_tag(tag['thumb'])

        menu = []
        menu.append({"title": tag['title'], "url": "/tag/"+tag['tag']})
        if tag['tag'] != "blog":
            menu.append({"title": "Blog", "url": "/blog/"})
        if tag['tag'] != "series":
            menu.append({"title": "…", "url": "/series/"})
        index = len(menu)
        if tag['tag'] != "carnets" and index<4:
            menu.insert(index-1, {"title": "Carnets", "url": "/tag/carnet-de-route/"})
        index = len(menu)
        if tag['tag'] != "borntobike" and index<4:
            menu.insert(index-1, {"title": "Vélo", "url": "/tag/borntobike/"})
        tag['menu'] = menu

        if not posts:
            posts = self.db.get_posts_by_tag(tag['tag'])
        
        total_posts = len(posts)
        numbered_posts = []
        for index, post in enumerate(posts, start=1):

            post=dict(post)

            if post["type"]==5:
                post = self.tag_2_post(post)
                post_with_order = self.supercharge_post(post, False)
                post_with_order['order']=post['count']

            else:
                post_with_order = self.supercharge_post(post, False)
                post_with_order['order']=total_posts-index+1
 
            numbered_posts.append(post_with_order)

        tag['posts'] = numbered_posts
      
        return tag

def home_builder():
    post = {}
    return post