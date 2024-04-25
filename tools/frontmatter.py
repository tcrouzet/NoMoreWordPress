class Frontmatter:

    def __init__(self, yalm):
        self.yalm = yalm

    def shop(self, url):
        if "amazon.fr" in url:
            return "Amazon"
        if "7switch.com" in url:
            return "7switch"
        if "kobo.com" in url:
            return "Kobo"
        if "vivlio.com" in url:
            return "Vivlio"
        if "apple.com" in url:
            return "Apple"
        if "google.com" in url:
            return "Google"
        if "decitre.fr" in url:
            return "Decitre"
        if "fnac.com" in url:
            return "Fnac"
        if "eyrolles.com" in url:
            return "Eyrolles"
        if "sauramps.com" in url:
            return "Sauramps"
        if "furet.com" in url:
            return "Furet du Nord"
        if "cultura.com" in url:
            return "Cultura"
        if "lalibrairie.com" in url:
            return "La Librairie"
        
        return url

    def supercharge(self):
        if not self.yalm:
            return None
        if "baseline" in self.yalm:
            #book
            if "prix" in self.yalm:
                self.yalm['papier'] = f"papier {self.yalm["prix"]} € "
                if "shops" in self.yalm:
                    for shop in self.yalm["shops"]:
                        self.yalm['papier'] += f'<a href="{shop}">{self.shop(shop)}</a> '
            if "eprix" in self.yalm:
                self.yalm['ebook'] = f"ebook {self.yalm["eprix"]} € "
                if "eshops" in self.yalm:
                    for shop in self.yalm["eshops"]:
                        self.yalm['ebook'] += f'<a href="{shop}">{self.shop(shop)}</a> '

        return self.yalm
