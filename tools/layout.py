from liquid import Liquid
import os
import shutil
import time

class Layout:

    def __init__(self, config):
        self.config = config
        self.config['version'] = time.time()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir) + os.sep
        script_dir = parent_dir

        self.template_dir = os.path.join(parent_dir, "templates", self.config['template'])
        self.config['template'] = self.template_dir

        self.header = self.load_template("header")
        self.footer = self.load_template("footer")
        self.single = self.load_template("single")

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
                if not os.path.exists(destination_item):
                    shutil.copytree(source_item, destination_item)
                    for root, dirs, files in os.walk(destination_item):
                        for file in files:
                            copied_files.append(os.path.join(root, file))
            else:
                if not os.path.exists(destination_item) or os.path.getsize(source_item) != os.path.getsize(destination_item):
                    shutil.copy2(source_item, destination_item)
                    copied_files.append(destination_item)

        return copied_files


    def single_gen(self, post):
        header_html = self.header.render(post=post, blog=self.config)
        footer_html = self.footer.render(post=post, blog=self.config)
        single_html = self.single.render(post=post, blog=self.config)
        #share_html = self.share.render(post=post)
        self.save(header_html + single_html + footer_html, post['url'])


    def save(self, html, path):

        dir = os.path.join( self.config['export'], path)
        os.makedirs(dir, exist_ok=True)

        with open(os.path.join( dir, 'index.html'), 'w', encoding="utf-8") as file:
            file.write(html)
