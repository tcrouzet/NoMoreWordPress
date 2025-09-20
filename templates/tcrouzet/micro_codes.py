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
        Liste toutes les PAGES (type == 1) du tag 'book'.
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
            post = web.supercharge_post(row, maximal=False)
            if post and post.get("type") == 1:
                pages.append(post)

        if not pages:
            return "<!-- book_list: aucune page pour 'book' -->"

        items = []
        for p in pages:
            url = "/" + str(p.get("url", "")).strip("/")
            title = p.get("title")
            if not title:
                base = os.path.basename(p.get("path_md", "")) or "Sans titre"
                title = os.path.splitext(base)[0].replace("-", " ").capitalize()
            items.append(f'<li><a href="{html.escape(url)}">{html.escape(title)}</a></li>')

        return '<ul class="book-list">\n' + "\n".join(items) + "\n</ul>"