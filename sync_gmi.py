import os, sys, re
from datetime import date
import shutil
import tools.tools
import tools.logs
import tools.github
import tools.sync_files
from md2gemini import md2gemini
from PIL import Image, ImageOps, ImageEnhance, ImageDraw

import numpy as np
import subprocess

sys.stdout = tools.logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

config = tools.tools.site_yml('site.yml')

def mount_synology_volume():
    server_address = "smb://NasZone._smb._tcp.local/Web"
    try:
        subprocess.run(["osascript", "-e", f'mount volume "{server_address}"'], check=True)
        print("Volume Synology monté avec succès.")
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du montage du volume Synology: {e}")


# https://github.com/makew0rld/md2gemini
def markdown_to_gemini(markdown_text, year, month):

    title = None
    lines = markdown_text.split('\n')    
    # Find first title
    for line in lines:
        if line.startswith('# ') and not title:
            title = line.strip('# ').strip()
            break

    # Supprime exposant
    markdown_text = markdown_text.replace("<sup>", "")
    markdown_text = markdown_text.replace("</sup>", "")

    # Supprimer tags
    markdown_text = re.sub(r'^#\S+(?:\s+#\S+)*\s*$', '', markdown_text, flags=re.MULTILINE)


    # Corriger les expressions régulières pour le gras et l'italique
    # Éviter de capturer les * en début de ligne (listes)
    markdown_text = re.sub(r'(?<!^)\*\*([^\*]*?)\*\*', r'\1', markdown_text, flags=re.MULTILINE)
    markdown_text = re.sub(r'(?<!^)\*([^\*]*?)\*', r'\1', markdown_text, flags=re.MULTILINE)

    markdown_text = re.sub(r'  \n', '<SAUT>', markdown_text)


    # gemini = md2gemini(markdown_text, links="paragraph")
    gemini = md2gemini(markdown_text, links="copy")

    gemini = gemini.replace(" [IMG]","")
    gemini = gemini.replace("<SAUT>","\n> ")

    return gemini, title


def extract_date_from_markdown(content):
    # Nouvelle regex avec capture séparée des composants
    date_pattern = r'#(\d{4})-(\d{1,2})-(\d{1,2})'
    match = re.search(date_pattern, content)
    
    if match:
        year = match.group(1)
        # Formatage avec zfill pour ajouter les zéros manquants
        month = match.group(2).zfill(2)
        day = match.group(3).zfill(2)
        return f"{year}-{month}-{day}"
    else:
        return None
    

def create_vintage_press_effect(input_path, output_path, width=1024, quality=15, colors=1025, dither=False):
    """
    Convertit une image en effet "ancienne presse" avec une forte pixelisation
    et une palette réduite pour minimiser la taille du fichier
    
    Args:
        input_path: Chemin de l'image source (webp ou autre)
        output_path: Chemin de l'image de sortie (jpeg)
        width: Largeur souhaitée en pixels
        quality: Qualité JPEG (1-95), plus basse = plus compressée
        colors: Nombre de niveaux par canal (réduit la palette)
        dither: Ajoute du dithering pour simuler plus de nuances
    """
    # Ouvrir l'image
    img = Image.open(input_path)
    
    # Calculer la nouvelle hauteur en conservant le ratio
    ratio = img.height / img.width
    height = int(width * ratio)
    
    # Redimensionner l'image
    img = img.resize((width, height), Image.LANCZOS)
    
    # Appliquer une forte pixelisation (effet gros pixels)
    pixel_size = 3  # Taille des "gros pixels"
    small_width = width // pixel_size
    small_height = height // pixel_size
    img = img.resize((small_width, small_height), Image.NEAREST)
    img = img.resize((width, height), Image.NEAREST)
    
    # Convertir en array numpy pour manipulation des couleurs
    img_array = np.array(img)
    
    # Réduire la palette de couleurs (effet "impression limitée")
    for i in range(3):  # Pour chaque canal RGB
        img_array[:,:,i] = np.floor(img_array[:,:,i] / (256 / colors)) * (256 / colors)
    
    # Reconvertir en image
    img = Image.fromarray(img_array.astype('uint8'))
    
    # Ajouter du contraste pour l'effet "presse"
    enhancer = ImageOps.autocontrast(img, cutoff=5)
    
    # Ajouter du grain/bruit pour simuler l'impression
    if dither:
        enhancer = enhancer.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=32).convert('RGB')
    
    # Ajouter un léger flou pour simuler l'impression qui "bave" légèrement
    # enhancer = enhancer.filter(ImageFilter.GaussianBlur(radius=0.5))
    
    # Sauvegarder avec une forte compression
    enhancer.save(output_path, 'JPEG', quality=quality, optimize=True, progressive=True)
    
    # Afficher les tailles avant/après
    original_size = os.path.getsize(input_path) / 1024
    new_size = os.path.getsize(output_path) / 1024
    print(f"Taille originale: {original_size:.2f} KB")
    print(f"Nouvelle taille: {new_size:.2f} KB")
    print(f"Réduction: {100 - (new_size / original_size * 100):.2f}%")


