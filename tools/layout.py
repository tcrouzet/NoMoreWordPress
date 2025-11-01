from liquid import Liquid

import os
import shutil
import time
import htmlmin
import csscompressor
import hashlib
import importlib.util
import re

def make_liquid_loader(base_dir):
    def make(fname):
        # garantir l’extension
        if not fname.endswith(".liquid"):
            fname += ".liquid"
        path = os.path.join(base_dir, fname)
        if not os.path.isfile(path):
            return None
        return Liquid(path)
    return make

class Layout:

    def __init__(self, config, web_instance):
        self.config = config
        if self.config['version'] == 0:
            self.config['version'] = time.time()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir) + os.sep
        script_dir = parent_dir

        self.web = web_instance

        self.debug = False

        self.templates = []
        for template in self.config['templates']:
            base_dir = os.path.join(parent_dir, "templates", template['name'])

            if not os.path.isdir(base_dir):
                raise FileNotFoundError(f"Template dir not found: {base_dir}")
            
            make = make_liquid_loader(base_dir)

            self.templates.append({
                "name": template['name'],
                "domain": template['domain'],
                "dir": base_dir,
                "export": template['export'],
                "infinite_scroll": bool(template.get('infinite_scroll', False)),
                "post_per_page": int(template.get('post_per_page', 40)),
                "image_max_size": int(template.get('image_max_size', 1024)),
                "micro": self._load_micro_executor(base_dir),
                "header": lambda m=make: m("header"),
                "footer": lambda m=make: m("footer"),
                "single": lambda m=make: m("single"),
                "article": lambda m=make: m("article"),
                "tag": lambda m=make: m("tag"),
                "tags_list": lambda m=make: m("tags_list"),
                "home": lambda m=make: m("home"),
                "menu": lambda m=make: m("menu"),
                "search": lambda m=make: m("search"),
                "share": lambda m=make: m("share"),
                "newsletter": lambda m=make: m("newsletter"),
            })

        self.templates_count = 0
        for template in self.templates:
            self.new_assets = self.copy_assets(template)
            self.templates_count += 1

        print(f"{self.templates_count} template(s) loaded.")


    # def load_template(self, template_dir, name):
    #     path = os.path.join(template_dir, f"{name}.liquid")
    #     return Liquid( path)

    def setDebug(self):
        self.debug = not self.debug

    def dp(self, *args, **kwargs):
        if self.debug:
            print(*args, **kwargs)

    def de(self):
        if self.debug:
            exit("Force exit")

            
    def _load_micro_executor(self, template_dir):
        """
        Charge templates/<template>/micro_codes.py s'il existe.
        Attendu: une classe 'MicroCodes'.
        """
        path = os.path.join(template_dir, "micro_codes.py")
        if not os.path.isfile(path):
            return None
        try:
            spec = importlib.util.spec_from_file_location("tpl_micro_codes", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.MicroCodes(self)  # On suppose un constructeur acceptant Layout
        except Exception as e:
            exit(f"Micro code error: {e}")

    def _apply_microcodes(self, template, html, context=None):
        """
        Remplace [code:func|p1|p2…] par l'appel à MicroCodes.func.
        - Paramètres passés tels quels (strings).
        - Si pas de microcodes, retourne html tel quel.
        """
        if not template or 'micro' not in template:
            return html
        
        if not template['micro'] or not html or "[code:" not in html:
            return html

        pattern = re.compile(r"\[code:([a-zA-Z_]\w*)(?:\|([^\]]+))?\]")

        def repl(m):
            func_name = m.group(1)
            params = m.group(2).split("|") if m.group(2) else []
            func = getattr(template['micro'], func_name, None)
            if not callable(func):
                return f"Microcode function {func_name} inexistant"
            try:
                try:
                    return str(func(context, *params))  # avec contexte si possible
                except TypeError:
                    return str(func(*params))           # sinon sans contexte
            except Exception:
                return m.group(0)  # en cas d'erreur, on ne casse rien

        return pattern.sub(repl, html)


    def copy_assets(self, template):

            os.makedirs(template['export'], exist_ok=True)
            copied_files = []

            for item in os.listdir(template['dir']):
                if item.endswith('.liquid') or item.endswith('.py'):
                    continue

                source_item = os.path.join(template['dir'], item)
                destination_item = os.path.join(template['export'], item)
                
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
        for template in self.templates:

            post = self.web.supercharge_post(template, post)
            if not post:
                raise("Error supercharge in layout")
            
            header_html = self.get_html(template["header"], post=post, blog=self.config)
            footer_html = self.get_html(template["footer"], post=post, blog=self.config)
            share_html = self.get_html(template["share"], post=post, blog=self.config)
            newsletter_html = self.get_html(template["newsletter"], post=post, blog=self.config)
            article_html = self.get_html(template['article'], post=post, blog=self.config, share=share_html, newsletter=newsletter_html)
            single_html = self.get_html(template['single'], post=post, blog=self.config, article=article_html)
            self.save(template, header_html + single_html + footer_html, post['url'], "index.html")
            if template['infinite_scroll']:
                self.save(template, article_html, post['url'], "content.html")


    def tag_gen(self, tag, posts=None):
        for template in self.templates:

            new_tag = self.web.supercharge_tag(template, tag, posts)

            header_html = self.get_html(template["header"], post=new_tag, blog=self.config)
            footer_html = self.get_html(template["footer"], post=new_tag, blog=self.config)

            post_per_page = template["post_per_page"]

            new_posts = new_tag['posts']
            self.dp(len(new_posts), template["infinite_scroll"])

            page = 1
            while new_posts:
                file_name = f"contener{page}.html"

                if post_per_page>0:
                    new_tag['posts'] = new_posts[:post_per_page]
                else:
                    self.dp("Tous les posts…")
                    new_tag['posts'] = new_posts

                if len(new_tag['posts'])<post_per_page or post_per_page==0:
                    new_tag['next_url'] = ""
                else:
                    new_tag['next_url'] = "/" + new_tag['url'].strip("/") + "/" + f"contener{page+1}.html"

                list_html = self.get_html(template["tags_list"], post=new_tag, blog=self.config)

                if page == 1:
                    tag_html = self.get_html(template["tag"], post=new_tag, list=list_html, blog=self.config)
                    self.save(template, header_html + tag_html + footer_html, new_tag['url'], "index.html")
                else:
                    self.save(template, list_html, new_tag['url'], file_name)
                if post_per_page>0:
                    del new_posts[:post_per_page]
                    page += 1
                else:
                    break
        self.de()


    def home_gen(self, last_post, last_carnet, last_bike, last_digest):
        for template in self.templates:

            home = {}
            home['digressions'] = self.web.supercharge_post(template, last_post, False)
            home['carnet'] = self.web.supercharge_post(template, last_carnet, False)
            home['bike'] = self.web.supercharge_post(template, last_bike, False)
            home['digest'] = self.web.supercharge_post(template, last_digest, False)
            
            home['canonical'] = template['domain']
            home['description'] = self.config['description']
            home['title'] = self.config['home_title']
            home['pub_update_str'] = home['digressions']['pub_update_str']
            home['pub_update'] = home['digressions']['pub_update']
            home['thumb'] = home['digressions']['thumb']
            home['thumb_path'] = home['digressions']['thumb_path']
            home['thumb_legend'] = home['digressions']['thumb_legend']
            home['is_home'] = True

            header_html = self.get_html(template["header"], post=home, blog=self.config)
            footer_html = self.get_html(template["footer"], post=home, blog=self.config)
            newsletter_html = self.get_html(template["newsletter"], post=home, blog=self.config)
            home_html = self.get_html(template["home"], post=home, blog=self.config, newsletter=newsletter_html)
            self.save(template, header_html + home_html + footer_html, "", "index.html")


    def special_pages(self, post, path, file_name="index.html"):
        for template in self.templates:
            header_html = self.get_html(template["header"], post=post, blog=self.config)
            footer_html = self.get_html(template["footer"], post=post, blog=self.config)
            article_html = self.get_html(template["article"], post=post, blog=self.config)
            page_html = self.get_html(template["single"], post=post, blog=self.config, article=article_html)
            self.save(template, header_html + page_html + footer_html, path, file_name)

    def e404_gen(self):
        text = '<p>Cette page n’existe plus ou n’a jamais existé.</p>'
        post = {"thumb": None, "title": "Erreur 404", "html": text, "frontmatter": None, "type":1}
        self.special_pages(post, "", "404.html")

    def archives_gen(self, archives):
        post = {"thumb": None, "title": "Archives", "html": archives, "frontmatter": None, "type":1}
        self.special_pages(post, "archives/")

    def get_html(self, template_obj, post=None, blog=None, **extra_ctx):
        tpl = template_obj if hasattr(template_obj, "render") else template_obj()
        if not tpl:
            return ""
        # Construit un contexte minimal cohérent
        ctx = {}
        if post is not None:
            ctx["post"] = post
        if blog is not None:
            # Compat: certains de tes templates semblent attendre "blog"
            ctx["blog"] = blog
        if extra_ctx:
            ctx.update(extra_ctx)
        return tpl.render(**ctx)

    def normal_pages(self, post, template, path, file_name="index.html"):
        header_html = self.get_html(template["header"], post=post, blog=self.config)
        footer_html = self.get_html(template["footer"], post=post, blog=self.config)
        self.save(template, header_html + post['html'] + footer_html, path, file_name)

    def menu_gen(self):
        for template in self.templates:
            menu_html = self.get_html(template["menu"])
            post = {"thumb": None, "title": "", "html": menu_html, "frontmatter": None, "type":3}
            self.normal_pages(post, template, "menu/")

    def search_gen(self):
        for template in self.templates:
            search_html = self.get_html(template["search"])
            post = {"thumb": None, "title": "", "html": search_html, "frontmatter": None, "type":3}
            self.normal_pages(post, template, "search/")


    def save(self, template, html, path, file_name="index.html", context=None):

        # Microcodes avant minification
        html = self._apply_microcodes(template, html, context)

        if self.config["version"]>0:
            html = htmlmin.minify(html, remove_empty_space=True)

        dir = os.path.join( template['export'], path)
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
        