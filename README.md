# NoMoreWordPress

Création d'un site à partir d'une hiérarchie de fichiers markdown.

Le site est décrit dans site.yml (renommer le fichier site_model.yml et modifier les paramètres).

Son look est défit par un template dans le dossier templates.

### wp_export.py


Le script se connecte à la base de données MySQL de WordPress, récupère tous les billets et crée une hiérarchie dans MARKDOWN_DIR.
Les tags et catégories se retrouvent en pied de page (et sont directement actifs sous Obsidian).
Les fichiers sont organisés par année et mois.
Les images sont copiées depuis OLD_IMG_DIR dans IMG_SUB_DIR de chacun des mois.
Tous les liens internes commes les liens images sont relatifs (et actifs).

### gen.py

### sync.py

