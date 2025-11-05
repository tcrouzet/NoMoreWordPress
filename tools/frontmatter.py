from datetime import date, datetime
import yaml

class Frontmatter:

    def __init__(self, yaml_lines):
        """
        Args:
            yaml_text: Texte brut du frontmatter (sans les ---)
        """
        self.yaml_text = '\n'.join(yaml_lines)
        self.yalm = yaml.safe_load(self.yaml_text)
        self.supercharge()
        self.yalm = self._serialize_value(self.yalm)

        # print(self.yalm)

    def __call__(self):
        return self.yalm

    def _serialize_value(self, value):
        """Convertit récursivement les dates en strings ISO"""
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        else:
            return value


    def shop(self, url) ->str:
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
        if "alaflamme.fr" in url:
            return "À la flamme"
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
        if "vilvio" in url:
            return "Vilvio"
        if "laprocure" in url:
            return "La Procure"
        
        return url

    def supercharge(self) ->dict:
        if not self.yalm:
            exit("NoYALM")
        if "baseline" in self.yalm:
            #book
            if "prix" in self.yalm:
                self.yalm['papier'] = f"<b>papier {self.yalm["prix"]} €</b> "
                if "shops" in self.yalm and self.yalm["shops"]:
                    for shop in self.yalm["shops"]:
                        self.yalm['papier'] += f'<a href="{shop}">{self.shop(shop)}</a> '
            if "eprix" in self.yalm and self.yalm["eprix"]:
                self.yalm['ebook'] = f"<b>ebook {self.yalm["eprix"]} €</b> "
                if "eshops" in self.yalm and self.yalm["eshops"]:
                    for shop in self.yalm["eshops"]:
                        self.yalm['ebook'] += f'<a href="{shop}">{self.shop(shop)}</a> '
