import mysql.connector
import os, sys
from markdownify import markdownify as md
import re
import shutil
import unidecode
import tools.wp_export_secret as wp_export_secret
import logs

sys.stdout = logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

os.system('clear')

if wp_export_secret.MARKDOWN_DIR:
    export_folder = wp_export_secret.MARKDOWN_DIR + os.sep
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    export_folder = os.path.join(parent_dir,'_export') + os.sep
    
os.makedirs(export_folder, exist_ok=True)

prefix = wp_export_secret.WP_DB_PREFIX

# Connexion à la base de données MySQL
conn = mysql.connector.connect(
    host=wp_export_secret.WP_DB_HOST,
    port=wp_export_secret.WP_DB_PORT,
    user=wp_export_secret.WP_DB_USER,
    password=wp_export_secret.WP_DB_PASSWORD,
    database=wp_export_secret.WP_DB_NAME,
    buffered=True
)

old_img_dir = wp_export_secret.OLD_IMG_DIR
img_sub_dir = wp_export_secret.IMG_SUB_DIR

def get_export_filepath(post, export_dir):
    filename = tag_format(post['post_name'])+".md"
    if post['post_type'] == 'page':
        export_path = os.path.join(export_dir, "page", filename)
        return export_path
    elif post['post_type'] == 'post':
        year = post['post_date'].year
        month = post['post_date'].month
        export_path = os.path.join(export_dir, str(year), str(month), filename)
        return export_path
    else:
        return False

def tag_format(tag):
    tag = unidecode.unidecode(tag.strip())
    tag = tag.lower()
    tag = tag.replace(" ", "_")
    tag = tag.replace("’", "")
    tag = tag.replace("'", "")
    tag = tag.replace("%e2%80%99", "")
    
    return tag

def tags_line(post):
    line = ""

    tags = post.get('tags')
    if tags is not None:
        for tag in tags.split(","):
            tag = tag_format(tag)
            if tag == "serie" or tag == "une":
                continue
            line += f"#{tag} "

    cats = post.get('categories')
    if cats is not None:
        for tag in cats.split(","):
            tag = tag_format(tag)
            if tag == "serie" or tag == "une":
                continue
            line += f"#{tag} "

    if post['post_type'] == 'page':
        line += f"#page "

    if "bookshop" in post['post_content']:
        line += f"#book "

    line += f" #y{post['post_date'].year} #{post['post_date'].year}-{post['post_date'].month}-{post['post_date'].day}-{post['post_date'].hour}h{post['post_date'].minute}"
    
    line=line.replace("  "," ").strip()

    return line

def clean_image_markdown(text):
    pattern = re.compile(r'(!\[.*?\])\((.*?)(\s+".*?")?\)')
    cleaned_text = pattern.sub(r'\1(\2)', text)
    return cleaned_text

def ensure_newlines_after_images(text):
    pattern = re.compile(r'(\[!\[.*?\]\(.*?\)\](?:\(.*?\))?)(?!\n\n)')
    
    def add_newlines(match):
        return match.group(1) + '\n\n'
    
    return pattern.sub(add_newlines, text)


def simplify_image_links(text):
    pattern = re.compile(r'\[\!\[([^\]]+)\]\(([^)]+)\)\]\(([^)]+)\)')

    def replace_link(match):
        alt_text = match.group(1)
        image_path = match.group(2)
        link_target = match.group(3)
        
        image_filename = os.path.splitext(os.path.basename(image_path))[0]
        
        if image_filename.lower() in link_target.lower():
            return f'![{alt_text}]({image_path})'
        else:
            return match.group(0)

    return pattern.sub(replace_link, text)

