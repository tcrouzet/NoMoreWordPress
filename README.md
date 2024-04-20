# NoMoreWordPress

Début du projet le 18/4/2024

### wp_export.py

Renommer model.env en .env et y saisir les bonnes infos.

Le script se connecte à la base de données MySQL de WordPress, récupère tous les billets et crée une hiérarchie dans MARKDOWN_DIR.
Les tags et catégories se retrouvent en pied de page (et sont directement actifs sous Obsidian).
Les fichiers sont horodatés à leur date de création et de dernière modification.
Les fichiers sont organisé par année et mois.
Les images sont copiées depuis OLD_IMG_DIR dans IMG_SUB_DIR de chacun des mois.
Tous les liens internes commes les les liens images sont relatifs.

### gen.py
