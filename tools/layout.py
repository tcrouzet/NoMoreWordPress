from liquid import Liquid
import os
import shutil
import time
import htmlmin
import csscompressor
import hashlib


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


    def load_template(self, name):
        return Liquid( os.path.join(self.template_dir,f"{name}.liquid"))

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
                if not os.path.exists(destination_item):
                    shutil.copytree(source_item, destination_item)
                    for root, dirs, files in os.walk(destination_item):
                        for file in files:
                            copied_files.append(os.path.join(root, file))
            else:
                ## File
                if self.copy_file(source_item, destination_item):
                    copied_files.append(destination_item)

        #print(copied_files)
        return copied_files
    

    def copy_file(self, source, target):

        _, ext = os.path.splitext(source)
        if ext in [".html", ".css"]:
            with open(source, "r") as file:
                content = file.read()
            if ext in [".css"]:
                content = csscompressor.compress(content)
            if ext in [".html"]:
                content = htmlmin.minify(content)

            # test is the same
            if os.path.exists(target):
                with open(target, 'r', encoding='utf-8') as file:
                    if file.read() == content:
                        return  False

            with open(target, "w", encoding="utf-8") as file:
                file.write(content)
                return True
        else:
            if os.path.exists(target) and self.file_hash(source) == self.file_hash(target):
                return False

            shutil.copy2(source, target)
            return True


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


    def save(self, html, path, file_name="index.html"):

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
        