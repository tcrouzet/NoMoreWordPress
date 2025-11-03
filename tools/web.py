import os, re
from datetime import datetime, timezone
import time
import locale
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
        post=dict(post)
        if 'path_md' not in post:
            print(post)
            exit("Bad post")
                
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
            url = None
            if "main" in post:
                main_url = post['main'].get('url',None)
                if main_url:
                    if main_url.startswith("/"):
                        url = main_url.strip("/")
                    else:
                        url = "tag/"+main_url
            if not url:
                url = "tag/" + post['path_md']


            #url = "tag/" + post['main'].get('url',post['path_md'])

        # print(url)
        # exit()
        return url


    def comment_url(self, post):

        if not post:
            print("No post")
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
        
        elif post['type'] == 1 or post['type'] == 2 or post['type'] == 5:

            #PAGES
            url = os.path.dirname(post['path_md']) + "/" + file_name_without_extension + ".md"
        
        else:

            url = None

        return url
    

    def url_image_relatif(self, src, post):
        """retourne url relatif d'un media"""
        if post['type'] == 5:
            exit("Must not occur")
            # filename = os.path.basename(post['thumb_path'])
            # path = self.normalize_month(os.path.dirname(post['post_md']))
        else:
            # print("-- Type Autre --")
            date = tools.timestamp_to_paris_datetime(post["pub_date"])
            path = date.strftime("%Y/%m/")
            filename = src.replace(self.config['vault_img'], "")
        
        url = os.path.join("/", self.config['images_dir'].strip("/"), path, filename)
        # print("url_img_relatif",url)
    
        return url

    
    def media_target_path(self, export_path, url_media_relatif):
        return os.path.join( export_path, url_media_relatif.strip("/"))

    def media_source_path(self, post, media_src_file):
        try:
            post=dict(post)
            if not media_src_file:
                print(post)
                exit("No media_src")
                return None
            base_dir_name =  post['path_md']
            dirname = os.path.dirname(base_dir_name)
            return os.path.join( self.config['vault'], dirname, media_src_file )
        except Exception as e:
            print(f"Media source for {media_src_file}")
            print(dict(post))
            exit()


    def add_before_extension(self, url, text):
        if text=="max_size":
            return url
        return f"{os.path.splitext(url)[0]}-{text}{os.path.splitext(url)[1]}".rstrip("/")
    
    # copy un media s'il existe pas
    def copy_if_needded(self, media_source_path, media_target_path):

        if not os.path.exists(media_source_path):
            print("Can't find:", media_source_path)
            raise  FileNotFoundError

        if not os.path.exists(media_target_path):
            destination_dir = os.path.dirname(media_target_path)
            os.makedirs(destination_dir, exist_ok=True)
            shutil.copy2(media_source_path, media_target_path)


    def relativise_path(self, export_path, path):
        return path.replace(export_path,"").rstrip("/")


    def normalize_month(self, path):
        parts = path.split('/')
        if len(parts) < 2:
            return path
        year = parts[0]
        month = parts[1]
        month_padded = month.zfill(2)
        normalized_parts = [year, month_padded] + parts[2:]
        return '/'.join(normalized_parts)


    def source_images(self, templates, media_src_file, post, legend="", thumb=False) ->dict:
        """Media manager
        media_src_file _i/image.webp"""

        if media_src_file is None:
            print(dict(post))
            exit()
        
        if not media_src_file:
            return None
        
        if media_src_file=="None":
            return None

        media_source_path = self.media_source_path( post, media_src_file )
        url_media_relatif = self.url_image_relatif( media_src_file, post)

        images = {'media_source_path': media_source_path}
        try:
            for template in templates:

                media_target_path = self.media_target_path(template['export'], url_media_relatif)
                # print("target:", media_target_path)

                if media_src_file.endswith('.mp3'):
                    self.copy_if_needded(media_source_path, media_target_path)
                    template_image = {
                        "target_path": media_target_path,
                        "format": "audio/mpeg",
                        "url": url_media_relatif,
                        "legend": legend
                    }

                elif media_src_file.endswith('.pdf'):
                    self.copy_if_needded(media_source_path, media_target_path)
                    template_image = {
                        "target_path": media_target_path,
                        "format": "application/pdf",
                        "url": url_media_relatif,
                        "legend": legend
                    }

                else:

                    with Image.open(media_source_path) as img:

                        (width, height) = img.size
                        final_max_width = final_max_height = None

                        if img.format in ["GIF","PNG"]:
                            # print("Format:",img.format)
                            self.copy_if_needded(media_source_path, media_target_path)
                            template_image = {
                                "width": width,
                                "height": height,
                                "format": "image/"+img.format.lower(),
                                "url": url_media_relatif,
                                "url_medium": '',
                                "url_small": '',
                                "jpeg": url_media_relatif,
                                "legend": legend
                            }

                        # Webp et JPEG
                        max_size = int(template['image_max_size'])
                        min_size = int(template['image_min_size'])
                        
                        sizes = {}
                        # print(width, max_size, min_size)
                        if width > max_size and max_size > 1024:
                            # print("cas 1")
                            sizes = {'max': 'resize', 'medium': 'resize', 'small': 'resize'}
                        elif width > 1024 and max_size > 1024:
                            # print("cas 2")
                            sizes = {'max': None, 'medium': 'resize', 'small': 'resize'}
                        elif width > 1024 and max_size <= 1024:
                            # print("cas 3")
                            sizes = {'max': 'resize', 'small': 'resize'}
                        else:
                            # print("case 1")
                            sizes = {'max': None, 'small': 'resize'}

                        # print(sizes)

                        # Création des versions redimensionnées de l'image
                        for size, value in sizes.items():

                            # print("Size:", size, "Value:", value)
                            if value is None:
                                self.copy_if_needded(media_source_path, media_target_path)
                                sizes[size] = self.relativise_path(template['export'], media_target_path)
                                if size == 'max':
                                    final_max_width = width
                                    final_max_height = height
                                continue
                            
                            # resize needed

                            if size == 'max':
                                new_path = media_target_path
                                new_width = max_size
                                ratio = (new_width / float(width))
                                new_height = int((float(height) * float(ratio)))
                                final_max_width = max_size
                                final_max_height = new_height
                            else:
                                new_path = self.add_before_extension(media_target_path,size)
                                if size=="small":
                                    new_width = int(min_size)
                                else:
                                    new_width = 1024
                                ratio = (new_width / float(width))
                                new_height = int((float(height) * float(ratio)))

                            if os.path.exists(new_path):
                                sizes[size] = self.relativise_path(template['export'], new_path)
                                # print(f"size {size} exist")
                                continue

                            destination_dir = os.path.dirname(new_path)
                            os.makedirs(destination_dir, exist_ok=True)

                            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            img_resized.save(new_path)
                            sizes[size] = self.relativise_path(template['export'], new_path)

                            # print("Fin for")
                        
                        template_image = {
                            "width": final_max_width,
                            "height": final_max_height,
                            "format": "image/"+img.format.lower(),
                            "url": sizes.get('max',''),
                            "url_medium": sizes.get('medium', '' ),
                            "url_small": sizes.get('small', ''),
                            "jpeg": "",
                            "legend": legend,
                        }

                        if thumb:
                            template_image['jpeg'] = self.makeJPEGthumb(template, template_image)
                        else:
                            template_image['jpeg'] =  template_image['url']
                    
                images[template['name']] = template_image
        
            return images

        except Exception as e:
            print(f"bug traitement image {media_source_path} media_file {media_src_file} post_type {post['type']}",e)
            exit()
    

    def makeJPEGthumb(self, template, image) ->dict:
        """Make jpeg for facebook share"""

        if not image:
            return ""

        # print(thumb)
        jpeg_file =  f"{os.path.splitext(image['url'])[0]}.jpeg".strip("/")
        jpeg_path = os.path.join(template['export'], jpeg_file)
        thumb = f"/{jpeg_file}"
        # print(thumb['jpeg'])
        # print(jpeg_path)

        if template['jpeg_thumb'] and image['format'] == "image/webp" and not os.path.exists(jpeg_path) :
            # Make jpeg file
            try:

                if image['url_medium']:
                    path = os.path.join(template['export'], image['url_medium'].strip("/"))
                else:
                    path = os.path.join(template['export'], image['url'].strip("/"))

                img = Image.open(path)
                     
                img.convert("RGB").save(jpeg_path, 'JPEG', quality=60, optimize=True, progressive=True)
                
                # Fermer l'image
                img.close()
                
            except Exception as e:
                print(f"Erreur lors de la conversion thumb JEPG template: {template['name']} : {e}")
                print(image)
                exit()
            
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


    def source_post_path(self, post):
        if not post:
            return None
        path = os.path.join(self.config['vault'], post['path_md'])
        if post["type"]<3:
            if not os.path.exists(path):
                exit("Non existing post!!!!")
                # self.db.delete_post(post)
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


    def media_production(self, templates, html, post) ->int:
        "Genère toutes les images par template"

        soup = BeautifulSoup(html, 'html.parser')
        ps = soup.find_all('p')
        
        index = 0
        for p in ps:
            
            img = p.find('img')
            if img:
                src = img.get('src', None)
                if src:
                    data = self.source_images(templates, img.get('src'), post, legend=img.get('alt', ''))
                    if data:
                        if self.db.insert_image_cache(data):
                            index +=1

        #thumb
        if post['thumb_path']:
            data = self.source_images(templates, post['thumb_path'], post, legend=post['thumb_legend'], thumb=True)
            if data:
                if self.db.insert_image_cache(data):
                    index +=1

        return index


    def image_manager(self, template, post) ->str:
        """Optimize HTML for images"""

        soup = BeautifulSoup(post['content'], 'html.parser')
        ps = soup.find_all('p')
        
        index = 0
        for p in ps:
            
            img = p.find('img')
            if img:
                src = img.get('src', None)
                if src:
                    source_path = self.media_source_path( post, img['src'] )
                else:
                    continue
                index +=1
                if source_path:
                    img_data = self.db.get_image_cache(template['name'], source_path)
                else:
                    continue
                if img_data:

                    alt_text = img.get('alt','')

                    if img_data["format"].startswith("image/"):

                        if img_data['width'] < img_data['height']:
                            myclass = 'portrait'
                            myclasslegend = 'legend-center'
                        else:
                            myclass = ''
                            myclasslegend = ''
                        if img_data['width'] < 1024:
                            myclass += ' small'
                            myclasslegend = 'legend-center'

                        if "png" in img_data["format"]:
                            myclasslegend = 'legend-center'

                        srcset_parts = [f"{img_data['url']} {img_data['width']}w"]
                        if img_data['url_medium']:
                            srcset_parts.append(f"{img_data['url_medium']} 1024w")
                        if img_data['url_small']:
                            srcset_parts.append(f"{img_data['url_small']} {template['image_min_size']}")

                        new_div = soup.new_tag('figure')
                        img_attrs = {
                            'src': img_data['url'],
                            'alt': alt_text,
                            'width': img_data['width'],
                            'height': img_data['height'],
                            'loading': 'lazy',
                            'decoding': 'async',
                            'srcset': ', '.join(srcset_parts)
                            # 'sizes': f'(max-width: {img_data['width']}px) 100vw, {img_data['width']}px'
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
    

    def link_manager(self, html, post) ->str:

        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a')

        # Canonical domaine (ex: https://tcrouzet.com → tcrouzet.com)
        site_domain = self.config["canonical_domain"]
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

    
    def extract_tags(self, post) ->list:
        
        if 'tags' in post:
            tags = json.loads(post['tags'])
        else:
            return None
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

    def date_html(self,post) ->str:
        current_time = tools.timestamp_to_paris_datetime(post["pub_date"])
        date_iso = current_time.strftime('%Y-%m-%dT%H:%M:00')
        time_published = current_time.strftime('%H:%M')
        year_link = current_time.strftime('/%Y/')
        day_month = current_time.strftime('%d %B')
        
        msg = f'<a href="{year_link}"><time datetime="{date_iso}" title="Publié à {time_published}">{day_month} {current_time.year}</time></a>'

        return msg


    def navigation(self, post, tagslist):

        try:

            post=dict(post)
            main_tag = tagslist[0]
            
            tag_posts = self.db.get_posts_by_tag(main_tag['slug'])
            url_prev_post = ""
            url_next_post = ""
            total_posts = len(tag_posts)
            i = 0
            # print(total_posts, main_tag['slug'], tagslist)

            for i, tag_post in enumerate(tag_posts):
                if post['id'] == tag_post['id']:
                    print(i, post['id'], tag_post['id'], total_posts)
                    if i-1>=0:
                        # print("next1")
                        url_next_post =  "/" + tag_posts[i-1]['url']
                    else:
                        # print("next2")
                        url_next_post =  "/" + tag_posts[-1]['url']
                    if i==total_posts-1:
                        # print("prev1")
                        url_prev_post =  "/" + tag_posts[0]['url']
                    else:
                        # print("prev2")
                        url_prev_post =  "/" + tag_posts[i+1]['url']
                    break

            return {"total_posts": total_posts,
                    "prev_url": url_prev_post,
                    "next_url": url_next_post,
                    "order": total_posts-i,
                    "slug": main_tag['slug'],
                    "title": main_tag['title']
                }
        except Exception as e:
            print(f"Navigation {e}")


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
        if not url:
            return ""
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


    def supercharge_post(self, template, post):
        """Get all post datas (text,tags, medias…)"""

        try:
            if isinstance(post, self.db.get_row_factory()):
                post = dict(post)
            else:
                exit("Bug supercharge")
            # elif isinstance(post, list):
            #     post = dict(post[0])

            post['canonical'] = template['domain'] + post['url']
            post['content'] = self.image_manager(template, post)
            if post['thumb_path']:
                post['thumb'] = self.db.get_image_cache(template['name'], self.media_source_path( post, post['thumb_path'] ) )
            else:
                post['thumb'] =  None

            return post
        
        except Exception as e:
            print(template)
            print(post["url"])
            print(f"supercharge {e}")


    def supercharge_post_non_template(self, post):

        if not post:
            raise("Impossible to supercharge - empty post")

        r_post = {}
        source_path = self.source_post_path(post)

        r_post['url'] = self.url(post)

        content = self.get_post_content(source_path)

        if post['type']==2 and 'frontmatter' in content:
            frontmatter = ft.Frontmatter(content['frontmatter'])
            r_post['frontmatter'] = frontmatter.supercharge()
        else:
            r_post['frontmatter'] = None

        if 'description' in content:
            r_post['description'] = content['description']
        else:
            r_post['description'] = ""

        r_post['pub_date_str'] = tools.format_timestamp_to_paris_time(post['pub_date'])
        r_post['pub_update_str'] = tools.format_timestamp_to_paris_time(post['pub_update'])

        r_post['github'] = self.get_github_url(r_post['url'])

        r_post['tagslist'] = self.extract_tags(post)

        r_post['datelink'] = self.date_html(post)

        r_post['navigation'] = self.navigation(post, r_post['tagslist'])

        r_post['content'] = markdown.markdown(
            content['content'], 
            extensions=['fenced_code'],
            extension_configs={
                'fenced_code': {
                    'lang_prefix': ''  # Supprime le préfixe de langage
                }
            }
        )

        r_post['content'] = self.link_manager(r_post['content'], post)

        return r_post 


    def supercharge_tag(self, template, tag, posts=None):
        """Get all tag datas"""

        if isinstance(tag, self.db.get_row_factory()):
            tag = dict(tag)
        elif isinstance(tag, list):
            print("Tag list")
            exit()

        # print(tag)

        tag['type'] = 5
        tag['main'] = self.extract_tags(tag['tag'])[0]
        # print("Supercharge path_md", tag['post_md'], tag['thumb_path'])
        tag['path_md'] = tag['tag'] + "/"
        tag['url'] = self.url(tag)
        tag['title'] = tag['main']['title']
        tag['pub_date'] = tag['pub_update']

        tag['description'] = tag['title']
        tag['canonical'] = template['domain'] + tag['url']
        tag['pub_date_str'] = tools.format_timestamp_to_paris_time(tag['pub_date'])
        tag['pub_update_str'] = tools.format_timestamp_to_paris_time(tag['pub_update'])
        # print("--TAG--", tag['post_md'], tag['thumb_path'])
        tag['thumb'] = self.source_image(template, tag['thumb_path'], tag)
        # print("after")
        if tag['thumb']:
            tag['thumb']["alt"] = tag['thumb_legend']
            # tag['thumb']['tag'] = self.img_tag(tag['thumb'])

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

        # print(tag['tag'])
        # print(list(posts))
        if not posts:
            posts = self.db.get_posts_by_tag(tag['tag'])
            if not posts:
                exit("BUG tag")

        
        total_posts = len(posts)
        numbered_posts = []
        for index, post in enumerate(posts, start=1):

            post=dict(post)

            if post["type"]==5:
                # print("Type 5")
                post = self.tag_2_post(post)
                post['path_md'] = tag['post_md']

                post_with_order = self.supercharge_post(template, post, 1)
                post_with_order['order']=post['count']

            else:
                # print("Autre type")
                # print(post)
                post_with_order = self.supercharge_post(template, post, 1)
                if not post_with_order:
                    total_posts -=1
                    continue
                else:
                    post_with_order['order']=total_posts-index+1
 
            numbered_posts.append(post_with_order)

        tag['posts'] = numbered_posts
        # print(f"Len posts {len(numbered_posts)}")
      
        return tag