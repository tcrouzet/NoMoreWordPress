from liquid import Liquid
from bs4 import BeautifulSoup

import os
import shutil
import time
import htmlmin
import csscompressor
import jsmin
import hashlib
import html
import importlib.util
import json
import re
import shlex
import tools

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
        configured_version = int(self.config['version'])
        self.minify = configured_version > 0
        if configured_version == 0:
            self.config['version'] = int(time.time())

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
                "post_per_page": int(template.get('post_per_page', 0)),
                "image_max_size": int(template.get('image_max_size', 1024)),
                "image_min_size": int(template.get('image_min_size', 250)),
                "sizes": template.get('sizes', None),
                "jpeg_thumb": bool(template.get('jpeg_thumb', False)),
                'comments': int(template.get('comments', 0)),
                'code_blocks': template.get('code_blocks'),
                "inlinecss": self.inlinecss(base_dir),
                "inlinejs": self.inlinejs(base_dir),
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
                "contact": lambda m=make: m("contact"),
            })

        self.templates_count = 0
        self.new_assets = []
        force_assets = int(self.config.get('build', 0)) >= 2
        for template in self.templates:
            self.new_assets.extend(self.copy_assets(template, force=force_assets))
            self.templates_count += 1

        print(f"{self.templates_count} template(s) loaded.")


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
                print(f"Microcode function {func_name} inexistant")
                return f"Microcode function {func_name} inexistant"
            try:
                try:
                    return str(func(context, *params))  # avec contexte si possible
                except TypeError:
                    return str(func(*params))           # sinon sans contexte
            except Exception:
                return m.group(0)  # en cas d'erreur, on ne casse rien

        return pattern.sub(repl, html)


    def copy_assets(self, template, force=False):

            os.makedirs(template['export'], exist_ok=True)
            copied_files = []

            for item in os.listdir(template['dir']):
                if (
                    item == '.DS_Store'
                    or item.endswith('.liquid')
                    or item.endswith('.py')
                    or item.startswith("_")
                ):
                    continue

                source_item = os.path.join(template['dir'], item)
                destination_item = os.path.join(template['export'], item)
                
                if os.path.isdir(source_item):
                    # Directory
                    copied_files.extend(
                        self.copy_directory(source_item, destination_item, force=force)
                    )
                else:
                    ## File
                    if self.copy_file(source_item, destination_item, force=force):
                        copied_files.append(destination_item)

            #print(copied_files)
            return copied_files

    def copy_file(self, source, target, force=False):
        """
        Copie un fichier uniquement s'il est plus récent ou différent.
        Applique la minification pour .html et .css.
        Retourne True si le fichier a été copié, False sinon.
        """
        # Vérifier si le fichier destination existe et est plus récent que la source
        if not force and os.path.exists(target):
            source_mtime = os.path.getmtime(source)
            target_mtime = os.path.getmtime(target)
            if target_mtime >= source_mtime:
                # Fichier destination plus récent ou identique en date, pas besoin de copier
                return False

        _, ext = os.path.splitext(source)
        if ext in [".html", ".css", ".js"]:
            with open(source, "r", encoding="utf-8") as file:
                content = file.read()
            if self.minify:
                if ext == ".css":
                    content = csscompressor.compress(content)
                elif ext == ".js":
                    content = jsmin.jsmin(content)
                elif ext == ".html":
                    content = htmlmin.minify(content)

            with open(target, "w", encoding="utf-8") as file:
                file.write(content)
            return True
        else:
            shutil.copy2(source, target)
            return True

    def inlinecss(self, base_dir):
        css_path = os.path.join(base_dir, "style.css")
        return tools.get_css(css_path)


    def inlinejs(self, base_dir):
        content = ""
        js_path = os.path.join(base_dir, "toggle.js")
        if os.path.exists(js_path):
            with open(js_path, "r", encoding="utf-8") as file:
                content = file.read()
                content = jsmin.jsmin(content)
        return content

    def copy_directory(self, source_dir, dest_dir, force=False):
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
                    if self.copy_file(source_file, dest_file, force=force):
                        copied_files.append(dest_file)
            
            return copied_files

    def clean_stale_tag_exports(self, tags):
        """Supprime uniquement les anciens /tag/<slug>/ lors d'un build complet."""
        current_slugs = {
            tag['tag_slug'] for tag in tags
            if (tag['tag_url'] or '').strip('/').startswith('tag/')
        }
        for template in self.templates:
            tag_root = os.path.abspath(os.path.join(template['export'], 'tag'))
            if not os.path.isdir(tag_root):
                continue
            for name in os.listdir(tag_root):
                target = os.path.abspath(os.path.join(tag_root, name))
                if (
                    name not in current_slugs
                    and os.path.isdir(target)
                    and os.path.commonpath((tag_root, target)) == tag_root
                ):
                    shutil.rmtree(target)
                    print(f"Deleted stale tag export: {target}")

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
            
            supercharged = self.web.supercharge_post(template, post)
            supercharged['content'] = self.content_blocks(
                template, supercharged.get('content', '')
            )

            article_template = template['article']
            layout_name = str(
                (supercharged.get('frontmatter') or {}).get('layout', '')
            ).strip()
            if layout_name and re.fullmatch(r'[a-zA-Z0-9_-]+', layout_name):
                layout_path = os.path.join(template['dir'], f'{layout_name}.liquid')
                if os.path.isfile(layout_path):
                    article_template = Liquid(layout_path)
                    if layout_name == 'timeline':
                        supercharged['content'] = self.timeline_blocks(
                            supercharged['content']
                        )

            header_html = self.get_html(template["header"], post=supercharged, blog=self.config, template=template)
            footer_html = self.footer_html(template, supercharged)
            share_html = self.get_html(template["share"], post=supercharged, blog=self.config, template=template)
            newsletter_html = self.get_html(template["newsletter"], post=supercharged, blog=self.config)
            article_html = self.get_html(article_template, post=supercharged, blog=self.config, share=share_html, newsletter=newsletter_html, template=template)
            single_html = self.get_html(template['single'], post=supercharged, blog=self.config, article=article_html)
            self.save(template, header_html + single_html + footer_html, supercharged['url'], "index.html")
            if template['infinite_scroll']:
                self.save(template, article_html, supercharged['url'], "content.html")

    def timeline_blocks(self, content):
        """Regroupe titre, date, texte et image en événements de frise."""
        soup = BeautifulSoup(content or '', 'html.parser')
        nodes = list(soup.contents)
        heading_indexes = [
            index for index, node in enumerate(nodes)
            if getattr(node, 'name', None) in ('h2', 'h3', 'h4', 'h5', 'h6')
        ]
        if not heading_indexes:
            return content

        intro = ''.join(str(node) for node in nodes[:heading_indexes[0]])
        events = []
        outro = ''
        for event_index, start in enumerate(heading_indexes):
            end = (
                heading_indexes[event_index + 1]
                if event_index + 1 < len(heading_indexes)
                else len(nodes)
            )
            heading = nodes[start]
            segment = BeautifulSoup(
                ''.join(str(node) for node in nodes[start + 1:end]),
                'html.parser'
            )

            date_html = ''
            first_element = segment.find(recursive=False)
            if first_element and first_element.name == 'p':
                date_html = first_element.decode_contents()
                first_element.extract()

            image_html = ''
            image = segment.find('img')
            if image:
                image_html = str(image)
                media = image.find_parent('figure')
                media = media or image
                top_level_media = media
                while top_level_media.parent is not segment:
                    top_level_media = top_level_media.parent
                if event_index == len(heading_indexes) - 1:
                    following = list(top_level_media.next_siblings)
                    outro = ''.join(str(node) for node in following).strip()
                    for node in following:
                        node.extract()
                top_level_media.extract()

            events.append({
                'title': heading.decode_contents(),
                'date': date_html,
                'body': segment.decode_contents().strip(),
                'image': image_html,
                'inverted': event_index % 2 == 1
            })

        timeline = BeautifulSoup('', 'html.parser')
        wrapper = timeline.new_tag('div', attrs={'class': 'timeline-layout'})
        if intro.strip():
            intro_block = timeline.new_tag('div', attrs={'class': 'timeline-intro'})
            intro_block.append(BeautifulSoup(intro, 'html.parser'))
            wrapper.append(intro_block)

        event_list = timeline.new_tag('ol', attrs={'class': 'timeline'})
        for event in events:
            classes = ['timeline-event']
            if event['inverted']:
                classes.append('timeline-inverted')
            item = timeline.new_tag('li', attrs={'class': classes})

            marker = timeline.new_tag('div', attrs={'class': 'timeline-image'})
            if event['image']:
                marker.append(BeautifulSoup(event['image'], 'html.parser'))
            item.append(marker)

            panel = timeline.new_tag('div', attrs={'class': 'timeline-panel'})
            if event['date']:
                date = timeline.new_tag('p', attrs={'class': 'timeline-date'})
                date.append(BeautifulSoup(event['date'], 'html.parser'))
                panel.append(date)
            title = timeline.new_tag('h2')
            title.append(BeautifulSoup(event['title'], 'html.parser'))
            panel.append(title)
            if event['body']:
                body = timeline.new_tag('div', attrs={'class': 'timeline-body'})
                body.append(BeautifulSoup(event['body'], 'html.parser'))
                panel.append(body)
            item.append(panel)
            event_list.append(item)

        wrapper.append(event_list)
        if outro:
            outro_block = timeline.new_tag('div', attrs={'class': 'timeline-outro'})
            outro_block.append(BeautifulSoup(outro, 'html.parser'))
            wrapper.append(outro_block)
        return str(wrapper)


    def tag_gen_serie(self, series, tags):
        """Génère une page listant tous les tags avec leur dernier post"""
                
        # tags = self.web.db.row_to_dict(tags)
        if not tags:
            print(series)
            exit("tag_gen_serie error")

        for template in self.templates:

            tags_super = self.web.supercharge_tags(template, tags)
            # tags_super = self.web.db.row_to_dict(tags_super)
            if len(tags_super)==0:
                exit("Strange pas de tags_super")
            new_series = self.web.supercharge_tag(template, series, tags_super[0])
            
            # Générer le HTML
            header_html = self.get_html(template["header"], post=new_series, blog=self.config, template=template)
            footer_html = self.footer_html(template, new_series)
            tags_list_html = self.get_html(template["tags_list"], post=new_series, tags=tags_super, blog=self.config)
            tag_html = self.get_html(template["tag"], post=new_series, tags={"list": tags_list_html})
            
            # Sauvegarder
            self.save(template, header_html + tag_html + footer_html, series['tag_url'], "index.html")


    def tag_gen(self, tag, posts):

        for template in self.templates:
            posts_super = self.web.supercharge_posts(template, posts)
            if len(posts_super) == 0:
                exit("Strange pas de posts_super")
            tag_super = self.web.supercharge_tag(template, tag, posts_super[0])

            header_html = self.get_html(template["header"], post=tag_super, blog=self.config, template=template)
            footer_html = self.footer_html(template, tag_super)

            post_per_page = template["post_per_page"]

            page = 1
            while posts_super:
                if post_per_page > 0:
                    posts_super_filter = posts_super[:post_per_page] # Prendre post_per_page premiers éléments
                    posts_super = posts_super[post_per_page:] #Réduit posts_super
                else:
                    # Une seule page avec tout
                    posts_super_filter = posts_super
                    posts_super = None

                # Vérifier s'il y a une page suivante
                if post_per_page > 0 and len(posts_super) > 0:
                    tag_super['navigation']['next_url'] = "/" + tag_super['tag_url'].strip("/") + "/" + f"contener{page+1}.html"
                else:
                    tag_super['navigation']['next_url'] = ""

                tags_list_html = self.get_html(template["tags_list"], post=tag_super, tags=posts_super_filter, blog=self.config)

                if page == 1:
                    tag_html = self.get_html(template["tag"], post=tag_super, tags={"list": tags_list_html})
                    self.save(template, header_html + tag_html + footer_html, tag_super['tag_url'], "index.html")
                else:
                    file_name = f"contener{page}.html"
                    self.save(template, tags_list_html, tag_super['tag_url'], file_name)
                
                page += 1


    def year_gen(self, year, posts):
        """Génère une page listant tous les tags avec leur dernier post"""
                
        for template in self.templates:

            super_posts = self.web.supercharge_posts(template, posts)
            year_super = self.web.supercharge_tag(template, year, super_posts[0])
            
            # Générer le HTML
            header_html = self.get_html(template["header"], post=year_super, blog=self.config, template=template)
            footer_html = self.footer_html(template, year_super)
            tags_list_html = self.get_html(template["tags_list"], post=year_super, tags=super_posts, blog=self.config)
            tag_html = self.get_html(template["tag"], post=year_super, tags={"list": tags_list_html})
            
            # Sauvegarder
            self.save(template, header_html + tag_html + footer_html, year_super['tag_url'], "index.html")

    def home_blocks(self, template, content):
        content = self.content_blocks(template, content)
        buttons_pattern = re.compile(
            r'<p>\s*(?P<buttons>(?:{%\s*bouton\s*=\s*.*?%}\s*)+)</p>',
            flags=re.DOTALL | re.IGNORECASE
        )
        button_pattern = re.compile(
            r'{%\s*bouton\s*=\s*(.*?)\s*%}',
            flags=re.DOTALL | re.IGNORECASE
        )

        def buttons(match):
            links = []
            for button_match in button_pattern.finditer(match.group('buttons')):
                value = button_match.group(1).strip()
                link = BeautifulSoup(value, 'html.parser').find('a', href=True)
                if link:
                    label = link.get_text(strip=True)
                    url = link['href'].strip()
                else:
                    markdown_link = re.fullmatch(r'\[([^]]+)]\(([^)]+)\)', value)
                    if not markdown_link:
                        continue
                    label, url = (
                        markdown_link.group(1).strip(),
                        markdown_link.group(2).strip()
                    )
                if not label or not url:
                    continue
                links.append(
                    f'<a class="home-choice-button" href="{html.escape(url, quote=True)}">'
                    f'{html.escape(label)}</a>'
                )
            if not links:
                return ''
            return '<nav class="home-choice-buttons" aria-label="Types de parcours">' + ''.join(links) + '</nav>'

        content = buttons_pattern.sub(buttons, content)
        cards_pattern = re.compile(
            r'<p>\s*{%\s*cards\s+(.*?)%}\s*</p>',
            flags=re.DOTALL
        )

        def cards(match):
            arguments = {}
            try:
                for argument in shlex.split(match.group(1)):
                    if '=' in argument:
                        key, value = argument.split('=', 1)
                        arguments[key.strip()] = value.strip()
            except ValueError as error:
                print(f"Invalid home cards block: {error}")
                return match.group(0)

            tag_slug = arguments.get('tag')
            if not tag_slug:
                return match.group(0)
            try:
                limit = max(1, int(arguments.get('limit', 3)))
            except ValueError:
                limit = 3

            posts = self.web.db.get_posts_by_tag(tag_slug, limit=limit)
            if not posts:
                return ''
            tag = self.web.db.tag_2_dict(tag_slug)
            cards_html = self.get_html(
                template["tags_list"], post=tag,
                tags=self.web.supercharge_posts(template, posts),
                blog=self.config
            )
            return f'<div class="home-card-grid card-grid">{cards_html}</div>'

        content = cards_pattern.sub(cards, content)
        newsletter_pattern = re.compile(
            r'<p>\s*{%\s*newsletter\s*%}\s*</p>'
        )
        newsletter_html = self.get_html(
            template["newsletter"], blog=self.config
        )
        content = newsletter_pattern.sub(newsletter_html, content)

        soup = BeautifulSoup(content, 'html.parser')

        for block in soup.find_all(['h2', 'blockquote']):
            figure = block.find_previous_sibling()
            if not figure or figure.name != 'figure':
                continue
            image = figure.find('img')
            if not image or not image.get('src'):
                continue
            window = soup.new_tag('div')
            window['class'] = ['home-parallax-window']
            if block.name == 'blockquote':
                window['class'].append('home-parallax-before-quote')
            window['style'] = (
                f"--parallax-image:url('{image['src']}');"
                "background-image:var(--parallax-image)"
            )
            window['role'] = 'img'
            if image.get('alt'):
                window['aria-label'] = image['alt']
            figure.replace_with(window)

        return str(soup)

    def home_gen(self, last_post=None, featured_posts=None, home_post=None):
        featured_posts = featured_posts or {}
        for template in self.templates:

            if home_post:
                home = self.web.supercharge_post(template, home_post)
                home['content'] = self.home_blocks(template, home['content'])
            else:
                home = {}
                home['digressions'] = self.web.supercharge_post(template, last_post)
                home.update(featured_posts)
                home['title'] = self.config['home_title']
                home['pub_update_str'] = home['digressions']['pub_update_str']
                home['pub_update'] = home['digressions']['pub_update']
                home['thumb'] = home['digressions']['thumb']
                home['thumb_path'] = home['digressions']['thumb_path']
                home['thumb_legend'] = home['digressions']['thumb_legend']
                home['frontmatter'] = None

            home['canonical'] = template['domain']
            home['description'] = home.get('description') or self.config['description']
            home['is_home'] = True

            header_html = self.get_html(template["header"], post=home, blog=self.config, template=template)
            footer_html = self.footer_html(template, home)
            newsletter_html = self.get_html(template["newsletter"], post=home, blog=self.config)
            home_html = self.get_html(template["home"], post=home, blog=self.config, newsletter=newsletter_html)
            self.save(template, header_html + home_html + footer_html, "", "index.html")


    def special_pages(self, post, path, file_name="index.html", content_template=None):
        for template in self.templates:
            page_post = self.special_page_context(template, post, path, file_name)
            if content_template:
                page_post['content'] = self.get_html(
                    template[content_template], blog=self.config
                )
            header_html = self.get_html(template["header"], post=page_post, blog=self.config, template=template)
            footer_html = self.footer_html(template, page_post)
            article_html = self.get_html(template["article"], post=page_post, blog=self.config)
            page_html = self.get_html(template["single"], post=page_post, blog=self.config, article=article_html)
            self.save(template, header_html + page_html + footer_html, path, file_name)

    def special_page_context(self, template, post, path, file_name="index.html"):
        """Complète les données minimales des pages générées hors base."""
        page_post = dict(post)
        relative_path = path.strip('/')
        if file_name != 'index.html':
            relative_path = '/'.join(filter(None, (relative_path, file_name)))
        canonical = template['domain'].rstrip('/') + '/'
        if relative_path:
            canonical += relative_path
            if file_name == 'index.html':
                canonical += '/'
        page_post['canonical'] = canonical
        page_post.setdefault('description', self.config.get('description', ''))
        page_post.setdefault('is_home', False)
        return page_post

    def e404_gen(self):
        text = '<p>Cette page n’existe plus ou n’a jamais existé.</p>'
        post = {"thumb": None, "title": "Erreur 404", "content": text, "frontmatter": None, "type":1, "frontmatter": None}
        self.special_pages(post, "", "404.html")

    def archives_gen(self, archives):
        post = {"thumb": None, "title": "Archives", "content": archives, "frontmatter": None, "type":1, "frontmatter": None}
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
        rendered = tpl.render(**ctx)
        if post and post.get('event_schema') and '</head>' in rendered:
            event_json = json.dumps(
                post['event_schema'],
                ensure_ascii=False,
                separators=(',', ':'),
            ).replace('</', '<\\/')
            event_script = (
                '<script type="application/ld+json">'
                + event_json
                + '</script>'
            )
            rendered = rendered.replace('</head>', event_script + '</head>', 1)
        return rendered

    def content_blocks(self, template, content):
        """Développe les shortcodes communs à tous les contenus éditoriaux."""
        if not content:
            return content
        contact_pattern = re.compile(
            r'<p>\s*{%\s*contact\s*%}\s*</p>|{%\s*contact\s*%}',
            flags=re.IGNORECASE
        )
        contact_html = self.get_html(template["contact"], blog=self.config)
        content = contact_pattern.sub(lambda _match: contact_html, content)

        soup = BeautifulSoup(content, 'html.parser')
        if template.get('code_blocks') == 'testimonials':
            self.testimonial_blocks(soup)
        for quote in soup.find_all('blockquote'):
            figure = quote.find_previous_sibling()
            if not figure or figure.name != 'figure':
                continue
            image = figure.find('img')
            if not image or not image.get('src'):
                continue
            window = soup.new_tag('div')
            window['class'] = [
                'home-parallax-window', 'home-parallax-before-quote'
            ]
            window['style'] = (
                f"--parallax-image:url('{image['src']}');"
                "background-image:var(--parallax-image)"
            )
            window['role'] = 'img'
            if image.get('alt'):
                window['aria-label'] = image['alt']
            figure.replace_with(window)

        return str(soup)

    def testimonial_blocks(self, soup):
        """Transforme chaque suite de blocs code en cartes de témoignages."""
        author_pattern = re.compile(
            r'(?:[»”"]\s*)?([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ’\'-]+)\s*$'
        )
        candidates = []
        for container in soup.find_all(['p', 'pre']):
            code = container.find('code', recursive=False)
            if code and container.get_text(strip=True) == code.get_text(strip=True):
                candidates.append(container)

        pending = set(map(id, candidates))
        for first in candidates:
            if id(first) not in pending:
                continue
            grid = soup.new_tag('div', attrs={'class': 'testimonial-grid'})
            first.insert_before(grid)
            current = first
            while current is not None and id(current) in pending:
                pending.remove(id(current))
                code = current.find('code', recursive=False)
                raw_text = code.get_text('\n', strip=True)
                author = ''
                author_match = author_pattern.search(raw_text)
                if author_match:
                    author = author_match.group(1)
                    raw_text = raw_text[:author_match.start()].rstrip()
                quote_text = raw_text.strip().lstrip('«“"').rstrip('»”"').strip()

                card = soup.new_tag('article', attrs={'class': 'testimonial-card'})
                paragraph = soup.new_tag('p')
                paragraph['class'] = ['testimonial-quote']
                for index, line in enumerate(quote_text.splitlines()):
                    if index:
                        paragraph.append(soup.new_tag('br'))
                    paragraph.append(line.strip())
                card.append(paragraph)
                if author:
                    caption = soup.new_tag('p', attrs={'class': 'testimonial-author'})
                    caption.string = author
                    card.append(caption)
                grid.append(card)

                next_candidate = current.find_next_sibling()
                current.extract()
                current = next_candidate

    def footer_html(self, template, post):
        footer_content = self.content_blocks(
            template, self.config.get('footer_content', '')
        )
        return self.get_html(
            template["footer"], post=post, blog=self.config,
            template=template, footer_content=footer_content
        )

    def menu_gen(self):
        post = {
            "thumb": None,
            "title": "Menu",
            "content": "",
            "description": "Navigation du site",
            "frontmatter": None,
            "type": 3
        }
        self.special_pages(post, "menu/", content_template="menu")

    def search_gen(self):
        post = {
            "thumb": None,
            "title": "Recherche",
            "content": "",
            "description": "Rechercher sur le site",
            "frontmatter": None,
            "type": 3
        }
        self.special_pages(post, "search/", content_template="search")


    def save(self, template, html, dir_path, file_name="index.html", context=None):

        # Microcodes avant minification
        html = self._apply_microcodes(template, html, context)

        if self.minify:
            html = htmlmin.minify(html, remove_empty_space=True)

        dir = os.path.join( template['export'], dir_path.lstrip("/"))
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