def create_vintage_press_bw(input_path, output_path, width=1024, quality=30, 
                           num_gray_levels=1024, pixel_size=1, contrast_boost=1):
    """
    Convertit une image en noir et blanc avec un nombre spécifique de niveaux de gris
    
    Args:
        input_path: Chemin de l'image source (webp ou autre)
        output_path: Chemin de l'image de sortie (jpeg)
        width: Largeur souhaitée en pixels
        quality: Qualité JPEG (1-95), plus basse = plus compressée
        num_gray_levels: Nombre de niveaux de gris (2-256)
                         2 = noir et blanc pur
                         4-8 = effet "ancienne presse"
                         16-32 = aspect plus photo
                         256 = tous les niveaux de gris
        pixel_size: Taille des "gros pixels" pour l'effet d'impression
        contrast_boost: Augmentation du contraste (>1 = plus contrasté)
    """

    if os.path.exists(output_path):
        return True

    # Vérifier que le nombre de niveaux est valide
    num_gray_levels = max(2, min(256, num_gray_levels))
    
    # Ouvrir l'image
    img = Image.open(input_path)
    
    # Calculer la nouvelle hauteur en conservant le ratio
    ratio = img.height / img.width
    height = int(width * ratio)
    
    # Redimensionner l'image
    img = img.resize((width, height), Image.LANCZOS)
    
    # Convertir en niveaux de gris
    img = ImageOps.grayscale(img)
    
    # Appliquer une pixelisation pour l'effet "gros pixels"
    if pixel_size > 1:
        small_width = width // pixel_size
        small_height = height // pixel_size
        img = img.resize((small_width, small_height), Image.NEAREST)
        img = img.resize((width, height), Image.NEAREST)
    
    # Augmenter le contraste
    if contrast_boost != 1.0:
        img_array = np.array(img)
        img_array = np.clip((img_array.astype(float) - 128) * contrast_boost + 128, 0, 255).astype(np.uint8)
        img = Image.fromarray(img_array)
    
    # Réduire le nombre de niveaux de gris
    if num_gray_levels < 256:
        step = 255 / (num_gray_levels - 1)
        img_array = np.array(img)
        # Arrondir chaque valeur au niveau de gris le plus proche
        img_array = np.round(img_array / step) * step
        img = Image.fromarray(img_array.astype('uint8'))
    
    # Sauvegarder avec une forte compression
    img.save(output_path, 'JPEG', quality=quality, optimize=True)
    
    # Afficher les tailles avant/après
    # original_size = os.path.getsize(input_path) / 1024
    # new_size = os.path.getsize(output_path) / 1024
    # print(f"Taille originale: {original_size:.2f} KB")
    # print(f"Nouvelle taille: {new_size:.2f} KB")
    # print(f"Réduction: {100 - (new_size / original_size * 100):.2f}%")