def my_markdown(post,path_dir):
    text = re.sub(r'<sup>(.*?)</sup>', r'[[SUP:\1]]', post['post_content'])
    text = md(text)
    text = re.sub(r'\[\[SUP:(.*?)\]\]', r'<sup>\1</sup>', text)

    text = text.replace(")\n!",")\n\n!")
    text = text.replace(")\n#",")\n\n#")
    text = text.replace(".\n#",".\n\n#")

    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.replace("'", "’")

    text = clean_image_markdown(text)
    text = process_image_urls(text,path_dir)
    text = simplify_image_links(text)

    text = process_internal_urls(text, path_dir)
    text = process_internal_tagurls(text)
    text = process_internal_pageurls(text, path_dir)

    #text = ensure_newlines_after_images(text)

    line = tags_line(post)

    final = f"# {post['post_title']}\n\n"
    final += get_thumbnail_info(post['thumbnail_id'],path_dir)
    final += f"{text}\n\n{line}\n"

    return final


def clean_relative_img_url(url):
    if url:
        new_url = url.lstrip('/')
        new_url = new_url.replace('//','/')
        return new_url
    return url


def find_highest_resolution_image(current_image_path, path_dir):

    relative_image_path = clean_relative_img_url(current_image_path)
    image_directory = os.path.join(old_img_dir, os.path.dirname(relative_image_path))

    target_dir = os.path.join(path_dir,img_sub_dir)

    if not os.path.isdir(image_directory):
        return None

    base_name = re.sub(r'(-\d+x\d+)(?=\.(?:png|jpg|jpeg|gif|webp)$)', '', os.path.basename(relative_image_path))

    files = [f for f in os.listdir(image_directory) if f.startswith(base_name)]
    if len(files)==0:
        return None
    elif len(files)==1:
        highest_res_file = files[0]
    else:
        highest_res_file = min(files, key=lambda f: (len(f), os.path.getsize(os.path.join(image_directory, f))))

    biggest = os.path.join(os.path.dirname(relative_image_path), highest_res_file)
    source = os.path.join(old_img_dir, biggest)
    target_file = os.path.join(img_sub_dir, highest_res_file)
    target = os.path.join(target_dir, highest_res_file)

    if not os.path.exists(target):
        os.makedirs(target_dir, exist_ok=True)
        shutil.copy2(source, target)
    elif os.path.isfile(target) and os.stat(source).st_mtime > os.stat(target).st_mtime:
        shutil.copy2(source, target)
    return target_file


def process_image_urls(text,path_dir):
    pattern = re.compile(r'(!\[.*?\]\()((https?://[^/]+)?(/[^)]+?\.(jpg|jpeg|png|gif|webp)))(\))')

    def replace_urls(match):

        full_url = match.group(2)  # URL complète capturée

        if match.group(3):
            # C'est un chemin absolu avec domaine, remplacer le domaine
            relatif = match.group(4)
        else:
            # C'est un chemin relatif, préserver tel quel
            relatif = full_url

        relatif = find_highest_resolution_image(relatif,path_dir)
        if not relatif:
            pass
            #print(match)
            #exit()
        relatif = clean_relative_img_url(relatif)
        new_url = relatif
        
        return f'{match.group(1)}{new_url}{match.group(6)}'
    
    return pattern.sub(replace_urls, text)


def relativise_url(link, path_dir):
    target_path = os.path.normpath(link)

    # Construire le chemin complet du répertoire actuel
    current_dir_path = os.path.normpath(path_dir.replace(export_folder,""))
    relative_path = os.path.relpath(target_path, current_dir_path)
    return relative_path

def process_internal_urls(text, path_dir):
    pattern = re.compile(r'\[([^\]]+)\]\((https?:\/\/(?:blog\.)?tcrouzet\.com)(\/\d{4}\/\d{2}\/\d{2}\/[^)]+)\)')

    def replace_url(match):
        full_url = match.group(3)  # URL complète capturée sans le domaine
        obsidian_link = full_url.strip('/')
        pattern = re.compile(r'(\d{4})/(\d{2})/\d{2}/')
        obsidian_link = pattern.sub(lambda m: f"{m.group(1)}/{int(m.group(2))}/", obsidian_link)

        obsidian_link = relativise_url(obsidian_link,path_dir)

        return f'[{match.group(1)}]({obsidian_link}.md)'

    # Appliquer la fonction replace_url sur toutes les occurrences
    return pattern.sub(replace_url, text)

