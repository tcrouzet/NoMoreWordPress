import yaml
from tqdm import tqdm
import os, sys
import shutil
import tools.logs
import hashlib
from PIL import Image
from git import Repo, GitCommandError
from datetime import datetime

sys.stdout = tools.logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

with open('site.yml', 'r') as file:
    config = yaml.safe_load(file)

def calculate_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def count_files(directory):
    file_count = 0
    for root, dirs, files in os.walk(directory):
        file_count += len(files)
    return file_count

def sync_files(src, dst):

    # Étape 1: Copier de la source vers la destination
    total = count_files(src)
    pbar = tqdm(total=total, desc='MD:')
    for root, dirs, files in os.walk(src):
        for file in files:

            if file == ".DS_Store":
                continue

            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, src)
            dst_path = os.path.join(dst, rel_path)

            if file.endswith('.md'):
                # Pour les fichiers Markdown, copier si différent ou inexistant
                if not os.path.exists(dst_path) or calculate_hash(src_path) != calculate_hash(dst_path):
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)
            else:
                # Pour les médias
                if not os.path.exists(dst_path):
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                    if src_path.endswith(".webp"):

                        try:

                            with Image.open(src_path) as img:
                                (width, height) = img.size
                                new_width = 1024
                                ratio = (new_width / float(width))
                                new_height = int((float(height) * float(ratio)))
                                img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                                img_resized.save(dst_path)

                        except Exception as e:
                            print(e)

                        # print(src_path)
                        # exit()

                    else:
                        shutil.copy2(src_path, dst_path)
            pbar.update(1)
    pbar.close()


def clean_files(src, dst, preserved_files):

    # Étape 2: Nettoyer la destination
    for root, dirs, files in os.walk(dst):
        for file_name in files:

            if file_name == ".DS_Store":
                continue

            dst_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(dst_path, dst)

            if file_name in preserved_files:
                continue

            if file_name.startswith(".") or rel_path.startswith("."):
                continue

            if os.path.exists( os.path.join(src,rel_path) ):
                continue

            os.remove(dst_path)
            print(f"Removed {dst_path}")


def index():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(script_dir, "templates", config['template'], "md.html")
    dst_path = os.path.join(config['export_github_md'], "index.html")

    if not os.path.exists(dst_path) or calculate_hash(src_path) != calculate_hash(dst_path):
        shutil.copy2(src_path, dst_path)


preserved_files = ["CNAME", "LICENSE", "README.md", "SECURITY.md"]
sync_files(config['vault'], config['export_github_md'])
clean_files(config['vault'], config['export_github_md'], preserved_files)
index()

repo = Repo(config['export_github_md'])

repo.git.add(all=True)

# Créer un commit
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
commit_message = f"Force update - {now}"

try:
    repo.git.commit('-m', commit_message, allow_empty=True)
    
    # Pousser les changements
    origin = repo.remote(name='origin')
    origin.push('main', force=True)

    print("Github MD commit done")
except GitCommandError as e:
    print(f"Erreur lors du commit : {e}")