import sys, re, os
from playwright.sync_api import sync_playwright
import markdown
import tools.tools
import tools.db


class Webot:

    def __init__(self, config, substack_url):
        self.config = config
        self.profile = config['playwright_profile'] # Chemin du profil
        self.substack_url = substack_url

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

    def load_markdown(self, url):
        # Expression régulière pour extraire l'année et le mois
        match = re.search(r'/(\d{4})/(\d{1,2})/', url)

        if match:
            year = match.group(1)  # Extrait l'année (4 chiffres)
            month = match.group(2)   # Extrait le mois (1 ou 2 chiffres)
            md = tools.tools.read_file(url)
            return md, year, month
        return None, None, None


    def markdown2html(self, markdown_path):

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

        # Chemin img
        markdown_text = markdown_text.replace("_i/",f"https://github.com/tcrouzet/md/raw/main/{year}/{month}/_i/")

        html = markdown.markdown(markdown_text)
        html = self.html_optimize(html)
        # print(html)
        # exit()

        return html, title


    def html_optimize_1(self, html):
        """
        Optimise le HTML pour Substack en ajoutant des espaces uniquement entre les images consécutives
        en utilisant des expressions régulières
        """
        # Détecter les images consécutives (avec ou sans paragraphes)
        # Cas 1: <img>...</img><img>
        html = re.sub(r'(<img[^>]+>)(\s*)(<img[^>]+>)', r'\1<p>&nbsp;</p>\3', html)
        
        # Cas 2: <p><img>...</p><p><img>
        html = re.sub(r'(<p><img[^>]+></p>)(\s*)(<p><img[^>]+>)', r'\1<p>&nbsp;</p>\3', html)
        
        # Cas 3: <img>...</img><p><img>
        html = re.sub(r'(<img[^>]+>)(\s*)(<p><img[^>]+>)', r'\1<p>&nbsp;</p>\3', html)
        
        # Cas 4: <p><img>...</p><img>
        html = re.sub(r'(<p><img[^>]+></p>)(\s*)(<img[^>]+>)', r'\1<p>&nbsp;</p>\3', html)
        
        return html


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
mode = "DIGEST"

if mode == "FR":
    last = db.get_last_published_post()
    print(last['path_md'])
    path = os.path.join( config['export_github_md'], last['path_md'])

    bot = Webot(config, config['substack_fr'])
    bot.substack(path)

elif mode == "DIGEST":
    path = "/Users/thierrycrouzet/Documents/ObsidianLocal/text/tcrouzetUS/Digest/2025/03/digest3.md"
    bot = Webot(config, config['substack_fr'])
    bot.substack(path)

else:
    path = tools.tools.find_latest_file(config['vault_us'])
    print(path)
    bot = Webot(config, config['substack_us'])
    bot.substack(path)
