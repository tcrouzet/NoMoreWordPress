import os
from datetime import datetime, timezone
import pytz


def format_timestamp_to_paris_time(timestamp):
    utc_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    paris_time = utc_time.astimezone(pytz.timezone('Europe/Paris'))
    return  paris_time.isoformat()


def url(post):
    date = datetime.fromtimestamp(post['pub_date'])
    path = date.strftime("/%Y/%m/%d")
    file_name_without_extension = os.path.splitext(os.path.basename(post['path_md']))[0]
    url = '/'.join([path.strip('/'), file_name_without_extension]) + "/"
    return url

def url_image(src, post, config):
    date = datetime.fromtimestamp(post['pub_date'])
    path = date.strftime("%Y/%m/")
    url = config['images_dir'] + path + src.replace(config['vault_img'],"")
    return url


def resume_paragraph(paragraph):
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


def get_post_content(post, config):
    path = os.path.join(config['vault'], post['path_md'])
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
        return {"content": md.strip(), "description":resume_paragraph(lines[0].strip())}

    except Exception as e:
        return None
    

def supercharge_post(post, config):
    post = dict(post)
    post['url'] = url(post)
    content = get_post_content(post, config)
    post['content'] = content['content']
    post['description'] = content['description']
    post['canonical'] = config['domain'] + post['url']
    post['pub_date_str'] = format_timestamp_to_paris_time(post['pub_date'])
    post['pub_update_str'] = format_timestamp_to_paris_time(post['pub_update'])
    post['thumb_url'] = url_image(post['thumb_path'], post, config)
    #print(post)
    #exit()
    return post
