import json
import tools as tools

class JsonLD:
    """Construit et rend les schémas JSON-LD à partir de la config du site."""

    def __init__(self, config):
        self.author_name = config.get('author')
        self.author_url = config.get('author_url')
        self.site_name = config.get('title')
        self.site_url = (
            config.get('canonical_domain') or config.get('domain') or ''
        ).rstrip('/')

    def render(self, post=None, blog=None) -> str:
        schemas = self._build(post=post)
        if not schemas:
            return ""
        scripts = []
        for schema in schemas:
            payload = json.dumps(
                schema, ensure_ascii=False, separators=(',', ':')
            ).replace('</', '<\\/')
            scripts.append(f'<script type="application/ld+json">{payload}</script>')
        return "".join(scripts)

    def _build(self, post=None) -> list:
        if not post:
            return []
        schemas = [self._blogposting(post)]
        if post.get('event_schema'):
            schemas.append(post['event_schema'])
        return schemas

    def _author(self) -> dict:
        author = {"@type": "Person", "name": self.author_name}
        if self.author_url:
            author["url"] = self.author_url
        return author

    def _blogposting(self, post) -> dict:
        frontmatter = post.get('frontmatter') or {}
        schema = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": frontmatter.get('metatitle') or post.get('title'),
            "description": (
                frontmatter.get('metadescription')
                or post.get('description')
                or post.get('title')
            ),
            "url": post.get('canonical'),
            "mainEntityOfPage": {"@type": "WebPage", "@id": post.get('canonical')},
            "author": self._author(),
            "publisher": {"@type": "Organization", "name": self.site_name},
        }
        if post.get('pub_date'):
            schema["datePublished"] = tools.format_timestamp_to_paris_time(
                post['pub_date']
            )
        thumb = post.get('thumb')
        if thumb and thumb.get('jpeg'):
            schema["image"] = self.site_url + thumb['jpeg']
        return schema