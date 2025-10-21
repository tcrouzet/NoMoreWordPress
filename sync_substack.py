import sys, re, os
from playwright.sync_api import sync_playwright
import markdown
import tools.tools
import tools.db

import requests
from PIL import Image
from io import BytesIO
import tempfile
import base64


class Webot:

    def __init__(self, config, substack_url=None):
        self.config = config
        self.profile = config['playwright_profile'] # Chemin du profil
        self.substack_url = substack_url

        self.base_dir = None

        p = sync_playwright().start()

        # Lancer Chrome avec votre profil existant
        self.browser = p.chromium.launch_persistent_context(
            user_data_dir=self.profile,
            headless=False,  # Ouvrir le navigateur en mode visible
            args=[
                '--start-maximized',  # Ouvrir en plein écran
            ]
        )

        # Ouvrir une nouvelle page
        self.page = self.browser.new_page()


    def substack(self, markdown_text):

        html, title = self.markdown2html(markdown_text)


        # Naviguer vers Substack
        self.page.goto(f'{self.substack_url}/publish/post/')
        # self.page.goto('https://727bikepacking.substack.com/publish/post/159771263')

        self.page.wait_for_selector('#post-title')

        # Remplir le champ de titre
        self.page.fill('#post-title', title)

        self.page.wait_for_selector('div[data-testid="editor"]')
        # self.page.fill('div[data-testid="editor"]', html)

        # Coller le contenu HTML dans l'éditeur
        self.page.evaluate(
            """
            (html) => {
                const editor = document.querySelector('div[data-testid="editor"]');
                editor.innerHTML = html;  // Insérer le HTML directement    
            }
            """,
            html
        )

        # page.wait_for_timeout(60000)

        input("Appuyez sur Entrée pour fermer le navigateur...")
        self.browser.close()


    def convert_webp_to_jpeg(self, html):
        # Trouver toutes les balises d'image dans le HTML
        img_pattern = re.compile(r'<img[^>]+src=["\'](.*?\.webp)["\'][^>]*>', re.IGNORECASE)
        img_tags = img_pattern.findall(html)
        
        for webp_url in img_tags:
            try:
                # Télécharger l'image WebP
                response = requests.get(webp_url)
                if response.status_code == 200:
                    # Ouvrir l'image avec PIL
                    img = Image.open(BytesIO(response.content))
                    
                    # Créer un fichier temporaire pour l'image JPEG
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                        # Convertir et sauvegarder en JPEG
                        if img.mode in ('RGBA', 'LA'):
                            # Si l'image a une couche alpha, convertir en RGB
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            background.paste(img, mask=img.split()[3])  # 3 est l'index du canal alpha
                            background.save(temp_file.name, 'JPEG', quality=85)
                        else:
                            img.convert('RGB').save(temp_file.name, 'JPEG', quality=85)
                    
                    # Lire l'image JPEG et la convertir en base64
                    with open(temp_file.name, 'rb') as jpeg_file:
                        jpeg_data = jpeg_file.read()
                        base64_jpeg = base64.b64encode(jpeg_data).decode('utf-8')
                    
                    # Créer une URL data pour l'image JPEG
                    jpeg_data_url = f"data:image/jpeg;base64,{base64_jpeg}"
                    
                    # Remplacer l'URL WebP par l'URL data JPEG dans le HTML
                    html = html.replace(webp_url, jpeg_data_url)
                    
                    # Supprimer le fichier temporaire
                    os.unlink(temp_file.name)
            
            except Exception as e:
                print(f"Erreur lors de la conversion de l'image {webp_url}: {e}")
        
        return html


    def load_markdown(self, url):

        md = tools.tools.read_file(url)
        match = re.search(r'/(\d{4})/(\d{1,2})/', url)

        if match:
            year = match.group(1)  # Extrait l'année (4 chiffres)
            month = match.group(2)   # Extrait le mois (1 ou 2 chiffres)
            return md, year, month
        return md, None, None


    def replace_with_base64(self, match):
        img_src = match.group(1)
        img_attrs = match.group(2)
        
        # Si l'image commence par _i/, c'est une image locale
        if img_src.startswith('_i/'):
            # Construire le chemin complet de l'image
            img_path = os.path.join(self.base_dir, img_src)
            
            # Vérifier si l'image existe
            if os.path.exists(img_path):
                try:
                    # Déterminer le type MIME en fonction de l'extension
                    mime_type = 'image/jpeg'  # Par défaut
                    if img_path.lower().endswith('.png'):
                        mime_type = 'image/png'
                    elif img_path.lower().endswith('.gif'):
                        mime_type = 'image/gif'
                    elif img_path.lower().endswith('.webp'):
                        mime_type = 'image/webp'
                    
                    # Lire l'image et la convertir en base64
                    with open(img_path, 'rb') as img_file:
                        img_data = base64.b64encode(img_file.read()).decode('utf-8')
                        
                    # Créer l'URL data
                    data_url = f"data:{mime_type};base64,{img_data}"
                    
                    # Retourner la balise img avec l'URL data
                    return f'<img src="{data_url}"{img_attrs}>'
                except Exception as e:
                    print(f"Erreur lors de la conversion de l'image {img_path}: {e}")
    

    def embed_local_images(self, html, markdown_path):
        """
        Remplace les chemins d'images par des données base64 incorporées
        """        
        # Trouver toutes les balises d'image dans le HTML
        img_pattern = re.compile(r'<img[^>]+src=["\'](.*?)["\'](.*?)>', re.IGNORECASE)

        # Remplacer toutes les balises d'image
        html = img_pattern.sub(self.replace_with_base64, html)
        
        return html


    def markdown2html(self, markdown_path):

        self.base_dir = os.path.dirname(markdown_path)
        markdown_text, year, month = self.load_markdown(markdown_path)

        title = None
        lines = markdown_text.split('\n')    
        # Find first title
        for line in lines:
            if line.startswith('# ') and not title:
                title = line.strip('# ').strip()
                markdown_text = markdown_text.replace(line + '\n', '', 1)
                break
        if title is None:
            sys.exit("No title found")

        # Supprimer tags
        markdown_text = re.sub(r'^#\S+(?:\s+#\S+)*\s*$', '', markdown_text, flags=re.MULTILINE)

        html = markdown.markdown(markdown_text)

        # Chemin img
        if year and month:
            html = html.replace("_i/",f"https://github.com/tcrouzet/md/raw/main/{year}/{month}/_i/")
        else:
            html = self.embed_local_images(html, markdown_path)
            
        html = self.html_optimize(html)
        # print(html)
        # exit()

        return html, title


    def html_optimize(self, html):
        """
        Version simplifiée qui se concentre uniquement sur les paragraphes contenant des images.
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Trouver tous les paragraphes contenant des images
        img_paragraphs = []
        for p in soup.find_all('p'):
            if p.find('img'):
                img_paragraphs.append(p)
        
        # Si nous avons au moins deux paragraphes avec des images
        if len(img_paragraphs) >= 2:
            # Parcourir les paragraphes consécutifs
            for i in range(len(img_paragraphs) - 1):
                current = img_paragraphs[i]
                next_p = img_paragraphs[i + 1]
                
                # Vérifier si les paragraphes sont directement consécutifs
                # en vérifiant si le prochain élément après current est next_p
                next_elem = current.next_sibling
                while next_elem and (not next_elem.name or next_elem.name not in ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    next_elem = next_elem.next_sibling
                
                if next_elem == next_p:
                    # Ajouter un espaceur entre les deux paragraphes
                    spacer = soup.new_tag('p')
                    current.insert_after(spacer)
        
        return str(soup)


config = tools.tools.site_yml('site.yml')
db = tools.db.Db(config)
mode = "FR"
# mode = "BIKE"
# mode = "PHONE"

if mode == "FR":
    last = db.get_last_published_post()
    # last = db.get_post_by_title("Se soustraire au monde")
    print(last['path_md'])
    path = os.path.join( config['export_github_md'], last['path_md'])

    bot = Webot(config, config['substack_fr'])
    bot.substack(path)

elif mode == "BIKE":
    last = db.get_last_published_post()
    print(last['path_md'])
    path = os.path.join( config['export_github_md'], last['path_md'])

    bot = Webot(config, config['substack_727'])
    bot.substack(path)

elif mode == "DIGEST":
    path = tools.tools.find_latest_file("/Users/thierrycrouzet/Documents/ObsidianLocal/text/tcrouzetUS/Digest/")
    bot = Webot(config, config['substack_fr'])
    bot.substack(path)

elif mode == "DIGEST_US":
    path = tools.tools.find_latest_file("/Users/thierrycrouzet/Documents/ObsidianLocal/text/tcrouzetUS/Digest/")
    bot = Webot(config, config['substack_us'])
    bot.substack(path)

elif mode == "PHONE":
    path = "/Users/thierrycrouzet/Documents/ObsidianLocal/text/Phones/001.md"
    bot = Webot(config, config['substack_fr'])
    bot.substack(path)

else:
    path = tools.tools.find_latest_file(config['vault_us'])
    print(path)
    bot = Webot(config, config['substack_us'])
    bot.substack(path)
