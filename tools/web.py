import os, re
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
from urllib.parse import urlparse
import tools.frontmatter as ft
import tools.tools as tools


class Web:

    def __init__(self, config, db):
        self.config = config
        self.db = db
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.parent_dir = os.path.dirname(script_dir) + os.sep


    def url(self, post):

        if not post:
            return None

        if "url" in post:
            return post['url']
                
        base = os.path.basename(post['path_md'])        
        file_name_without_extension = os.path.splitext(base)[0]
        if post['type'] == 0:

            #POST
            dt = tools.timestamp_to_paris_datetime(post["pub_date"])
            path = dt.strftime("/%Y/%m/%d")
            url = "/".join([path.strip("/"), file_name_without_extension]) + "/"
        
        elif post['type'] == 1 or post['type'] == 2:

            #PAGES
            url = os.path.dirname(post['path_md']) + "/" + file_name_without_extension + "/"
            #url = file_name_without_extension + "/"
            # print(url)
            # print(post)
            # exit()

        elif post['type'] == 5:

            #TAGS
            main_url = post['main'].get('url',None)
            if main_url:
                if main_url.startswith("/"):
                    url = main_url.strip("/")
                else:
                    url = "tag/"+main_url
            else:
                url = "tag/" + post['path_md']


            #url = "tag/" + post['main'].get('url',post['path_md'])

        # print(url)
        # exit()
        return url


    def comment_url(self, post):

        if not post:
            return None

        if "comment_url" in post:
            return post['comment_url']
                
        base = os.path.basename(post['path_md'])        
        file_name_without_extension = os.path.splitext(base)[0]
        if post['type'] == 0:

            #POST
            date = tools.timestamp_to_paris_datetime(post["pub_date"])
            path = date.strftime("/%Y/%-m/")
            url = '/'.join([path.strip('/'), file_name_without_extension]) + ".md"
        
        elif post['type'] == 1 or post['type'] == 2:

            #PAGES
            url = os.path.dirname(post['path_md']) + "/" + file_name_without_extension + ".md"
        
        else:

            url = None

        return url
    

    def url_image_relatif(self, src, post):
        """retourne url relatif d'un media"""
        if post['type'] == 5:
            filename = os.path.basename(post['thumb_path'])
            path = self.normalize_month(os.path.dirname(post['post_md']))
        else:
            date = tools.timestamp_to_paris_datetime(post["pub_date"])
            path = date.strftime("%Y/%m/")
            filename = src.replace(self.config['vault_img'], "")
        
        url = os.path.join("/", self.config['images_dir'].strip("/"), path, filename)
    
        return url

    # def media_path(self, src, post, template):
    #     source_path = self.url_image( src, post)
    #     target_path = os.path.join( template['export'], source_path.strip("/"))
    #     return source_path, target_path
    
    def media_target_path(self, template, url_media_relatif):
        return os.path.join( template['export'], url_media_relatif.strip("/"))

    def add_before_extension(self, url, text):
        if text=="max_size":
            return url
        return f"{os.path.splitext(url)[0]}-{text}{os.path.splitext(url)[1]}".strip("/")
    
    # copy un media s'il existe pas
    def copy_if_needded_all(self, media_source_path, url_media_relatif):

        if not os.path.exists(media_source_path):
            print("Can't find:", media_source_path)
            raise  FileNotFoundError

        for template in self.config['templates']:
            media_target_path = self.media_target_path(template, url_media_relatif)
            if not os.path.exists(media_target_path):
                destination_dir = os.path.dirname(media_target_path)
                os.makedirs(destination_dir, exist_ok=True)
                print(destination_dir, media_target_path)
                shutil.copy2(media_source_path, media_target_path)


    def copy_if_needded(self, media_source_path, media_target_path):

        if not os.path.exists(media_source_path):
            print("Can't find:", media_source_path)
            raise  FileNotFoundError

        if not os.path.exists(media_target_path):
            destination_dir = os.path.dirname(media_target_path)
            os.makedirs(destination_dir, exist_ok=True)
            shutil.copy2(media_source_path, media_target_path)


    def relativise_path(self, template, path):
        return path.replace(template['export'],"").strip("/")


    def normalize_month(self, path):
        parts = path.split('/')
        if len(parts) < 2:
            return path
        year = parts[0]
        month = parts[1]
        month_padded = month.zfill(2)
        normalized_parts = [year, month_padded] + parts[2:]
        return '/'.join(normalized_parts)


    def source_image(self, media_src_file, post):
        """Media manager
        media_src_file _i/image.webp"""
        
        if not media_src_file:
            return None
        
        media_source_path = os.path.join( self.config['vault'], os.path.dirname(post['path_md']), media_src_file )
        url_media_relatif = self.url_image_relatif( media_src_file, post)

        if media_src_file.endswith('.mp3'):
            self.copy_if_needded_all(media_source_path, url_media_relatif)
            return {"path": media_source_path,
                "format": "audio/mpeg",
                "url": url_media_relatif,
            }

        if media_src_file.endswith('.pdf'):
            self.copy_if_needded_all(media_source_path, url_media_relatif)
            return {"path": media_source_path,
                "format": "application/pdf",
                "url": url_media_relatif,
            }

        #print(path)
        try:
            with Image.open(media_source_path) as img:

                (width, height) = img.size

                if img.format in ["GIF","PNG"]:
                    self.copy_if_needded_all(media_src_file, url_media_relatif)
                    return {"path": media_source_path,
                        "width": width,
                        "height": height,
                        "format": "image/"+img.format.lower(),
                        "url": url_media_relatif,
                        # "url_absolu": self.config['domain'] + url.strip("/"),
                        "url_absolu": url_media_relatif.strip("/"),
                        "url_1024": url_media_relatif,
                        "url_250": url_media_relatif,
                        "jpeg": url_media_relatif,
                        "legend": getattr(post, 'thumb_legend', '') or ''
                    }

                # Webp et JPEG
                for template in self.config['templates']:
                    if width > template['image_max_size']:
                        # Need to resize
                        sizes = {'max': 'resize', '1024': 'resize', '250': 'resize'}
                        max_size = template['image_max_size']
                    elif width > 1024:
                        sizes = {'max': None, '1024': 'resize', '250': 'resize'}
                    else:
                        sizes = {'max': None, '250': 'resize'}

                    # Création des versions redimensionnées de l'image
                    media_target_path = self.media_target_path(template, url_media_relatif)
                    print(media_source_path, "→", media_target_path)
                    for size, value in sizes.items():

                        if value is None:
                            self.copy_if_needded(media_source_path, media_target_path)
                            sizes[size] = self.relativise_path(template, media_target_path)
                            continue
                        
                        # resize needed

                        if size == 'max':
                            new_path = media_target_path
                            new_width = int(template['image_max_size'])
                        else:
                            new_path = self.add_before_extension(media_target_path,size)
                            new_width = int(size)

                        if os.path.exists(new_path):
                            sizes[size] = self.relativise_path(template, new_path)
                            continue

                        ratio = (new_width / float(width))
                        new_height = int((float(height) * float(ratio)))
                        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                        img_resized.save(new_path)
                        sizes[size] = self.relativise_path(template, new_path)
                
                return {"path": media_source_path,
                        "width": width,
                        "height": height,
                        "format": "image/"+img.format.lower(),
                        "url": sizes.get('max',''),
                        "url_absolu": sizes.get('max',''),
                        "url_1024": sizes.get('1024', sizes.get('max','') ),
                        "url_250": sizes.get('250', sizes.get('max','')),
                        "jpeg": "",
                        "legend": getattr(post, 'thumb_legend', '') or ''
                    }

        except Exception as e:
            #print("bug",e)
            return None
    

    def makeJPEGthumb(self, thumb):
        """Make jpeg for facebook share"""

        if not thumb:
            return thumb

        thumb['jpeg'] =  f"{os.path.splitext(thumb['url'])[0]}.jpeg".strip("/")
        jpeg_path = os.path.join(self.config['export'], thumb['jpeg'])

        if thumb['format'] == "image/webp" and not os.path.exists(jpeg_path) :
            # Make jpeg file
            try:
                img = Image.open(thumb['path'])
     
                # if img.width > 1024:
                #     # Calculer le ratio de réduction
                #     ratio = 1024 / img.width
                #     new_height = int(img.height * ratio)
                #     img = img.resize((1024, new_height), Image.Resampling.LANCZOS)
                
                img.convert("RGB").save(jpeg_path, 'JPEG', quality=85, optimize=True, progressive=True)
                
                # Fermer l'image
                img.close()
                
            except Exception as e:
                print(f"Erreur lors de la conversion thumb JEPG : {e}")
                return False
            
        return thumb


    def striptags(self, html_text):
        return re.sub(r'<[^>]+>', '', html_text)
    
    def stripmd(self, markdown_text):
        # Remove images
        markdown_text = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_text)
        # Remove links but keep the text
        markdown_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', markdown_text)
        markdown_text = markdown_text.replace("*","")
        return markdown_text

    def resume_paragraph(self, paragraph):
        # Longueur maximale du résumé
        max_length = 160

        c_paragraph = self.striptags(paragraph)
        c_paragraph = self.stripmd(c_paragraph)

        # Si le paragraphe est déjà assez court, le retourner entier
        if len(c_paragraph) <= max_length:
            return c_paragraph
        
        # Couper le paragraphe aux 160 premiers caractères pour trouver un point
        end_index = c_paragraph.rfind('.', 0, max_length)
        
        # Si un point est trouvé dans la limite, retourner jusqu'au point inclus
        if end_index != -1:
            return c_paragraph[:end_index + 1]
        
        # Si aucun point n'est trouvé, couper à 157 caractères et ajouter "..."
        return c_paragraph[:159] + "…"


    def is_post_otherwise_delete(self, post):
        if not post:
            return None
        path = os.path.join(self.config['vault'], post['path_md'])
        if post["type"]==0:
            if not os.path.exists(path):
                self.db.delete_post(post)
                return None
        return path

    def get_post_content(self, path):
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

            description = self.resume_paragraph(lines[0].strip())
            
            return {"content": md.strip(), "description":description, "frontmatter": frontmatter}

        except Exception as e:
            #print(e)
            return {"content": "", "description":"", "frontmatter": None}


    def image_manager(self, html, post):
        """Optimize HTML for images"""

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

                    if img_data["format"].startswith("image/"):

                        if img_data['width'] < img_data['height']:
                            myclass = 'portrait'
                            myclasslegend = 'legend-center'
                        else:
                            myclass = ''
                            myclasslegend = ''
                        if img_data['width'] < 1500:
                            myclass += ' small'
                            myclasslegend = 'legend-center'

                        if "png" in img_data["format"]:
                            myclasslegend = 'legend-center'

                        # new_div = soup.new_tag('figure', id=f"image-{post['id']}-{index}", **{'class': 'image'})
                        new_div = soup.new_tag('figure')
                        img_attrs = {
                            'src': img_data['url'],
                            'alt': alt_text,
                            'width': img_data['width'],
                            'height': img_data['height'],
                            'loading': 'lazy',
                            'decoding': 'async',
                            'srcset': f"{img_data['url']} 1600w, {img_data['url_1024']} 1024w, {img_data['url_250']} 250w",
                            'sizes': '(max-width: 1600px) 100vw, 1600px'
                        }

                        if myclass:
                            img_attrs['class'] = myclass

                        new_img = soup.new_tag('img', **img_attrs)

                        new_div.append(new_img)

                        if myclasslegend:
                            new_legend = soup.new_tag('figcaption', **{'class': f'legend {myclasslegend}'})
                        else:
                            new_legend = soup.new_tag('figcaption')
                        new_legend.string = alt_text
                        new_div.append(new_legend)
                        p.replace_with(new_div)

                    elif img_data["format"].startswith("audio/"):

                        new_div = soup.new_tag('figure')
                        new_audio = soup.new_tag('audio', controls='', preload='none')
                        new_audio['src'] = img_data['url']
                        new_div.append(new_audio)

                        fallback_link = soup.new_tag('a', href=f"{img_data['url']}")
                        fallback_link.string = "Ouvrir l'audio…"
                        new_div.append(fallback_link)

                        p.replace_with(new_div)

                    elif img_data["format"].startswith("application/"):
                        new_div = soup.new_tag('div', id=f"pdf-{post['id']}-{index}", **{'class': 'pdf'})
                        new_object = soup.new_tag('object', data=f"{img_data['url']}", type="application/pdf", width="100%", height="500px")
                        fallback_link = soup.new_tag('a', href=f"{img_data['url']}")
                        fallback_link.string = "Click here to download the PDF file."
                        new_object.append(fallback_link)
                        new_div.append(new_object)
                        p.replace_with(new_div)

                else:
                    p.decompose()

        return str(soup)


    def is_valid_year_month_path(self, path):
        # Utilisation d'une expression régulière pour tester le format
        pattern = r'^\d{4}/\d{1,2}/'
        return re.match(pattern, path) is not None


    def relative_to_absolute(self, post, relative_url):
        
        directory_path = os.path.dirname(post['path_md'])
        full_path = os.path.normpath(os.path.join(directory_path, relative_url.replace(".md","")))
        absolute_path = os.path.abspath(full_path)
        url = os.path.relpath(absolute_path, self.parent_dir).strip("/")

        if self.is_valid_year_month_path(url):
            #C'est un post, faut ajouter le jour
            href_post = self.db.get_post_by_path(url+".md")
            if href_post:
                url = self.url( href_post )
            elif "#com" in url:
                #Non géré
                pass
            else:
                pass
                # print("Unknown url", url, "dans:", post['path_md'])
                # exit()
        return "/" + url
    

    def link_manager(self, html, post):

        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a')

        # Domaine du site (ex: https://tcrouzet.com → tcrouzet.com)
        site_domain = self.config["domain"]
        site_netloc = urlparse(site_domain if site_domain.startswith("http") else f"https://{site_domain}").netloc

        for link in links:
            href = link.get('href', '')
            if not href:
                continue

            if href.endswith(".md") and not href.startswith("http"):
                #internal
                link['href'] = self.relative_to_absolute(post, href)
                continue

            # Liens externes: ajouter rel="noopener noreferrer"
            # on ignore ancres, mailto, tel, etc.
            if href.startswith(("http://", "https://")):
                netloc = urlparse(href).netloc
                if netloc and netloc != site_netloc:
                    existing_rel = link.get("rel", [])
                    # BeautifulSoup normalise rel en liste si présent
                    if isinstance(existing_rel, str):
                        existing_rel = existing_rel.split()
                    # fusion sans doublons
                    rel_tokens = set(existing_rel) | {"noopener", "noreferrer"}
                    link['rel'] = " ".join(sorted(rel_tokens))

        return str(soup)


    def img_tag(self, img):
        return f'''<img width="{img['width']}" height="{img['height']}" src="{img['url']}" class="poster-img poster-img-full"
            alt="{img['alt']}" loading="lazy" decoding="async"
            srcset="{img['url_250']} 250w, {img['url_1024']} 1024w, {img['url']} 1600w"
            sizes="(max-width: 768px) 100vw, 768px" />'''

    
    def extract_tags(self, post):
        
        #Cleaning
        if isinstance(post, str):
            tags = [post]
        elif "tags" in post:
            tags = json.loads(post['tags'])
        else:
            tags = ["None"]
        if len(tags)>1 and "dialogue" in tags:
            tags.remove("dialogue")
        
        #Enrich
        tagslist = []
        main_tag = True
        for tag in tags:
            if tag in self.config['tags']:
                response = {'slug': tag, "title":self.config['tags'][tag]['title']}
                turl = self.config['tags'][tag].get("url",None)
                if turl:
                    response['url'] = turl
                else:
                    response['url'] = tag
                if main_tag:
                    tagslist.insert(0, response)
                    main_tag = False
                else:
                    tagslist.append(response)        
            else:
                response = {'slug': tag, "title": self.title_formater(tag), "url": tag}
                tagslist.append(response)

        return tagslist

    
    def title_formater(self, title):
        return title.capitalize().replace("-"," ").replace("_"," ")

    def date_html(self,post):
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
        current_time  = tools.timestamp_to_paris_datetime(post["pub_date"])
        date_iso = current_time.strftime('%Y-%m-%dT%H:%M:00')
        time_published = current_time.strftime('%H:%M')
        # date_link = current_time.strftime('/%Y/%m/')
        year_link = current_time.strftime('/%Y/')
        day_month = current_time.strftime('%d %B')
        
        msg = f'<a href="{year_link}"><time datetime="{date_iso}" title="Publié à {time_published}">{day_month} {current_time.year}</time></a>'

        return msg

    def navigation(self, post):

        main_tag =  post['tagslist'][0]
        if not main_tag:
            return None

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
        post['main'] = self.extract_tags( post['tag'] )[0]
        post['pub_date'] = time.time()
        post['pub_update'] = post['pub_date']
        post['title'] = self.title_formater(post['main']['title'])
        if post['main']['url']:
            if post['main']['url'].startswith("/"):
                post['url'] = post['main']['url'].strip("/")
            else:
                post['url'] = "tag/"+post['main']['url']
        else:
            post['url'] = "tag/"+post['tag']
        return post
    
    def post_comment_total(self, post):
        comment_url = os.path.join(self.config['comments_root'],self.comment_url(post))

        try:
            with open(comment_url, 'r', encoding='utf-8') as file:
                content = file.read()
                count = content.count('---\n\n')
                    
        except FileNotFoundError:
            count = 0
        if count == 0:
            count = "&nbsp;&nbsp;"
        return count    
    

    def get_github_url(self, url):
        if not url.endswith('/'):
            return ""
        parts = url.strip('/').split('/')
        if len(parts) != 4:
            return ""
        # Si format AAAA/MM/JJ/..., on enlève le "JJ"
        if parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
            parts.pop(2)
        parts[-1] += '.md'
        return self.config['github_raw'] + '/'.join(parts)


    def supercharge_post(self, post, maximal=True):
        """Get all post datas (text,tags, medias…)"""

        if isinstance(post, self.db.get_row_factory()):
            post = dict(post)
        elif isinstance(post, list):
            post = dict(post[0])

        path = self.is_post_otherwise_delete(post)
        if not path:
            return None

        post['url'] = self.url(post)
        #print(post)
 
        if maximal:
            content = self.get_post_content(path)
            post['content'] = content['content']
            # html = markdown.markdown(content['content'])

            html = markdown.markdown(
                content['content'], 
                extensions=['fenced_code'],
                extension_configs={
                    'fenced_code': {
                        'lang_prefix': ''  # Supprime le préfixe de langage
                    }
                }
            )

            post['html'] = self.image_manager(html, post)
            post['html'] = self.link_manager(post['html'], post)
            post['description'] = content['description']
            frontmatter = ft.Frontmatter(content['frontmatter'])
            post['frontmatter'] = frontmatter.supercharge()
            #print(post['frontmatter'])
            post['comments'] = self.post_comment_total(post)
        
        post['canonical'] = self.config['domain'] + post['url']
        post['pub_date_str'] = tools.format_timestamp_to_paris_time(post['pub_date'])
        post['pub_update_str'] = tools.format_timestamp_to_paris_time(post['pub_update'])
        post['thumb'] = self.source_image(post['thumb_path'], post)
        post['thumb'] = self.makeJPEGthumb(post['thumb'])
        post['github'] = self.get_github_url(post['url'])

        post['tagslist'] = self.extract_tags(post)
        post['navigation'] = self.navigation(post)
        if post['navigation']:
            post['navigation']['datelink'] = self.date_html(post)
        # print(post['navigation'])
        # print(post['navigation']['maintag'])
        # exit()

        return post

    def supercharge_tag(self, tag, posts=None):
        """Get all tag datas"""

        if isinstance(tag, self.db.get_row_factory()):
            tag = dict(tag)
        elif isinstance(tag, list):
            print("Tag list")

        tag['type'] = 5
        tag['main'] = self.extract_tags(tag['tag'])[0]
        tag['path_md'] = tag['tag'] + "/"
        tag['url'] = self.url(tag)
        tag['title'] = tag['main']['title']
        tag['pub_date'] = tag['pub_update']

        tag['description'] = tag['title']
        tag['canonical'] = self.config['domain'] + tag['url']
        tag['pub_date_str'] = tools.format_timestamp_to_paris_time(tag['pub_date'])
        tag['pub_update_str'] = tools.format_timestamp_to_paris_time(tag['pub_update'])
        tag['thumb'] = self.source_image(tag['thumb_path'], tag)
        if tag['thumb']:
            tag['thumb']["alt"] = tag['thumb_legend']
            tag['thumb']['tag'] = self.img_tag(tag['thumb'])

        menu = []
        if "title_date" in tag:
            menu.append({"title": tag['title_date'], "url": "/tag/"+tag['tag']})
        else:
            menu.append({"title": tag['title'], "url": "/tag/"+tag['tag']})
        if tag['tag'] != "blog":
            menu.append({"title": "Digressions", "url": "/blog/"})
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
                if not post_with_order:
                    total_posts -=1
                    continue
                else:
                    post_with_order['order']=total_posts-index+1

 
            numbered_posts.append(post_with_order)

        tag['posts'] = numbered_posts
      
        return tag
