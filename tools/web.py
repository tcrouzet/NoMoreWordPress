import os
from datetime import datetime, timezone
import pytz
from PIL import Image
import markdown
import shutil
from bs4 import BeautifulSoup


class Web:

    def __init__(self, config):
        self.config = config

        # script_dir = os.path.dirname(os.path.abspath(__file__))
        # parent_dir = os.path.dirname(script_dir) + os.sep
        # script_dir = parent_dir

        # self.template_dir = os.path.join(parent_dir, "templates", self.config['template'])


    def format_timestamp_to_paris_time(self, timestamp):
        utc_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        paris_time = utc_time.astimezone(pytz.timezone('Europe/Paris'))
        return  paris_time.isoformat()


    def url(self, post):
        date = datetime.fromtimestamp(post['pub_date'])
        path = date.strftime("/%Y/%m/%d")
        file_name_without_extension = os.path.splitext(os.path.basename(post['path_md']))[0]
        url = '/'.join([path.strip('/'), file_name_without_extension]) + "/"
        return url


    def url_image(self, src, post):
        date = datetime.fromtimestamp(post['pub_date'])
        path = date.strftime("%Y/%m/")
        url = self.config['images_dir'] + path + src.replace(self.config['vault_img'],"")
        return url

    def add_before_extension(self, url, text):
        return f"{os.path.splitext(url)[0]}-{text}{os.path.splitext(url)[1]}"

    def source_image(self, src, post):
        path = os.path.join( self.config['vault'], os.path.dirname(post['path_md']), src )
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
            with open(path, "r", encoding="utf-8") as file:
                lines = file.readlines()

            for i, line in enumerate(lines):
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
            return {"content": md.strip(), "description":self.resume_paragraph(lines[0].strip())}

        except Exception as e:
            return None
        
    def image_manager(self, html, post):

        soup = BeautifulSoup(html, 'html.parser')
        images = soup.find_all('p')
        
        index = 0
        for p in images:
            
            img = p.find('img')
            if img:
                index +=1
                img_data = self.source_image(img['src'], post)
                alt_text = img.get('alt','')

                print(img_data)
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

        return str(soup)


    def supercharge_post(self, post):
        post = dict(post)
        post['url'] = self.url(post)
        content = self.get_post_content(post)
        post['content'] = content['content']
        html = markdown.markdown(content['content'])
        post['html'] = self.image_manager(html, post)
        post['description'] = content['description']
        post['canonical'] = self.config['domain'] + post['url']
        post['pub_date_str'] = self.format_timestamp_to_paris_time(post['pub_date'])
        post['pub_update_str'] = self.format_timestamp_to_paris_time(post['pub_update'])
        post['thumb'] = self.source_image(post['thumb_path'], post)
        #print(post)
        #exit()
        return post
