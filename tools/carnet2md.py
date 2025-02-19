"""Export only the Carnet or spectific tag in _output dir
python3 tools/carnet2md.py
"""


import os, yaml
import re
import csv
from datetime import datetime
import tools

os.system('clear')

config = tools.site_yml('site.yml')


script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
output_dir = os.path.join(project_root, "_output")
carnet_file = os.path.join(output_dir, "carnet.md")

#output_file = 'journal.md'
output_file_csv = 'journal.csv'

# Créer le répertoire de sortie s'il n'existe pas
os.makedirs(output_dir, exist_ok=True)

# Mapping des mois en français vers leur numéro
mois_mapping = {
    "janvier": "01", "février": "02", "mars": "03", "avril": "04", "mai": "05", "juin": "06",
    "juillet": "07", "août": "08", "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"
}

mois_mapping_bdc = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12
}

def extract_date(filename):
    """Fonction pour sélectionner les fichiers du carnet"""
    match = re.search(r'carnet-de-route-(\w+)-(\d{4})\.md', filename)
    if match:
        mois, annee = match.groups()
        mois_num = mois_mapping_bdc.get(mois.lower())
        if mois_num:
            return datetime(int(annee), mois_num, 1)
        
    match = re.search(r'(\w+)-(\d{4})\.md', filename)
    if match:
        mois, annee = match.groups()
        mois_num = mois_mapping_bdc.get(mois.lower())
        if mois_num:
            return datetime(int(annee), mois_num, 1)
    return None

def modifier_date(ligne, annee, mois):
    def remplacement(match):
        jour_texte = match.group(1)
        numero_jour = match.group(2).zfill(2)  # Formatage du numéro du jour avec zfill(2)
        return f"{jour_texte}{annee}/{mois}/{numero_jour}"

    # Utiliser une fonction de remplacement pour le formatage
    return re.sub(r'(### \w+ )(\d+)', remplacement, ligne)

def to_valid_filename(text):
    # Remove invalid characters
    filename = re.sub(r'[\/\0\|*?"<>]', '', text)

    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Remove leading/trailing whitespace
    filename = filename.strip()

    # Convert to lowercase
    filename = filename.lower()

    # Shorten the filename if it's too long
    max_length = 255
    if len(filename) > max_length:
        filename = filename[:max_length]

    # Avoid reserved filenames
    reserved_names = ['con', 'aux', 'nul', 'prn', 'com1', 'com2', 'com3', 'com4', 'lpt1', 'lpt2', 'lpt3', 'lpt4']
    if filename in reserved_names:
        filename = '_' + filename

    return filename

# Fonction pour modifier le contenu du fichier md
def modifier_contenu(fichier):
    contenu_modifie = ""
    mois, annee = None, None

    with open(fichier, 'r', encoding='utf-8') as file:
        lignes = file.readlines()

    for ligne in lignes:
        # Trouver les titres de mois
        if ligne.startswith("# "):
            mois, annee = ligne.strip("# ").split()
            mois = mois_mapping[mois.lower()]
            continue

        # Modifier les entrées de journal
        if ligne.startswith("### "):
            ligne = ligne.replace('1<sup>er</sup>', '1')
            contenu_modifie += modifier_date(ligne, annee, mois)
            continue

        # Supprimer les liens vers les images
        if re.search(r'!\[.*\]\(.*\)', ligne):
            continue

        # Supprimer les commentaires
        ligne = re.sub(r'~[^~]*~', '', ligne)
        ligne = re.sub(r'<span[^>]*>.*?</span>', '', ligne)

        # Supprime liens
        ligne = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', ligne)

        contenu_modifie += ligne

    #Vire triples sauts
    contenu_modifie = re.sub(r'\n{3,}', '\n\n', contenu_modifie)
    #Vire 2 sauts au début
    contenu_modifie = re.sub(r'^\n{1,2}', '', contenu_modifie, count=1)

    return contenu_modifie


