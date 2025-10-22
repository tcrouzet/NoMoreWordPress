from liquid import Liquid
import os
import shutil
import time
import htmlmin
import csscompressor
import hashlib
import importlib.util
import re


class Layout:

    def __init__(self, config):
        self.config = config
        if self.config['version'] == 0:
            self.config['version'] = time.time()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir) + os.sep
        script_dir = parent_dir

        self.template_dir = os.path.join(parent_dir, "templates", self.config['template'])
        self.config['template'] = self.template_dir

        self.header = self.load_template("header")
        self.footer = self.load_template("footer")
        self.single = self.load_template("single")
        self.article = self.load_template("article")
        self.tag = self.load_template("tag")
        self.tags_list = self.load_template("tags_list")
        self.home = self.load_template("home")
        self.page = self.load_template("page")

        self.new_assets = self.copy_assets()

        self.micro = self._load_micro_executor()


    def load_template(self, name):
        return Liquid( os.path.join(self.template_dir,f"{name}.liquid"))


    def _load_micro_executor(self):
        """
        Charge templates/<template>/micro_codes.py s'il existe.
        Attendu: une classe 'MicroCodes'.
        """
        path = os.path.join(self.template_dir, "micro_codes.py")
        if not os.path.isfile(path):
            return None
        try:
            spec = importlib.util.spec_from_file_location("tpl_micro_codes", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.MicroCodes(self)  # On suppose un constructeur acceptant Layout
        except Exception:
            return None

    def _apply_microcodes(self, html, context=None):
        """
        Remplace [code:func|p1|p2…] par l'appel à MicroCodes.func.
        - Paramètres passés tels quels (strings).
        - Si pas de microcodes, retourne html tel quel.
        """
        if not self.micro or not html or "[code:" not in html:
            return html

        pattern = re.compile(r"\[code:([a-zA-Z_]\w*)(?:\|([^\]]+))?\]")

        def repl(m):
            func_name = m.group(1)
            params = m.group(2).split("|") if m.group(2) else []
            func = getattr(self.micro, func_name, None)
            if not callable(func):
                return m.group(0)  # laisse le token tel quel
            try:
                try:
                    return str(func(context, *params))  # avec contexte si possible
                except TypeError:
                    return str(func(*params))           # sinon sans contexte
            except Exception:
                return m.group(0)  # en cas d'erreur, on ne casse rien

        return pattern.sub(repl, html)


    def copy_assets(self):

            os.makedirs(self.config['export'], exist_ok=True)
            copied_files = []

            for item in os.listdir(self.template_dir):
                if item.endswith('.liquid'):
                    continue

                source_item = os.path.join(self.template_dir, item)
                destination_item = os.path.join(self.config['export'], item)
                
                if os.path.isdir(source_item):
                    # Directory
                    copied_files.extend(self.copy_directory(source_item, destination_item))
                else:
                    ## File
                    if self.copy_file(source_item, destination_item):
                        copied_files.append(destination_item)

            #print(copied_files)
            return copied_files

    def copy_file(self, source, target):
        """
        Copie un fichier uniquement s'il est plus récent ou différent.
        Applique la minification pour .html et .css.
        Retourne True si le fichier a été copié, False sinon.
        """
        # Vérifier si le fichier destination existe et est plus récent que la source
        if os.path.exists(target):
            source_mtime = os.path.getmtime(source)
            target_mtime = os.path.getmtime(target)
            if target_mtime >= source_mtime:
                # Fichier destination plus récent ou identique en date, pas besoin de copier
                return False

        _, ext = os.path.splitext(source)
        if ext in [".html", ".css"]:
            with open(source, "r", encoding="utf-8") as file:
                content = file.read()
            if ext == ".css":
                content = csscompressor.compress(content)
            elif ext == ".html":
                content = htmlmin.minify(content)

            with open(target, "w", encoding="utf-8") as file:
                file.write(content)
            return True
        else:
            shutil.copy2(source, target)
            return True


    def copy_directory(self, source_dir, dest_dir):
            """
            Copie récursivement un dossier en ne copiant que les fichiers plus récents.
            Retourne la liste des fichiers copiés.
            """
            copied_files = []
            os.makedirs(dest_dir, exist_ok=True)
            
            for root, dirs, files in os.walk(source_dir):
                # Calculer le chemin relatif depuis source_dir
                rel_path = os.path.relpath(root, source_dir)
                dest_root = os.path.join(dest_dir, rel_path) if rel_path != '.' else dest_dir
                os.makedirs(dest_root, exist_ok=True)
                
                for file in files:
                    source_file = os.path.join(root, file)
                    dest_file = os.path.join(dest_root, file)
                    if self.copy_file(source_file, dest_file):
                        copied_files.append(dest_file)
            
            return copied_files

    def file_hash(self,file_path):
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as file:
            buf = file.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = file.read(65536)
        return hasher.hexdigest()

    def single_gen(self, post):
        header_html = self.header.render(post=post, blog=self.config)
        footer_html = self.footer.render(post=post, blog=self.config)
        article_html = self.article.render(post=post, blog=self.config)
        single_html = self.single.render(post=post, blog=self.config, article=article_html)
        self.save(header_html + single_html + footer_html, post['url'], "index.html")
        self.save(article_html, post['url'], "content.html")


    def tag_gen(self, tag):
        header_html = self.header.render(post=tag, blog=self.config)
        footer_html = self.footer.render(post=tag, blog=self.config)

        posts = tag['posts']
        page = 1
        while posts:
            file_name = f"contener{page}.html"
            tag['posts'] = posts[:40]
            if len(tag['posts'])<40:
                tag['next_url'] = ""
            else:
                tag['next_url'] = "/" + tag['url'].strip("/") + "/" + f"contener{page+1}.html"
            list_html = self.tags_list.render(post=tag, blog=self.config)
            if page == 1:
                tag_html = self.tag.render(post=tag, list=list_html, blog=self.config)
                self.save(header_html + tag_html + footer_html, tag['url'], "index.html")
            else:
                self.save(list_html, tag['url'], file_name)
            del posts[:40]
            page += 1

    def home_gen(self, post):
        header_html = self.header.render(post=post, blog=self.config)
        footer_html = self.footer.render(post=post, blog=self.config)
        home_html = self.home.render(post=post, blog=self.config)
        self.save(header_html + home_html + footer_html, "", "index.html")


    def e404_gen(self):
        post = {"thumb": None, "title": "Erreur 404", "content": '<p>Cette page n’existe plus… ou n’a jamais existé.</p>'}
        header_html = self.header.render(post=post, blog=self.config)
        footer_html = self.footer.render(post=post, blog=self.config)
        page_html = self.page.render(post=post, blog=self.config)
        self.save(header_html + page_html + footer_html, "", "404.html")


    def archives_gen(self, archives):
        post = {"thumb": None, "title": "Archives", "content": archives}
        header_html = self.header.render(post=post, blog=self.config)
        footer_html = self.footer.render(post=post, blog=self.config)
        page_html = self.page.render(post=post, blog=self.config)
        self.save(header_html + page_html + footer_html, "archives/")


    def save(self, html, path, file_name="index.html", context=None):

        # Microcodes avant minification
        html = self._apply_microcodes(html, context)

        if self.config["version"]>0:
            html = htmlmin.minify(html, remove_empty_space=True)

        dir = os.path.join( self.config['export'], path)
        os.makedirs(dir, exist_ok=True)

        file_path = os.path.join( dir, file_name)
        #print(file_path)

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                if file.read() == html:
                    return  False

        with open(file_path, 'w', encoding="utf-8") as file:
            file.write(html)
            return True
        