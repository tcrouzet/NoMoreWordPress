import yaml
import hashlib
import os
import subprocess
import json
import re

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