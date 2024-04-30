import yaml
import os, sys, re
from PIL import Image
import logs
from tqdm import tqdm

sys.stdout = logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

os.system('clear')

with open('site.yml', 'r') as file:
    config = yaml.safe_load(file)

total_images = 0
total_images_converted = 0
md_root = None


def convert_to_webp(image_path, webp_path):
    global total_images, total_images_converted
    total_images +=1

    if os.path.isfile(image_path) and (image_path.lower().endswith('.jpeg') or image_path.lower().endswith('.jpg')):
        try:
            # Ouvrir l'image originale
            img = Image.open(image_path)
            total_images_converted += 1
            #exit("stop",webp_path)
            img.save(webp_path, 'WEBP')
            img.close
            os.remove(image_path)
            return True
        except Exception as e:
            print(e)
            exit("First error")
            return False
    else:
        print("Unknown file:", image_path)
        exit()
        return False


def update_image(match):

    if not match:
        exit("Not match!")

    #print(match.group(0))
    image_markdown = match.group(1)
    image_mdpath = match.group(2)
    image_extension = match.group(3)

    image_name = f"{image_mdpath}.{image_extension}"
    webp_name = f"{image_mdpath}.webp"

    image_path = os.path.join(md_root, image_name)
    webp_path = os.path.join(md_root, webp_name)

    if os.path.exists(webp_path):
        if os.path.exists(image_path):
            os.remove(image_path)
        return image_markdown.replace(image_name, webp_name)
    elif convert_to_webp(image_path, webp_path):
        return image_markdown.replace(image_name, webp_name)
    else:
        return image_markdown
        

def remove_image_links(content):
    # Pattern pour identifier les liens d'images pointant vers les domaines spécifiés
    pattern = r'\[(!\[.*?\]\(.*?\))\]\(https?://(?:blog\.)?tcrouzet\.com/.*?\)'
    
    # Remplacer le pattern trouvé par juste l'image markdown
    updated_content = re.sub(pattern, r'\1', content)
    
    return updated_content

def markdown_update(path):

    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()

    new_content = remove_image_links(content)
    
    # Regex pour trouver les images JPEG ou JPG
    pattern = r'(!\[.*?\]\((.*?)\.(jpeg|jpg)\))'
    
    updated_content = re.sub(pattern, update_image, new_content, flags=re.IGNORECASE)    

    if updated_content != content:
        with open(path, 'w', encoding='utf-8') as file:
            file.write(updated_content)
    return True


def count_files(directory):
    file_count = 0
    for root, dirs, files in os.walk(directory):
        file_count += len(files)
    return file_count


pbar = tqdm(total=count_files(config['vault']), desc='Posts:')
count_updated = 0
count_files = 0
for root, dirs, files in os.walk(config['vault']):
    # Exlude images dirs
    dirs[:] = [d for d in dirs if not d.startswith('_i')]

    for file in files:
        if file.endswith('.md'):
            count_files +=1
            md_path = os.path.join(root, file)
            md_root = os.path.dirname(md_path)
            #print(md_path)
            if markdown_update(md_path):
                count_updated += 1
        elif file==".DS_Store":
            continue
        else:
            print("Non MD!",root,file)
        pbar.update(1)
pbar.close()


print("MD files", count_files, "Updated", count_updated)
print("Images:", total_images, "Converted:", total_images_converted)