import mysql.connector
from dotenv import load_dotenv
import os
from markdownify import markdownify as md
import re
import shutil
os.system('clear')

load_dotenv()

if os.getenv('MARKDOWN_DIR'):
    export_folder = os.getenv('MARKDOWN_DIR') + os.sep
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    export_folder = os.path.join(parent_dir,'_export') + os.sep
    
os.makedirs(export_folder, exist_ok=True)

prefix = os.getenv('WP_DB_PREFIX')

# Connexion à la base de données MySQL
conn = mysql.connector.connect(
    host=os.getenv('WP_DB_HOST'),
    port=os.getenv('WP_DB_PORT'),
    user=os.getenv('WP_DB_USER'),
    password=os.getenv('WP_DB_PASSWORD'),
    database=os.getenv('WP_DB_NAME'),
    buffered=True
)

new_img_dir = os.getenv('NEW_IMG_DIR')
old_img_dir = os.getenv('OLD_IMG_DIR')

def get_export_filepath(post, export_dir):
    filename = post['post_name']+".md"
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


def tags_line(post):
    line = ""

    tags = post.get('tags')
    if tags is not None:
        line += "#" + " #".join(tag.strip().replace(" ","_") for tag in tags.split(","))

    cats = post.get('categories')
    if cats is not None:
        line += " #" + " #".join(cat.strip().replace(" ","_") for cat in cats.split(","))

    line += f" #{post['post_date'].year}-{post['post_date'].month}-{post['post_date'].day}"
    
    line=line.replace("  "," ")

    return line


def my_markdown(post):
    text = re.sub(r'<sup>(.*?)</sup>', r'[[SUP:\1]]', post['post_content'])
    text = md(text)
    text = re.sub(r'\[\[SUP:(.*?)\]\]', r'<sup>\1</sup>', text)
    text = text.replace('\n', '\n\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.replace("'", "’")

    text = process_image_urls(text)

    line = tags_line(post)

    return text+f"\n\n{line}"


def find_highest_resolution_image(current_image_path, source_images_dir=old_img_dir, target_images_dir=new_img_dir):
    relative_image_path = current_image_path.lstrip('/')
    relative_image_path = relative_image_path.replace('//','/')
    image_directory = os.path.join(source_images_dir, os.path.dirname(relative_image_path))

    if not os.path.isdir(image_directory):
        return None

    base_name = re.sub(r'-\d+x\d+|\.png|\.jpg|\.jpeg|\.gif|\.webp', '', os.path.basename(relative_image_path))
    files = [f for f in os.listdir(image_directory) if f.startswith(base_name)]
    if len(files)==0:
        return None
    elif len(files)==1:
        highest_res_file = files[0]
    else:
        highest_res_file = max(files, key=lambda f: os.path.getsize(os.path.join(image_directory, f)))

    biggest = os.path.join(os.path.dirname(relative_image_path), highest_res_file)
    source = os.path.join(source_images_dir, biggest)
    target = os.path.join(target_images_dir, biggest)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copy2(source, target)
    return biggest


def process_image_urls(text, base_url='http://localhost:8000'):
    pattern = re.compile(r'(!\[.*?\]\()((https?://[^/]+)?(/[^)]+?\.(jpg|jpeg|png|gif)))(\))')

    def replace_url(match):
        full_url = match.group(2)  # URL complète capturée
        if match.group(3):
            # C'est un chemin absolu avec domaine, remplacer le domaine
            relatif = match.group(4)
        else:
            # C'est un chemin relatif, préserver tel quel
            relatif = full_url

        #Vérifier relatif is the biggest images, sinon remplacé par the bigest
        relatif = find_highest_resolution_image(relatif)

        new_url = f'{base_url}/{relatif}'
        new_url = new_url.replace("//","/")
        
        return f'{match.group(1)}{new_url}{match.group(6)}'

    # Appliquer la fonction replace_url sur toutes les occurrences
    return pattern.sub(replace_url, text)


def get_thumbnail_info(thumbnail_id):
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
            r =  f"![{result['description']}]({result['file_path']})\n\n"
            new_cursor.close()
            
    return process_image_urls(r)

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
    path = get_export_filepath(post, export_folder)
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            file.write(f"# {post['post_title']}\n\n")
            file.write(get_thumbnail_info(post['thumbnail_id']))
            file.write(my_markdown(post)+"\n")
        
        creation = post['post_date'].timestamp()
        update = post['post_modified'].timestamp()
        os.utime(path, (creation, creation))
        os.utime(path, (creation, update))

cursor.close()
conn.close()
