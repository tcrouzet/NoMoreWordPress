import yaml
import os, sys
import shutil
import tools.logs
from git import Repo
from datetime import datetime

#chmod -R 777 /Users/thierrycrouzet/Documents/GitHub/blog/images_tc
    
sys.stdout = tools.logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

print(f"GitHub commit…")

with open('site.yml', 'r') as file:
    config = yaml.safe_load(file)


def copy_if_new(source, target):
    if os.path.exists(target):
        return 0
    try:
        shutil.copy2(source, target)
        return 1
    except Exception as e:
        print(f"Erreur lors de la copie de {source} vers {target}: {e}")
        return -1


def test_directory_creation(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            print(f"Directory created: {path}")
        else:
            print(f"Directory already exists: {path}")
    except Exception as e:
        print(f"Error creating directory {path}: {e}")
        exit()


def filter_and_copy_images(source_dir, target_dir):

    print(f"source: {source_dir} target: {target_dir}")
    total = 0

    os.makedirs(target_dir,  exist_ok=True)

    for root, dirs, files in os.walk(source_dir):

        dest_root = root.replace(source_dir, target_dir)
        os.makedirs(dest_root, exist_ok=True)
        # if not os.path.exists(dest_root):
        #     print(dest_root)
        #     os.makedirs(dest_root, exist_ok=True)
        #     test_directory_creation(dest_root)
    
        # Filtrer et copier les fichiers
        for file in files:

            file_path = os.path.join(root, file)
            target = os.path.join( dest_root, file.replace("-1024.",".") )
            
            if "-1024." in file:
                total += copy_if_new(file_path,target)
            elif "-250." in file:
                continue
            elif ".webp" in file:
                continue
            else:
                total += copy_if_new(file_path,target)

    print(f"Total new images: {total}")


def copy_and_update_html(source_dir, target_dir):

    #print(f"source: {source_dir} target: {target_dir}")

    images_dir_full_path = os.path.abspath(os.path.join(source_dir, config['images_dir'].strip("/")))
    #print(images_dir_full_path)
    #exit()


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

                    target_path = file_path.replace(source_dir, target_dir)
                    #print(f"source: {file_path} target: {target_path}")
                    #exit()

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

repo = Repo(config['export_github_html'])

for remote in repo.remotes:
    print(remote.name, remote.url)

# Nettoyage du dépôt
# repo.git.reset('--hard')
# repo.git.clean('-fd')

repo.git.add(all=True)

# Créer un commit
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
commit_message = f"Force update - {now}"
repo.git.commit('-m', commit_message, allow_empty=True)

# Pousser les changements
origin = repo.remote(name='origin')

try:
    #origin.push('main', force=True)
    origin.push('main')
except Exception as e:
    print(f"An error occurred: {e}")

print("Github commit done")