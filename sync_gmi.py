import os, sys, re
import shutil
import tools.tools
import tools.logs
import tools.github
from collections import defaultdict
from md2gemini import md2gemini

sys.stdout = tools.logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

config = tools.tools.site_yml('site.yml')

# https://github.com/makew0rld/md2gemini
def markdown_to_gemini(markdown_text, year, month):

    title = None
    lines = markdown_text.split('\n')    
    # Find first title
    for line in lines:
        if line.startswith('# ') and not title:
            title = line.strip('# ').strip()
            break

    # Supprime exposant
    markdown_text = markdown_text.replace("<sup>", "")
    markdown_text = markdown_text.replace("</sup>", "")

    # Supprimer tags
    markdown_text = re.sub(r'^#\S+(?:\s+#\S+)*\s*$', '', markdown_text, flags=re.MULTILINE)

    # gemini = md2gemini(markdown_text, links="paragraph")
    gemini = md2gemini(markdown_text, links="copy")

    gemini = gemini.replace("=> _i/", f"=> https://github.com/tcrouzet/md/raw/main/{year}/{month}/_i/")
    gemini = gemini.replace("**","")

    return gemini, title


def sync_files(src, dst):

    print(f"GMI syncing {src} to {dst}")

    entries = defaultdict(list)

    for root, dirs, files in os.walk(src):

        # print(f"Scanning directory: {root}")
        # print(f"Files found: {files}")

        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:

            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, src).replace(".md", ".gmi")
            dst_path = os.path.join(dst, rel_path)

            if file == "README.md" or file == "SECURITY.md" or file.startswith(".")  or file.startswith("_"):
                continue

            if file == "LICENSE":
                shutil.copy2(src_path, dst_path)
                continue

            if "/comments/" not in src_path and dst_path.endswith('.gmi'):
                # Pour les fichiers Markdown, copier si différent ou inexistant

                content = tools.tools.read_file(src_path)
                if content is None:
                    continue

                # Extraire year et month du chemin
                path_parts = rel_path.split(os.sep)  # divise le chemin en segments
                if len(path_parts) >= 2:  # vérifie qu'il y a au moins year/month
                    year = path_parts[0]
                    if year =="page" or year == "books":
                        continue
                    month = path_parts[1]
                else:
                    continue

                gmi, title = markdown_to_gemini(content, year, month)

                if year and month:
                    entries[f"{year}-{month.zfill(2)}"].append(f"=> {rel_path} {title}\n")
                
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                if not os.path.exists(dst_path) or tools.tools.calculate_hash(dst_path) != tools.tools.hash_content(gmi):
                    print("New file: ", dst_path)
                    with open(dst_path, 'w', encoding='utf-8') as f:
                        f.write(gmi)


    if entries:
        sorted_keys = sorted(entries.keys(), reverse=True)
        index_gmi = "# Thierry Crouzet\n"
        for key in sorted_keys:
            index_gmi += f"# {key}\n"
            for text in entries[key]:
                index_gmi += text

        with open(os.path.join(dst, "index.gmi"), 'w', encoding='utf-8') as f:
            f.write(index_gmi)

# test = "/Users/thierrycrouzet/Documents/GitHub/tcrouzet/2025/01/decembre-2024.md"
# print( markdown_to_gemini( tools.tools.read_file(test), "2025", "01" ) )

sync_files(config['export_github_md'], config['gemini_export'] )
# shutil.copy2("sourcehut.yml", os.path.join(config['gemini_export'], ".build.yml") )


gh = tools.github.MyGitHub(config, "tcrouzet", config['gemini_export'], "sourcehut")
gh.push()
