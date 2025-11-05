import os, re
from datetime import datetime, timezone
import time
import locale
from PIL import Image
import shutil
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse
import tools.frontmatter as ft
import tools.tools as tools


class Web:

    def __init__(self, config, db):
        self.config = config
        self.db = db
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.parent_dir = os.path.dirname(script_dir) + os.sep


    # def url(self, post):

    #     if not post:
    #         return None
    #     post=dict(post)
    #     if 'path_md' not in post:
    #         print(post)
    #         exit("Bad post")
                
    #     base = os.path.basename(post['path_md'])        
    #     file_name_without_extension = os.path.splitext(base)[0]
    #     if post['type'] == 0:

    #         #POST
    #         dt = tools.timestamp_to_paris_datetime(post["pub_date"])
    #         path = dt.strftime("/%Y/%m/%d")
    #         url = "/".join([path.strip("/"), file_name_without_extension]) + "/"
        
    #     elif post['type'] == 1 or post['type'] == 2:

    #         #PAGES
    #         url = os.path.dirname(post['path_md']) + "/" + file_name_without_extension + "/"
    #         #url = file_name_without_extension + "/"
    #         # print(url)
    #         # print(post)
    #         # exit()

    #     elif post['type'] == 5:

    #         #TAGS
    #         url = None
    #         if "main" in post:
    #             main_url = post['main'].get('url',None)
    #             if main_url:
    #                 if main_url.startswith("/"):
    #                     url = main_url.strip("/")
    #                 else:
    #                     url = "tag/"+main_url
    #         if not url:
    #             url = "tag/" + post['path_md']


    #         #url = "tag/" + post['main'].get('url',post['path_md'])

    #     # print(url)
    #     # exit()
    #     return url


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
                # print(post)
                # exit("No media_src")
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
    

    def media_production(self, templates, post) ->int:
        "Genère toutes les images par template"

        soup = BeautifulSoup(post['content'], 'html.parser')
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


    def navigation(self, post):

        if not post:
            raise("Impossible to supercharge - empty post")

        try:

            post=dict(post)

            tagslist = json.loads(post['tagslist'])

            if not 'tagslist':
                return None
            
            main_tag = tagslist[0]

            tag_posts = self.db.get_posts_by_tag(main_tag['tag_slug'])
            url_prev_post = ""
            url_next_post = ""
            total_posts = len(tag_posts)
            i = 0
            # print(total_posts, main_tag['slug'], tagslist)

            for i, tag_post in enumerate(tag_posts):
                # print("OK")
                # print(dict(tag_post))
                if post['id'] == tag_post['id']:
                    # print(i, post['id'], tag_post['id'], total_posts)
                    if i-1>=0:
                        # print("next1")
                        url_next_post =  "/" + tag_posts[i-1]['url'].lstrip("/")
                    else:
                        # print("next2")
                        url_next_post =  "/" + tag_posts[-1]['url'].lstrip("/")
                    if i==total_posts-1:
                        # print("prev1")
                        url_prev_post =  "/" + tag_posts[0]['url'].lstrip("/")
                    else:
                        # print("prev2")
                        url_prev_post =  "/" + tag_posts[i+1]['url'].lstrip("/")
                    break

            r = {"total_posts": total_posts,
                    "prev_url": url_prev_post,
                    "next_url": url_next_post,
                    "order": total_posts-i,
                    "slug": main_tag['tag_slug'],
                    "title": main_tag['tag_title']
                }
            r_post = {}
            r_post['navigation'] = r

            return r_post
            
        except Exception as e:
            print(f"Navigation {e}")
            exit()


    # def tag_2_post(self, post):
    #     post = dict(post)
    #     post['main'] = self.extract_tags( post['tag'] )[0]
    #     post['pub_date'] = time.time()
    #     post['pub_update'] = post['pub_date']
    #     post['title'] = self.title_formater(post['main']['title'])
    #     if post['main']['url']:
    #         if post['main']['url'].startswith("/"):
    #             post['url'] = post['main']['url'].strip("/")
    #         else:
    #             post['url'] = "tag/"+post['main']['url']
    #     else:
    #         post['url'] = "tag/"+post['tag']
    #     return post
    
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
    

    def supercharge_posts(self, template, posts):
        enriched_posts = []
        for post in posts:
            enriched_posts.append( self.supercharge_post(template, post) )
        return enriched_posts


    def supercharge_post(self, template, post):
        """Get all post datas (text,tags, medias…)"""

        if template == None:
            return post
        
        if post == None:
            exit("Big problem avec supercharge post … post None")

        if not isinstance(post, dict):
            post = dict(post)

        if "url" not in post:
            print(post)
            exit("Ce n'est pas un bon post")

        try:

            # post = self.db.row_to_dict(post)

            # post = dict(post)
            # for key in post:
               
            #    print(post[key])

            post['canonical'] = template['domain'] + post['url']
            
            if "content" in post:
                post['content'] = self.image_manager(template, post)

            if 'thumb_path' in post and post['thumb_path']:
                post['thumb'] = self.db.get_image_cache(template['name'], self.media_source_path( post, post['thumb_path'] ) )
            else:
                post['thumb'] =  None

            if "navigation" in post and isinstance(post['navigation'], str):
                post['navigation'] = json.loads(post['navigation'])
            else:
                post['navigation'] = None

            return post
        
        except Exception as e:
            print(post)
            print(f"supercharge_post {e}")
            return None


    def supercharge_tags(self, template, tags):
        enriched_tags = []
        for tag in tags:
            enriched_tags.append( self.supercharge_tag(template, tag) )
        return enriched_tags
    
    def supercharge_tag(self, template, tag, first_post=None):
        # First_post déjà superchargé
        # print(first_post)
        # exit()

        try:

            if isinstance(tag, self.db.get_row_factory()):
                tag = dict(tag)

            if "tag_url" not in  tag:
                print(tag)
                exit("tag_url in tag")
                # tag = self.db.row_to_dict(tag)

            tag['menu'] = self.tag_menu(tag)

            tag['canonical'] = template['domain'] + tag['tag_url'].lstrip("/")

            if "description" not in tag and "tag_title" in tag:
                tag["description"] = tag['tag_title']
            else:
                tag["description"] = ""

            if "navigation" in tag and tag['navigation'] and isinstance(tag['navigation'],str):
                tag['navigation'] = json.loads(tag['navigation'])
            else:
                tag['navigation'] = {}

            if first_post:
                tag['pub_date'] = first_post['pub_date']
                tag['pub_update'] = first_post['pub_update']
                tag['pub_date_str'] = tools.format_timestamp_to_paris_time(tag['pub_date'])
                tag['pub_update_str'] = tools.format_timestamp_to_paris_time(tag['pub_update'])

                tag["thumb_path"] = first_post['thumb_path'],
                tag["thumb_legend"] = first_post['thumb_legend'],

                media_path = self.media_source_path(first_post, first_post['thumb_path'])
                tag['thumb'] = self.db.get_image_cache(template['name'], media_path)

            else:
                if 'thumb_path' in tag and tag['thumb_path']:
                    media_path = self.media_source_path(tag, tag['thumb_path'])
                    tag['thumb'] = self.db.get_image_cache(template['name'], media_path)
                else:
                    tag['thumb'] = None

            return tag

        except Exception as e:
            print(tag)
            print(f"supercharge_post {e}")
            exit()
            # return None


    def tag_menu(self, tag):
        menu = []
        if "tag_title_date" in tag:
            menu.append({"tag_title": tag['tag_title_date'], "tag_url": "/tag/"+tag['tag_slug']})
        else:
            menu.append({"tag_title": tag['tag_title'], "tag_url": "/tag/"+tag['tag_slug']})
        if tag['tag_slug'] != "blog":
            menu.append({"tag_title": "Digressions", "tag_url": "/blog/"})
        if tag['tag_slug'] != "series":
            menu.append({"tag_title": "…", "tag_url": "/series/"})
        index = len(menu)
        if tag['tag_slug'] != "carnets" and index<4:
            menu.insert(index-1, {"tag_title": "Carnets", "tag_url": "/tag/carnet-de-route/"})
        index = len(menu)
        if tag['tag_slug'] != "borntobike" and index<4:
            menu.insert(index-1, {"tag_title": "Vélo", "tag_url": "/tag/borntobike/"})
        return menu