def process_internal_tagurls(text):
    pattern = re.compile(r'\[([^\]]+)\]\(https?:\/\/(?:blog\.)?tcrouzet\.com\/tag\/([^)]+)\)')

    def replace_url(match):
        link_text = match.group(1)
        tag_name = match.group(2)
        tag_name = tag_name.strip("/")
        return f'[{link_text}](#{tag_name})'

    # Appliquer la fonction replace_url sur toutes les occurrences
    return pattern.sub(replace_url, text)

def process_internal_pageurls(text, path_dir):
    pattern = re.compile(r'\[([^\]]+)\]\(https?:\/\/(?:blog\.)?tcrouzet\.com\/([^)]+\/)\)')

    def replace_url(match):
        link_text = match.group(1)
        if link_text.startswith('*') and link_text.endswith('*'):
            star = "*"
        else:
            star = ""
        link_text = link_text.strip("*")
        page_path = match.group(2)
        page_path = page_path.strip("/")

        obsidian_link = relativise_url(f"page/{page_path}",path_dir)

        return f'{star}[{link_text}]({obsidian_link}){star}'

    return pattern.sub(replace_url, text)

def get_thumbnail_info(thumbnail_id,path_dir):
    r = ""
    if thumbnail_id:
        new_cursor = conn.cursor(dictionary=True)
        #print(thumbnail_id)
        query = f"""
        SELECT 
            p.guid AS file_path, 
            pm.meta_value AS description
        FROM 
            {prefix}posts AS p
        LEFT JOIN 
            {prefix}postmeta AS pm ON p.ID = pm.post_id AND pm.meta_key = '_wp_attachment_image_alt'
        WHERE 
            p.ID = {thumbnail_id}
        """
        new_cursor.execute(query)
        result = new_cursor.fetchone()
        if result:
            description = result.get('description', '')
            if description is not None:
                description = description.strip()
            else:
                description = ''
            r =  f"![{description}]({result['file_path']})\n\n"
            new_cursor.close()
            
    return process_image_urls(r,path_dir)


cursor = conn.cursor(dictionary=True)

query = f"""
SELECT
    p.*,
    GROUP_CONCAT(DISTINCT t.name SEPARATOR ', ') AS tags,
    GROUP_CONCAT(DISTINCT c.name SEPARATOR ', ') AS categories,
    pm.meta_value AS thumbnail_id
FROM
    {prefix}posts AS p
LEFT JOIN {prefix}term_relationships AS trt ON p.ID = trt.object_id
LEFT JOIN {prefix}term_taxonomy AS ttt ON trt.term_taxonomy_id = ttt.term_taxonomy_id AND ttt.taxonomy = 'post_tag'
LEFT JOIN {prefix}terms AS t ON ttt.term_id = t.term_id
LEFT JOIN {prefix}term_relationships AS trc ON p.ID = trc.object_id
LEFT JOIN {prefix}term_taxonomy AS ttc ON trc.term_taxonomy_id = ttc.term_taxonomy_id AND ttc.taxonomy = 'category'
LEFT JOIN {prefix}terms AS c ON ttc.term_id = c.term_id
LEFT JOIN {prefix}postmeta AS pm ON p.ID = pm.post_id AND pm.meta_key = '_thumbnail_id'
WHERE
    p.post_status = 'publish'
GROUP BY
    p.ID
"""

#print(query)
cursor.execute(query)

for post in cursor:
    #print(post)
    #exit()

    if post['post_name'] in wp_export_secret.EXCLUDE:
        continue

    path = get_export_filepath(post, export_folder)
    if path:
        path_dir = os.path.dirname(path)
        markdown = my_markdown(post, path_dir)

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as existing_file:
                existing_content = existing_file.read()
            if existing_content == markdown:
                continue
        
        os.makedirs(path_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            file.write(markdown)
        
        creation = post['post_date'].timestamp()
        update = post['post_modified'].timestamp()
        os.utime(path, (creation, update))

cursor.close()
conn.close()