import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

class Sitemap:

    def __init__(self, config):
        self.config = config
        self.sitemap_index = []
        self.urlset = None
        self.output = None


    def open(self, sitemap_name):
        #self.urlset = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')

        ET.register_namespace('image', "http://www.google.com/schemas/sitemap-image/1.1")
        self.urlset = ET.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9",
            attrib={
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xsi:schemaLocation": "http://www.sitemaps.org/schemas/sitemap/0.9 "
                            "http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd "
                            "http://www.google.com/schemas/sitemap-image/1.1 "
                            "http://www.google.com/schemas/sitemap-image/1.1/sitemap-image.xsd",
                "xmlns:image": "http://www.google.com/schemas/sitemap-image/1.1"
            })
        
        self.output = os.path.join(self.config['export'], f"{sitemap_name}.xml")


    def save(self):
        self._indent(self.urlset)
        tree = ET.ElementTree(self.urlset)
        tree.write(self.output, xml_declaration=True, encoding='utf-8', method='xml')
        self.sitemap_index.append(self.output)


    def add(self, url_loc, lastmod=None, image_url=None):
        if ".html" not in url_loc:
            url_loc += "index.html"
        url_loc = self.config['domain'] + url_loc
        if image_url:
            image_url = self.config['domain'] + image_url.strip("/")
        url = ET.SubElement(self.urlset, 'url')
        loc = ET.SubElement(url, 'loc')
        loc.text = url_loc
        if lastmod:
            lastmod_elem = ET.SubElement(url, 'lastmod')
            lastmod_elem.text = lastmod
        if image_url:
            image_elem = ET.SubElement(url, 'image:image')
            image_loc = ET.SubElement(image_elem, 'image:loc')
            image_loc.text = image_url

    def add_post(self, post):
        if 'pub_update_str' in post:
            pub_date = post['pub_update_str']
        else:
            pub_date = None
        thumb = None
        if 'thumb' in post and post['thumb']:
            if 'url' in post['thumb']:
                thumb = post['thumb']['url']

        self.add(post['url'], pub_date, thumb)

    def add_page(self, url, date):
        self.add_post({"url": url, "pub_update_str": date })


    def save_index(self, sitemap_name = 'sitemap'):
        output = os.path.join(self.config['export'], f"{sitemap_name}.xml")
        index_element = ET.Element('sitemapindex', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')

        now = datetime.now(timezone.utc).isoformat(timespec='seconds')

        for sitemap in self.sitemap_index:
            sitemap_elem = ET.SubElement(index_element, 'sitemap')
            loc = ET.SubElement(sitemap_elem, 'loc')
            loc.text = self.config['domain'] + os.path.basename(sitemap)

            lastmod_elem = ET.SubElement(sitemap_elem, 'lastmod')
            lastmod_elem.text = now

        self._indent(index_element)
        index_tree = ET.ElementTree(index_element)
        index_path = os.path.join(self.config['export'], )
        index_tree.write(output, xml_declaration=True, encoding='utf-8', method='xml')

    def _indent(self, elem, level=0):
            i = "\n" + level*"  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for elem in elem:
                    self._indent(elem, level+1)
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i