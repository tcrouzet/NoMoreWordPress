import yaml
import hashlib
import os


def site_yml(path):
    with open(path, 'r') as file:
        return yaml.safe_load(file)

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
