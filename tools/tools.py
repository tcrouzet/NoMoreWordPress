import yaml
import hashlib
import os, sys
import subprocess
import json
import re
import locale
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Python 3.9+

PARIS_TZ = ZoneInfo("Europe/Paris")

def site_yml(path):
    with open(path, 'r') as file:
        return yaml.safe_load(file)
    
def run_script(script_name):
    try:
        subprocess.run(['python3', script_name], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running {script_name}: {e}")
        return False

def calculate_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def hash_content(content):
    hasher = hashlib.sha256()
    hasher.update(content.encode('utf-8'))
    return hasher.hexdigest()

def count_files(directory):
    file_count = 0
    for root, dirs, files in os.walk(directory):
        file_count += len(files)
    return file_count

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()
    return None

def get_root(path):
    directory = path.strip("/")
    parts = directory.split('/')
    root = parts[0].strip()
    if not root:
        root = "/"
    return root

def find_latest_file(directory):
    latest_file = None
    latest_time = 0

    for root, _, files in os.walk(directory):  # Traverse directory
        for file in files:
            file_path = os.path.join(root, file)
            file_time = os.path.getmtime(file_path)  # Get modification time

            if file_time > latest_time:  # Check if it's the latest
                latest_time = file_time
                latest_file = file_path

    return latest_file

def load_json(state_file):
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(state_file, state):
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=4)

def remove_markdown_images(markdown_text):
    """
    Supprime toutes les images d'un texte Markdown.
    Gère à la fois la syntaxe standard ![alt](url) et les variantes avec légendes.
    
    Args:
        markdown_text (str): Le texte Markdown d'entrée
        
    Returns:
        str: Le texte Markdown sans images
    """
    # Motif pour capturer les images markdown standard ![texte alt](url)
    pattern = r'!\[.*?\]\(.*?\)'
    
    # Suppression des images
    text_without_images = re.sub(pattern, '', markdown_text)
    
    return text_without_images

def format_timestamp_to_paris_time(timestamp: int) -> str:
    dt_paris = timestamp_to_paris_datetime(timestamp)
    return dt_paris.isoformat(timespec="seconds")

def timestamp_to_paris_datetime(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(PARIS_TZ)

def now_datetime() -> datetime:
    dt = datetime.now()
    return timestamp_to_paris_datetime( datetime.timestamp(dt) )

def now_datetime_str() -> str:
    dt_paris = now_datetime()
    return dt_paris.isoformat(timespec="seconds")

def month_year(timestamp: int) -> str:
    # Configure la locale pour obtenir le nom du mois en français
    try:
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8') 
    except locale.Error:
        locale.setlocale(locale.LC_TIME, 'fr_FR')

    dt_paris = timestamp_to_paris_datetime(timestamp)
    return dt_paris.strftime('%B %Y')    

def output_dir():
    output_dir = "_output"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir) + os.sep
    
    output_dir = os.path.join(parent_dir, "_output")
    os.makedirs(output_dir, exist_ok=True)

    return output_dir


def get_args_dict():
    """
    Analyse les arguments de ligne de commande (hors nom du script) 
    et retourne un dictionnaire de type {cle: valeur} 
    pour toutes les chaînes contenant un signe =.
    """
    args_dict = {}
    
    # sys.argv[1:] exclut le nom du script (sys.argv[0])
    for arg in sys.argv[1:]:
        # Vérifie si l'argument contient le séparateur clé=valeur
        if '=' in arg:
            try:
                # Sépare la chaîne au premier signe '='
                key, value = arg.split('=', 1)
                
                # Supprime les espaces autour de la clé et de la valeur (optionnel mais recommandé)
                key = key.strip()
                value = value.strip()
                
                if key:  # S'assure que la clé n'est pas vide
                    args_dict[key] = value
                
            except ValueError:
                print(f"⚠️ Erreur d'analyse de l'argument: {arg}")
        else:
            args_dict[arg.strip()] = True
            
    return args_dict