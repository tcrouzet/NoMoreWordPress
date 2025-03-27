from tqdm import tqdm
import os, sys, re
import shutil
import tools.tools
import tools.logs
import tools.github
from PIL import Image

sys.stdout = tools.logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

config = tools.tools.site_yml('site.yml')

def sync_files(src, dst):

    print(f"Syncing {src} to {dst}")
    # Étape 1: Copier de la source vers la destination
    total = tools.tools.count_files(src)
    pbar = tqdm(total=total, desc='MD:')
    for root, dirs, files in os.walk(src):

        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:

            if file == "LICENSE" or file == "README.md" or file.startswith(".")  or file.startswith("_"):
                continue

            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, src)
            dst_path = os.path.join(dst, rel_path)

            if file.endswith('.md'):
                # Pour les fichiers Markdown, copier si différent ou inexistant

                if "/comments/" not in src_path:

                    content = tools.tools.read_file(src_path)
                    if content is None:
                        continue

                    # Vérifie si tag date présent
                    match = re.search(r'#\d{4}-\d{1,2}-\d{1,2}-\d{1,2}h\d{1,2}', content)

                    if not match:
                        # Not yet on line
                        # print(f"Missing date tag in {src_path}")
                        continue

                if not os.path.exists(dst_path) or tools.tools.calculate_hash(src_path) != tools.tools.calculate_hash(dst_path):
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

    if not os.path.exists(dst_path) or tools.tools.calculate_hash(src_path) != tools.tools.calculate_hash(dst_path):
        shutil.copy2(src_path, dst_path)


gh = tools.github.MyGitHub(config, "md", config['export_github_md'])

# Quand des fichiers montent pas
#gh.sync_local_with_github()
# exit()

preserved_files = ["CNAME", "LICENSE", "README.md", "SECURITY.md"]
sync_files(config['vault'], config['export_github_md'])
clean_files(config['vault'], config['export_github_md'], preserved_files)
index()

gh.pull()
gh.push()
# gh.sync_and_push()