def convertir_md_en_csv(fichier_md, fichier_csv):
    # Lire le fichier Markdown
    with open(fichier_md, 'r') as file:
        contenu = file.readlines()

    # Préparer les données pour le CSV
    donnees = []
    texte = ""
    date = ""
    lieu = ""
    jour = ""
    for ligne in contenu:
        # Rechercher les entrées de journal
        if ligne.startswith("### "):
            # New date and lieu

            if date and jour and lieu and texte.strip():
                # Sauvegarder l'entrée précédente avant de passer à la suivante
                donnees.append({"Date": date, "Jour":jour, "Lieu": lieu, "Texte": texte.strip()})
                texte = ""

            match = re.search(r'### (\w+) (\d+)/(\d+)/(\d+), (\w+)', ligne)
            if match:
                jour, annee, mois, jour_num, lieu = match.groups()
                date = f"{annee}-{mois.zfill(2)}-{jour_num.zfill(2)}"  # Format YYYY-MM-DD
        else:
            # Collecter le texte du journal
            texte += ligne.strip() + " "

    donnees.append({"Date": date, "Jour": jour, "Lieu": lieu, "Texte": texte.strip()})

    # Écrire les données dans un fichier CSV
    with open(fichier_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Date', 'Jour', 'Lieu', 'Texte']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for entree in donnees:
            writer.writerow(entree)


def journal():
    #Trouver les fichiers et extraire les dates
    file_dates = []
    for root, dirs, files in os.walk(config['export_github_md']):
        for file in files:
            date = extract_date(file)
            if date:
              file_dates.append((os.path.join(root, file), date))

    # Étape 3 : Trier les fichiers en ordre antichronologique
    file_dates.sort(key=lambda x: x[1], reverse=False)

    # Étape 4 : Concaténer les fichiers
    with open(carnet_file, 'w', encoding='utf-8') as outfile:
        for file_path, _ in file_dates:
            with open(file_path, 'r', encoding='utf-8') as infile:
                file_content = infile.readlines()
                tags, file_content = find_tags(file_content)
                if tags and "carnets" in tags:
                    outfile.write('\n\n'.join(file_content) + '\n\n')

    contenu_final = modifier_contenu(carnet_file)

    # Écrire le contenu modifié dans un nouveau fichier
    with open(carnet_file, 'w', encoding='utf-8') as modified_file:
        modified_file.write("# Journal de Thierry Crouzet\n\n")
        modified_file.write(contenu_final)

def find_tags(file_content):
    """Recherche les tags dans le texte"""
    lines = [line.strip() for line in file_content if line.strip()]  # Supprimer les lignes vides
    if lines:
        last_line = lines[-1]  # Prendre la dernière ligne non vide
        if last_line.startswith('#'):
            tags = last_line.split(' ')
            tags = [tag.strip("#") for tag in tags]
            return tags, lines[:-1] 
    return None, lines


def contains_tags(file_path):
    #print(file_path)
    with open(file_path, 'r') as file:
        return find_tags(file)


def tagpage(tag):
  output_file=to_valid_filename(tag)+".md"
  myfiles = []
  mypages = []
  for root, dirs, files in os.walk('md'):
      for file in files:
          if file.endswith('.md'):
              file_path = os.path.join(root, file)
              if tag in file_path:
                  #Tag dans le titre
                  priority = 10
                  if("md/page/les-727-aventures-bikepacking-en-herault.md"==file_path): priority = 0
                  if("md/page/727tour.md"==file_path): priority = 1
                  if("md/page/i727.md"==file_path): priority = 1
                  if("md/page/g727.md"==file_path): priority = 1
                  if("md/page/727gd.md"==file_path): priority = 2
                  if("md/page/g727gd.md"==file_path): priority = 2
                  #print(file_path)
                  mypages.append((file_path,priority))
              else:
                  tags = contains_tags(file_path)
                  #print(tags)
                  if tags and tag in tags:
                      myfiles.append(file_path)

  outfile = ""
  mypages.sort(key=lambda x: x[1])

  for file_path, _ in mypages:
      with open(file_path, 'r') as infile:
          outfile += infile.read() + '\n\n'

  for file_path in myfiles:
      with open(file_path, 'r') as infile:
          outfile += infile.read() + '\n\n'

  with open(output_file, 'w') as modified_file:
      modified_file.write(outfile)

  print(output_file, "done!!!")

#tagpage("Born to Bike")
#tagpage("727")

#convertir_md_en_csv(output_file, output_file_csv)

journal()