import os, re
from datetime import datetime, timedelta, timezone
from PIL import Image
import shutil
from bs4 import BeautifulSoup
import json
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree
import frontmatter as ft
import tools


def is_upcoming_event(frontmatter):
    """Retourne vrai tant que la date de fin, ou de début, n'est pas passée."""
    value = frontmatter.get('end_date') or frontmatter.get('date')
    if not value:
        return False
    if isinstance(value, datetime):
        event_end = value
        date_only = False
    else:
        raw = str(value).strip().strip("'\"‘’")
        date_only = bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw))
        try:
            event_end = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except ValueError:
            return False
    if event_end.tzinfo is None:
        event_end = event_end.replace(tzinfo=timezone.utc)
    if date_only:
        event_end += timedelta(days=1)
    return event_end > datetime.now(timezone.utc)


def svg_dimensions(path):
    """Lit les dimensions d'affichage d'un SVG sans le modifier."""
    root = ElementTree.parse(path).getroot()
    view_box = root.get('viewBox')
    if view_box:
        values = re.split(r'[\s,]+', view_box.strip())
        if len(values) == 4:
            return max(1, round(float(values[2]))), max(1, round(float(values[3])))

    def numeric_dimension(name):
        value = root.get(name, '')
        match = re.match(r'\s*([0-9]+(?:\.[0-9]+)?)', value)
        return max(1, round(float(match.group(1)))) if match else None

    return numeric_dimension('width') or 1, numeric_dimension('height') or 1


