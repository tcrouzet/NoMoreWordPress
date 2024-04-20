from liquid import Liquid
import os

class Layout:

    def __init__(self, config):
        self.config = config

        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir) + os.sep
        script_dir = parent_dir

        self.template_dir = os.path.join(parent_dir, "templates", self.config['template'])


    def load_template(self, name):
        return Liquid( os.path.join(self.template_dir,f"{name}.liquid"))


    def single(self, post):
        header = self.load_template("header")
        header_html = header.render(post=post, blog=self.config)
        #print(dict(post))
        #print(header_html)
        #print( self.url(post))
        self.save(header_html, post['url'])


    def save(self, html, path):

        dir = os.path.join( self.config['export'], path)
        os.makedirs(dir, exist_ok=True)

        with open(os.path.join( dir, 'index.html'), 'w', encoding="utf-8") as file:
            file.write(html)
