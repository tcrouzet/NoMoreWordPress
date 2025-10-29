"""Changer site.yml si mise à jour template"""
# audit_css.py
# python3 tools/audit_css.py


"""
audit_css.py (strict, sans safelist)
Analyse un site statique local: pour chaque sélecteur du CSS, vérifie s'il est
potentiellement utilisé en fonction des classes et IDs présents dans les HTML.

Sorties:
- css_audit_report.csv : liste de tous les sélecteurs avec statut "used"/"unused"
- Impression console des sélecteurs potentiellement non utilisés

Installation:
  pip install tinycss2 beautifulsoup4

Usage:
  1) Place ce script à la racine de ton projet (ou ajuste les chemins ci-dessous)
  2) Configure HTML_ROOT et CSS_FILE
  3) python audit_css.py
"""

from pathlib import Path
import re
import csv
import sys, os

from bs4 import BeautifulSoup
import tinycss2

import tools
import logs

sys.stdout = logs.DualOutput("./_log.txt")
sys.stderr = sys.stdout

os.system('clear')

config = tools.site_yml('./site.yml')

HTML_ROOT = Path(config['export'])
CSS_FILE = Path(os.path.join(HTML_ROOT, "style.css"))
OUTPUT_DIR = tools.output_dir()
OUTPUT = Path(os.path.join(OUTPUT_DIR,"css_audit.csv"))

# Marquer "used" les sélecteurs SANS classe ni ID (ex: h1, p, img)
# Si tu veux les considérer "inconnus" (et donc potentiellement unused),
# passe cette valeur à False (mais tu auras beaucoup de faux positifs).
MARK_TAG_ONLY_SELECTORS_AS_USED = True

# Affichage console: nombre max de sélecteurs "unused" à lister
CONSOLE_UNUSED_LIMIT = 150

# ======= LOGIQUE =======

def collect_html_files(root: Path):
    if not root.exists():
        print(f"[ERREUR] Dossier HTML introuvable: {root.resolve()}")
        return []
    return list(root.rglob("*.html"))

def extract_classes_ids_from_html(files):
    classes, ids = set(), set()
    for fp in files:
        try:
            html = fp.read_text(encoding="utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            # Classes
            for tag in soup.find_all(True):
                cls = tag.get("class")
                if cls:
                    for c in cls:
                        c = str(c).strip()
                        if c:
                            classes.add(c)
            # IDs
            for tag in soup.find_all(True):
                idv = tag.get("id")
                if idv:
                    idv = str(idv).strip()
                    if idv:
                        ids.add(idv)
        except Exception as e:
            print(f"[AVERTISSEMENT] Lecture problématique {fp}: {e}")
    return classes, ids

def parse_css_selectors(css_text: str):
    # Retourne une liste de "groupes" de sélecteurs (séparés par virgules)
    rules = tinycss2.parse_stylesheet(css_text, skip_comments=True, skip_whitespace=True)
    selectors = []
    for rule in rules:
        if rule.type != "qualified-rule":
            continue
        prelude = tinycss2.serialize(rule.prelude).strip()
        parts = [p.strip() for p in prelude.split(",") if p.strip()]
        if parts:
            selectors.append(parts)
    return selectors

def selector_tokens(sel: str):
    # Extrait .classes et #ids d'un sélecteur (sans interpréter combinators/attributs)
    classes = re.findall(r'\.([A-Za-z0-9_-]+)', sel)
    ids = re.findall(r'#([A-Za-z0-9_-]+)', sel)
    return set(classes), set(ids)

def main():
    if not CSS_FILE.exists():
        print(f"[ERREUR] CSS introuvable: {CSS_FILE.resolve()}")
        sys.exit(1)

    html_files = collect_html_files(HTML_ROOT)
    if not html_files:
        print(f"[ERREUR] Aucun HTML trouvé sous {HTML_ROOT.resolve()}")
        print("Astuce: ajuste HTML_ROOT ou génère ton site statique dans ce dossier.")
        sys.exit(1)

    print(f"[INFO] HTML trouvés: {len(html_files)} fichiers sous {HTML_ROOT.resolve()}")

    classes_in_html, ids_in_html = extract_classes_ids_from_html(html_files)
    print(f"[INFO] Classes uniques trouvées: {len(classes_in_html)}")
    print(f"[INFO] IDs uniques trouvés: {len(ids_in_html)}")

    css_text = CSS_FILE.read_text(encoding="utf-8", errors="ignore")
    selector_groups = parse_css_selectors(css_text)

    report_rows = []
    unused_selectors = []

    for group in selector_groups:
        group_used = False
        details = []

        for sel in group:
            cset, iset = selector_tokens(sel)

            # Strict: "used" seulement si au moins une classe ou un ID du sélecteur est présent dans le HTML
            used = False
            if cset and any(c in classes_in_html for c in cset):
                used = True
            if iset and any(i in ids_in_html for i in iset):
                used = True

            # Sélecteur sans classe ni id (tag-only)
            if not cset and not iset:
                used = MARK_TAG_ONLY_SELECTORS_AS_USED

            details.append((sel, "used" if used else "unused"))
            if used:
                group_used = True

        if not group_used:
            for sel, status in details:
                if status == "unused":
                    unused_selectors.append(sel)

        for sel, status in details:
            report_rows.append({"selector": sel, "status": status})


    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["selector", "status"])
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"[OK] Rapport écrit: {OUTPUT.resolve()}")

    if unused_selectors:
        print(f"[RÉSUMÉ] Sélecteurs potentiellement non utilisés: {len(unused_selectors)}")
        for s in unused_selectors[:CONSOLE_UNUSED_LIMIT]:
            print(" -", s)
        if len(unused_selectors) > CONSOLE_UNUSED_LIMIT:
            print(f" ... et {len(unused_selectors) - CONSOLE_UNUSED_LIMIT} autres")
    else:
        print("[RÉSUMÉ] Aucun sélecteur manifestement non utilisé détecté selon cette méthode.")

if __name__ == "__main__":
    main()