class Web:

    def __init__(self, config, db):
        self.config = config
        self.db = db
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.parent_dir = os.path.dirname(script_dir) + os.sep
    

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
        return os.path.join(export_path, unquote(url_media_relatif).strip("/"))

    def media_source_path(self, post, media_src_file):
        try:
            post=dict(post)
            if not media_src_file:
                return None
            if media_src_file.startswith((
                'http://', 'https://', '//', 'data:'
            )):
                return None
            base_dir_name =  post['path_md']
            dirname = os.path.dirname(base_dir_name)
            return os.path.join(
                self.config['vault'], dirname, unquote(media_src_file)
            )
        except Exception as e:
            print(f"Media source path {e}")
            print(f"{media_src_file} {base_dir_name} {dirname}")
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
        if media_source_path is None:
            return None
        url_media_relatif = self.url_image_relatif( media_src_file, post)

        images = {
            'media_source_path': media_source_path,
            'media_size': os.path.getsize(media_source_path)
        }
        try:
            for template in templates:

                media_target_path = self.media_target_path(template['export'], url_media_relatif)
                # print("target:", media_target_path)

                extension = os.path.splitext(media_src_file)[1].lower()

                if extension == '.mp3':
                    self.copy_if_needded(media_source_path, media_target_path)
                    template_image = {
                        "target_path": media_target_path,
                        "format": "audio/mpeg",
                        "url": url_media_relatif,
                        "legend": legend
                    }

                elif extension == '.pdf':
                    self.copy_if_needded(media_source_path, media_target_path)
                    template_image = {
                        "target_path": media_target_path,
                        "format": "application/pdf",
                        "url": url_media_relatif,
                        "legend": legend
                    }

                elif extension == '.svg':
                    width, height = svg_dimensions(media_source_path)
                    self.copy_if_needded(media_source_path, media_target_path)
                    template_image = {
                        "target_path": media_target_path,
                        "width": width,
                        "height": height,
                        "format": "image/svg+xml",
                        "url": url_media_relatif,
                        "url_medium": '',
                        "url_small": '',
                        "jpeg": url_media_relatif,
                        "legend": legend,
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

                        else:

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

        if (
            template['jpeg_thumb']
            and image['format'] in ("image/webp", "image/avif")
            and not os.path.exists(jpeg_path)
        ):
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

                    alt_text = img.get('alt', '')
                    width_percent = None
                    width_match = re.search(r'(?:^|\s)(\d{1,3})%\s*$', alt_text)
                    if width_match:
                        requested_width = int(width_match.group(1))
                        if 1 <= requested_width <= 100:
                            width_percent = requested_width
                            alt_text = alt_text[:width_match.start()].rstrip()
                    is_background = alt_text.endswith(' background')

                    if img_data["format"].startswith("image/"):
                        is_svg = img_data["format"] == "image/svg+xml"

                        if img_data['width'] <= img_data['height'] or alt_text.endswith(" poster"):
                            myclass = 'portrait'
                            myclasslegend = 'legend-center'
                        else:
                            myclass = ''
                            myclasslegend = ''
                        if img_data['width'] < 1024 and not is_svg:
                            myclass += ' portrait'
                            myclasslegend = 'legend-center'

                        if "png" in img_data["format"]:
                            myclasslegend = 'legend-center'

                        srcset_parts = [f"{img_data['url']} {img_data['width']}w"]
                        if img_data['url_medium']:
                            srcset_parts.append(f"{img_data['url_medium']} 1024w")
                        if img_data['url_small']:
                            srcset_parts.append(f"{img_data['url_small']} {template['image_min_size']}w")

                        alt_text = (
                            alt_text
                            .removesuffix(" background")
                            .removesuffix(" poster")
                            .strip()
                        )
                        new_div = soup.new_tag('figure')
                        figure_classes = []
                        if img_data['height'] > img_data['width']:
                            figure_classes.append('portrait-figure')
                        if is_background:
                            figure_classes.append('background-figure')
                        if figure_classes:
                            new_div['class'] = figure_classes
                        img_attrs = {
                            'src': img_data['url'],
                            'alt': alt_text,
                            'width': img_data['width'],
                            'height': img_data['height'],
                        }
                        if width_percent:
                            img_attrs['style'] = (
                                'width:100%;'
                                f'max-width:{width_percent}%;'
                                'height:auto;'
                                'margin-left:auto;margin-right:auto'
                            )

                        #Not small web
                        if template['sizes']:
                            img_attrs['loading'] = 'lazy'
                            img_attrs['decoding'] = 'async'
                            if not is_svg:
                                img_attrs['srcset'] = ', '.join(srcset_parts)
                                img_attrs['sizes'] = template['sizes']

                        if myclass:
                            img_attrs['class'] = myclass

                        new_img = soup.new_tag('img', **img_attrs)

                        new_div.append(new_img)

                        new_legend = soup.new_tag('figcaption')
                        new_legend.string = alt_text
                        new_div.append(new_legend)

                        a = p.find('a')
                        if a:
                            a['target'] = '_blank'
                            a.clear() 
                            a.append(new_div)
                            p.replace_with(a)
                        else:
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

            if not tagslist:
                return {}
            
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
                    "title": main_tag['tag_title'],
                    "url": main_tag['tag_url']
                }
            r_post = {}
            r_post['navigation'] = r

            return r_post
            
        except Exception as e:
            print(f"Navigation {e}")
            exit()    

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
            exit("Ce n'est pas un bon post")

        try:

            post['canonical'] = template['domain'] + post['url'].lstrip("/")
            if 'pub_date' in post:
                post['month'] = tools.month_year(post['pub_date'])
            else:
                post['month'] = ""
            
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

            if "tagslist" in post and isinstance(post['tagslist'], str):
                post['tagslist'] = json.loads(post['tagslist'])

            if "frontmatter" in post and isinstance(post['frontmatter'], str):
                post['frontmatter'] = json.loads(post['frontmatter'])

            post['pub_date_label'] = (
                tools.timestamp_date_label(post['pub_date'])
                if post.get('pub_date')
                else ''
            )
            post['event_date_label'] = ''
            if post.get('frontmatter') and post['frontmatter'].get('date'):
                post['event_date_label'] = tools.event_date_label(
                    post['frontmatter']['date']
                )
            tag_slugs = {
                tag.get('tag_slug') for tag in (post.get('tagslist') or [])
            }
            post['event_schema'] = None
            event_config = self.config.get('events')
            if (
                event_config
                and
                post.get('frontmatter')
                and post['frontmatter'].get('date')
                and is_upcoming_event(post['frontmatter'])
            ):
                frontmatter = post['frontmatter']
                event = {
                    '@context': 'https://schema.org',
                    '@type': 'Event',
                    '@id': post['canonical'] + '#event',
                    'mainEntityOfPage': {
                        '@type': 'WebPage',
                        '@id': post['canonical'] + '#primary',
                    },
                    'name': frontmatter.get('metatitle') or post['title'],
                    'description': (
                        frontmatter.get('metadescription')
                        or post.get('description')
                        or post['title']
                    ),
                    'url': post['canonical'],
                    'startDate': frontmatter['date'],
                    'eventAttendanceMode': (
                        'https://schema.org/OfflineEventAttendanceMode'
                    ),
                    'eventStatus': frontmatter.get(
                        'event_status', 'https://schema.org/EventScheduled'
                    ),
                }
                if frontmatter.get('end_date'):
                    event['endDate'] = frontmatter['end_date']
                if post.get('thumb') and post['thumb'].get('jpeg'):
                    event['image'] = (
                        template['domain'].rstrip('/')
                        + post['thumb']['jpeg']
                    )
                if event_config.get('location'):
                    location = dict(event_config['location'])
                    location['@type'] = 'Place'
                    if location.get('address'):
                        address = dict(location['address'])
                        address['@type'] = 'PostalAddress'
                        location['address'] = address
                    event['location'] = location
                if event_config.get('organizer'):
                    event['organizer'] = {
                        '@type': 'Organization',
                        **event_config['organizer'],
                    }
                offer_url = frontmatter.get('header_link')
                if offer_url and offer_url != '#':
                    event['offers'] = {
                        '@type': 'Offer',
                        'url': offer_url,
                        'price': str(event_config.get('price', '')),
                        'priceCurrency': event_config.get(
                            'priceCurrency', 'EUR'
                        ),
                        'availability': 'https://schema.org/InStock',
                    }
                post['event_schema'] = event
            post['display_date_label'] = ''
            if 'grands_departs' in tag_slugs and post['event_date_label']:
                post['display_date_label'] = post['event_date_label']
            elif post.get('type') == 0:
                post['display_date_label'] = post['pub_date_label']

            return post
        
        except Exception as e:
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

            tag['is_tag'] = True

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

            tag['frontmatter'] = None

            if first_post:
                tag['pub_date'] = first_post['pub_date']
                tag['pub_update'] = first_post['pub_update']
                tag['pub_date_str'] = tools.format_timestamp_to_paris_time(tag['pub_date'])
                tag['pub_update_str'] = tools.format_timestamp_to_paris_time(tag['pub_update'])

                tag["thumb_path"] = first_post['thumb_path']
                tag["thumb_legend"] = first_post['thumb_legend']

                media_path = self.media_source_path(first_post, first_post['thumb_path'])
                tag['thumb'] = self.db.get_image_cache(template['name'], media_path)

            else:
                if 'thumb_path' in tag and tag['thumb_path']:
                    media_path = self.media_source_path(tag, tag['thumb_path'])
                    tag['thumb'] = self.db.get_image_cache(template['name'], media_path)
                else:
                    tag['thumb'] = None

            # Tag CSS
            tag['css'] = ""
            if 'dir' in template:
                css_path = os.path.join(template['dir'],f"style_{tag['tag_slug']}.css")
                tag['css'] = tools.get_css(css_path)

            return tag

        except Exception as e:
            print(tag)
            print(f"supercharge_tag {e}")
            exit()
            # return None


    def tag_menu(self, tag):
        menu = []
        if "tag_title_date" in tag:
            menu.append({"tag_title": tag['tag_title_date'], "tag_url": tag['tag_slug']})
        else:
            menu.append({"tag_title": tag['tag_title'], "tag_url": tag['tag_slug']})
        if tag['tag_slug'] != "blog":
            blog_tag = self.db.tag_2_dict("blog")
            menu.append({
                "tag_title": blog_tag['tag_title'],
                "tag_url": blog_tag['tag_url']
            })
        if tag['tag_slug'] != "series":
            menu.append({"tag_title": "…", "tag_url": "/series/"})
        index = len(menu)
        if tag['tag_slug'] != "carnets" and index<4:
            menu.insert(index-1, {"tag_title": "Carnets", "tag_url": "/carnet-de-route/"})
        index = len(menu)
        if tag['tag_slug'] != "borntobike" and index<4:
            menu.insert(index-1, {"tag_title": "Vélo", "tag_url": "/borntobike/"})
        return menu
