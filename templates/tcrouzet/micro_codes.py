# templates/<template>/micro_codes.py

import html
import os

class MicroCodes:
    def __init__(self, layout=None):
        self.layout = layout  # accès à config, template_dir, etc.

    def hello(self, name="monde"):
        return f"<strong>Bonjour {name} !</strong>"

    def book_list(self, context=None):
        """
        Liste toutes les PAGES du tag 'book'.
        Utilisation dans le contenu : [code:book_list]
        """
        web = getattr(self.layout, "web", None)
        if web is None:
            return "<!-- book_list: layout.web non défini -->"

        try:
            rows = web.db.get_posts_by_tag("book")
        except Exception as e:
            return f"<!-- book_list: erreur DB: {html.escape(str(e))} -->"

        pages = []
        for row in rows:
            post = web.supercharge_post(row, True)
            if post and post.get("type")==1:
                pages.append(post)

        if not pages:
            return "<!-- book_list: aucune page pour 'book' -->"


        romman = ""
        imaginaire =""
        essais = ""
        recit = ""
        autre =""
        for p in pages:
            frontmatter = p.get("frontmatter", None)
            if frontmatter:
                genre = frontmatter.get("genre","autre").lower()
                url = html.escape(p.get("url","/biliographie/"))
                book = f'<em>{html.escape(p.get("title"))}</em>, {frontmatter.get("date").year}'

                if genre == "roman":
                    romman += book + "<br/>"
                elif genre == "imaginaire":
                    imaginaire += book + "<br/>"
                elif genre == "essai":
                    essais += book + "<br/>"
                elif genre == "récit":
                    recit += book + "<br/>"
                else:
                    autre += book  + f" ({genre})<br/>"

        msg = ""
        if imaginaire:
            msg += f"<h3>Romans SF/imaginaire</h3><p>{imaginaire}</p>"
        if romman:
            msg += f"<h3>Romans</h3><p>{romman}</p>"
        if essais:
            msg += f"<h3>Essais</h3><p>{essais}</p>"
        if recit:
            msg += f"<h3>Récit</h3><p>{recit}</p>"
        if autre:
            msg += f"<h3>Autre</h3><p>{autre}</p>"

        return msg