def extract_image_links(gmi_text):
    """
    Extrait simplement la liste des liens d'images commençant par '_i/' dans un texte Gemini.
    
    Args:
        gmi_text: Le texte au format Gemini
    
    Returns:
        Une liste des chemins d'images trouvés
    """
    image_links = []
    
    # Parcourir chaque ligne
    for line in gmi_text.split('\n'):
        # Vérifier si c'est une ligne avec un lien qui commence par '=> _i/'
        if line.startswith('=> _i/'):
            # Extraire le chemin jusqu'au premier espace (qui sépare le lien du texte alt)
            parts = line[3:].split(' ', 1)
            link = parts[0].strip()
            
            # Vérifier que c'est une image en vérifiant l'extension
            if any(link.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                image_links.append(link)
    
    return image_links


def sync_images(gmi, source_dir, output_dir):

    # Créer un dossier 'i' pour les images optimisées
    # print(source_dir, output_dir)
    images_dir = os.path.join(output_dir, "i")
    os.makedirs(images_dir, exist_ok=True)

    # Récupérer tous les liens d'images dans le texte Gemini
    image_links = extract_image_links(gmi)

    for img_path in image_links:
        # Chemin complet de l'image source
        input_path = os.path.join(source_dir, img_path)
        # print(input_path, img_path)
        
        # Déterminer le chemin de sortie
        filename = os.path.basename(img_path)
        output_filename = os.path.splitext(filename)[0] + ".jpg"  # Convertir en jpg
        output_path = os.path.join(images_dir, output_filename)
        
        # Créer la version optimisée de l'image
        try:
            create_vintage_press_bw(input_path, output_path)
            
            # Mettre à jour le lien dans le texte Gemini
            gmi = gmi.replace(img_path, f"i/{output_filename}")
            
        except Exception as e:
            print(f"Erreur lors du traitement de l'image {input_path}: {e}")

    return gmi


def sync_one_file(src_path, src, dst):
        
        file = os.path.basename(src_path)
        rel_path = os.path.relpath(src_path, src).replace(".md", ".gmi")
        dst_path = os.path.join(dst, rel_path)

        # print(file)
        # print(rel_path)
        # print(dst_path)

        if file ==  "README.md" or file == "SECURITY.md" or file.startswith(".")  or file.startswith("_"):
            return None

        if "/books/" in src_path or "/page/" in src_path:
            return None

        if file == "LICENSE":
            shutil.copy2(src_path, dst_path)
            return None

        if "/comments/" not in src_path and dst_path.endswith('.gmi'):
            # Pour les fichiers Markdown, copier si différent ou inexistant

            content = tools.tools.read_file(src_path)
            if content is None:
                return None

            post_date = extract_date_from_markdown(content)
            if post_date == None:
                return None

            year, month, _ = post_date.split("-")

            gmi, title = markdown_to_gemini(content, year, month)

            gmi = sync_images(gmi, os.path.dirname(src_path), os.path.dirname(dst_path))
            
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            if not os.path.exists(dst_path) or tools.tools.calculate_hash(dst_path) != tools.tools.hash_content(gmi):
                print("New file: ", dst_path)
                with open(dst_path, 'w', encoding='utf-8') as f:
                    f.write(gmi)

            return {'date': post_date, 'link': f"=> {rel_path} {post_date} - {title}\n"}


def sync_files(src, dst):

    print(f"GMI syncing {src} to {dst}")

    # entries = defaultdict(list)

    entries = {}

    for root, dirs, files in os.walk(src):

        # print(f"Scanning directory: {root}")
        # print(f"Files found: {files}")

        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:

            src_path = os.path.join(root, file)
            r = sync_one_file(src_path, src, dst)
            if r:
                entries[r['date']] = r['link']

    if entries:

        date_courante = date.today()
        date_formatee = date_courante.strftime("%Y-%m-%d")

        sorted_keys = sorted(entries.keys(), reverse=True)
        index_gmi = "# Thierry Crouzet\n"
        gemfeed_gmi = index_gmi
        index_gmi += f"=> gemfeed.gmi {date_formatee} - Gemfeed\n"
        old_year = ""
        old_month = ""
        i = 0
        for key in sorted_keys:
            text = entries[key]
            year, month, _ = key.split("-")
            if old_year != year or old_month != month:
                old_year = year
                old_month = month
                index_gmi += f"# {year}-{month}\n"
            index_gmi += text
            if i<20:
                gemfeed_gmi += text
            i += 1

        with open(os.path.join(dst, "index.gmi"), 'w', encoding='utf-8') as f:
            f.write(index_gmi)

        with open(os.path.join(dst, "gemfeed.gmi"), 'w', encoding='utf-8') as f:
            f.write(gemfeed_gmi)

# test = "/Users/thierrycrouzet/Documents/GitHub/tcrouzet/2025/01/decembre-2024.md"
# print( markdown_to_gemini( tools.tools.read_file(test), "2025", "01" ) )

# create_vintage_press_bw("/Users/thierrycrouzet/Downloads/test.webp", "/Users/thierrycrouzet/Downloads/test.jpg")

# sync_one_file('/Users/thierrycrouzet/Documents/ObsidianLocal/text/tcrouzet/2025/03/quitter-facebook.md', '/Users/thierrycrouzet/Documents/ObsidianLocal/text/tcrouzet', '/Users/thierrycrouzet/Documents/gemini')
# exit()

sync_files(config['export_github_md'], config['gemini_export'] )

sync = tools.sync_files.SyncFiles(config['gemini_export'],'/Volumes/docker/gemini/content')

# command = 'rsync -av --update --exclude=".DS_Store" --exclude=".*/" --delete --checksum=false ~/Documents/gemini/ /Volumes/docker/gemini/content'
# subprocess.run(command, shell=True, check=True)

gh = tools.github.MyGitHub(config, "tcrouzet", config['gemini_export'], "sourcehut")
gh.push()


# rsync -av --update --exclude=".DS_Store" --exclude=".*/" --delete --checksum=false ~/Documents/gemini/ /Volumes/docker/gemini/content
