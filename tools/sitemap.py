import os
import xml.etree.ElementTree as ET
import tools.tools as tools

class Sitemap:

    def __init__(self, config, web_instance):
        self.config = config
        self.web = web_instance

        self.sitemap_index = {}
        self.urlset = {}
        self.output = {}
        self.lastmod = {}
        self.count = {}

        for template in self.config['templates']:
            self.sitemap_index[template['name']] = []
            self.urlset[template['name']] = None
            self.output[template['name']] = None
            self.lastmod[template['name']] = ""
            self.count[template['name']] = 0


    def open(self, sitemap_name):

        for template in self.config['templates']:

            ET.register_namespace('image', "http://www.google.com/schemas/sitemap-image/1.1")
            self.urlset[template['name']] = ET.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9",
                attrib={
                    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "xsi:schemaLocation": "http://www.sitemaps.org/schemas/sitemap/0.9 "
                                "http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd "
                                "http://www.google.com/schemas/sitemap-image/1.1 "
                                "http://www.google.com/schemas/sitemap-image/1.1/sitemap-image.xsd",
                    "xmlns:image": "http://www.google.com/schemas/sitemap-image/1.1"
                })
            
            self.output[template['name']] = os.path.join(template['export'], f"sitemap/{sitemap_name}.xml")
            self.count[template['name']] = 0
 

    def save(self, ucount=None):

        for template in self.config['templates']:

            if ucount:
                if self.count[template['name']] != ucount:
                    return True

            self._indent(self.urlset[template['name']])
            tree = ET.ElementTree(self.urlset[template['name']])

            destination_dir = os.path.dirname(self.output[template['name']])
            os.makedirs(destination_dir, exist_ok=True)

            tree.write(self.output[template['name']], xml_declaration=True, encoding='utf-8', method='xml')
            self.sitemap_index[template['name']].append(self.output[template['name']])


    def add(self, template, url_loc, lastmod=None, image_url=None):
        if ".html" not in url_loc:
            url_loc = url_loc.rstrip("/")+ "/index.html"
        url_loc = template['domain'] + url_loc
        if image_url:
            image_url = template['domain'] + image_url.strip("/")
        url = ET.SubElement(self.urlset[template['name']], 'url')
        loc = ET.SubElement(url, 'loc')
        loc.text = url_loc
        if lastmod:
            self.lastmod[template['name']] = max(self.lastmod[template['name']], lastmod)
            lastmod_elem = ET.SubElement(url, 'lastmod')
            lastmod_elem.text = lastmod
        if image_url:
            image_elem = ET.SubElement(url, 'image:image')
            image_loc = ET.SubElement(image_elem, 'image:loc')
            image_loc.text = image_url
        self.count[template['name']] += 1


    def add_post(self, post, superchare=True):

        for template in self.config['templates']:

            if superchare:
                if post['type'] == 5:
                    post = self.web.supercharge_tag(template, post, 1)
                else:
                    post = self.web.supercharge_post(template, post, 1)

            if not post:
                return None
            if 'pub_update_str' in post:
                pub_date = post['pub_update_str']
            else:
                pub_date = None
            thumb = None
            if 'thumb' in post and post['thumb']:
                if 'url' in post['thumb']:
                    thumb = post['thumb']['url']

            if pub_date is not None:
                self.lastmod[template['name']] = max(self.lastmod[template['name']], pub_date)
            self.add(template, post['url'], pub_date, thumb)


    def add_page(self, url, date=None, supercharge=True):
        
        for template in self.config['templates']:

            if date == None:
                date = tools.now_datetime_str()
            self.lastmod[template['name']] = max(self.lastmod[template['name']], date)
            self.add_post({"url": url, "pub_update_str": date }, supercharge)


    def save_index(self, sitemap_name, icount = None):

        for template in self.config['templates']:

            if icount:
                if len(self.sitemap_index) != icount:
                    return False

            output = os.path.join(template['export'], f"sitemap/{sitemap_name}.xml")
            index_element = ET.Element('sitemapindex', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')

            if not self.lastmod[template['name']]:
                self.lastmod[template['name']] = tools.now_datetime_str()

            for sitemap in self.sitemap_index[template['name']]:
                sitemap_elem = ET.SubElement(index_element, 'sitemap')
                loc = ET.SubElement(sitemap_elem, 'loc')
                loc.text = template['domain'] + os.path.basename(sitemap)

                lastmod_elem = ET.SubElement(sitemap_elem, 'lastmod')
                lastmod_elem.text = self.lastmod[template['name']]

            self._indent(index_element)
            index_tree = ET.ElementTree(index_element)
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