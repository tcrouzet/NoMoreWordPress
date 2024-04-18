# NoMoreWordPress

Début du projet le 18/4/2024, 13h

### wp_export (18/4/2024, 20h)

Renommer model.env en .env et y saisir les bonnes infos.

Le script se connecte à la base de données MySQL de WordPress, récupère tous les billets et crée une hiérarchie dans MARKDOWN_DIR.
Les tags et catégories se retrouvent en pied de page (et sont directement actifs sous Obsidian).
Les fichiers sont horodatés à leur date de création et de dernière modification.
Les images sont copiées depuis OLD_IMG_DIR dans NEW_IMG_DIR.
À la racine de ce dossier, on peut copier tools/server.py et l'exécuter pour qu'il serve les images aux éditeurs markdown.
Je ne copie pas directement les images dans la hiérarchie de fichiers pour ne pas l'alourdir.
Dans mon cas, j'ai accumulé 3,5 Go d'images pour 20 Mo de textes.