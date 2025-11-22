import sys, re, os
from playwright.sync_api import sync_playwright
import tools
import db
import web
import logs

import requests
from PIL import Image
from io import BytesIO
import tempfile
import base64

sys.stdout = logs.DualOutput("_log.txt")
sys.stderr = sys.stdout


class Webot:

    def __init__(self, config, db, template=None, substack_url=None):
        self.config = config
        self.profile = config['playwright_profile'] # Chemin du profil
        self.substack_url = substack_url
        self.db = db
        self.template = template
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


    def substack(self, post):

        lweb = web.Web(config, self.db)
        post = lweb.supercharge_post(self.template, post)

        html = f'<img src="{post["thumb"]["url"]}" alt="{post["thumb"]["legend"]}" />{post['content']}'
        html = html.replace('src="/',f'src="{self.template['domain']}')

        # Naviguer vers Substack
        self.page.goto(f'{self.substack_url}/publish/post/')
        # self.page.goto('https://727bikepacking.substack.com/publish/post/159771263')

        self.page.wait_for_selector('#post-title')

        # Remplir le champ de titre
        self.page.fill('#post-title', post['title'])

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


config = tools.site_yml('site.yml')
template = next((item for item in config['templates'] if item['name'] == 'tcrouzet'), None)
db = db.Db(config)

last = db.get_last_published_post()
print(last['path_md'])
if '"us"' in last["tags"]:
    substack_url=config['substack_us']
elif '"velo"' in last["tags"]:
    substack_url=config['substack_727']
else:
    substack_url=config['substack_fr']
bot = Webot(config, db, template=template, substack_url=substack_url)
bot.substack(last)
