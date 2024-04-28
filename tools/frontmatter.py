class Frontmatter:

    def __init__(self, yalm):
        self.yalm = yalm

    def shop(self, url):
        if "amazon" in url:
            return "Amazon"
        if "7switch.com" in url:
            return "7switch"
        if "kobo" in url:
            return "Kobo"
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
        if "leslibraires.fr" in url:
            return "Les Libraires"
        if "librest.com" in url:
            return "Librest"
        if "parislibrairies.fr" in url:
            return "Paris Librairies"
        if "mollat.com" in url:
            return "Mollat"
        if "initiales.org" in url:
            return "Initiales"
        if "vivlio.com" in url or "bookeen" in url:
            return "Vivlio"
        if "les12singes.com" in url:
            return "Les XII Singes"
        if "trictrac.net" in url:
            return "Trictrac"
        if "cocote.com" in url:
            return "Cocote"
        if "troll2jeux" in url:
            return "Troll2jeux"
        if "librairiedialogues" in url:
            return "Dialogues"
        if "placedeslibraires" in url:
            return "Place des libraires"
        if "epagine.fr" in url:
            return "ePagine"
        if "barnesandnoble" in url:
            return "Barnes and Noble"
        if "arbrealettres" in url:
            return "L'arbre à lettres"
        if "numilog.com" in url:
            return "Numilog"
        
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
