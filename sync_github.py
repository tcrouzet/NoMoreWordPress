import yaml
import os, sys
import shutil
import tools.logs
from git import Repo
from datetime import datetime


sys.stdout = tools.logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

os.system('clear')

with open('site.yml', 'r') as file:
    config = yaml.safe_load(file)


def filter_and_copy_images(source_dir, target_dir):

    os.makedirs(target_dir,  exist_ok=True)

    for root, dirs, files in os.walk(source_dir):

        dest_root = root.replace(source_dir, target_dir)
        os.makedirs(dest_root, exist_ok=True)

        # Filtrer et copier les fichiers
        for file in files:

            file_path = os.path.join(root, file)
            
            if "-1024." in file:
                shutil.copy2(file_path, os.path.join(dest_root, file.replace("-1024.",".") ))
            elif "-250." in file:
                continue
            elif ".webp" in file:
                continue
            else:
                shutil.copy2(file_path, os.path.join(dest_root, file ))


def copy_and_update_html(source_dir, target_dir):

    images_dir_full_path = os.path.abspath(os.path.join(source_dir, config['images_dir'].strip("/")))

    for root, dirs, files in os.walk(source_dir):

        dest_root = root.replace(source_dir, target_dir)
        os.makedirs(dest_root, exist_ok=True)

        for file in files:
            
            file_path = os.path.join(root, file)

            if  images_dir_full_path in file_path:
                continue

            if file.endswith('.json'):
                continue

            if file.endswith('.html'):

                try:

                    #print(file_path)
                    target_path = file_path.replace(source_dir, target_dir)
                    #print(target_path)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    updated_content = content.replace("-250.webp", ".webp").replace("-1024.webp", ".webp")

                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)

                except Exception as e:
                    print(e)

            else:
                shutil.copy2(file_path, os.path.join(dest_root, file ))


source_img = os.path.join(config['export'], config['images_dir'].strip("/"))
target_img = os.path.join(config['export_github_html'], config['images_dir'].strip("/"))
filter_and_copy_images(source_img, target_img)
copy_and_update_html(config['export'], config['export_github_html'])


print(config['export_github_html'])
repo = Repo(config['export_github_html'])
repo.git.add(all=True)

# Créer un commit
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
commit_message = f"Auto-{now}"
repo.git.commit('-m', commit_message)

# Pousser les changements
origin = repo.remote(name='origin')
origin.push('main', set_upstream=True)

print("Github commit done")