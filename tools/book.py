import mysql.connector
import os, sys
import wp_export_secret as wp_export_secret
import logs
import yaml
from urllib.parse import urlparse

def is_url(url):
    resultat = urlparse(url)
    return bool(resultat.scheme and resultat.netloc)

sys.stdout = logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

os.system('clear')

prefix = wp_export_secret.WP_DB_PREFIX

# Connexion à la base de données MySQL
conn = mysql.connector.connect(
    host=wp_export_secret.WP_DB_HOST,
    port=wp_export_secret.WP_DB_PORT,
    user=wp_export_secret.WP_DB_USER,
    password=wp_export_secret.WP_DB_PASSWORD,
    database=wp_export_secret.WP_DB_NAME,
    buffered=True
)

cursor = conn.cursor(dictionary=True)

query = f"""
SELECT
    b.*,
    l.*
FROM tc_bookshop_books AS b
LEFT JOIN tc_bookshop AS l ON b.book_name = l.book
ORDER BY book_id DESC
"""

#print(query)
cursor.execute(query)

livres = []
stores = []
book_name = None

for book in cursor:
    
    #print(book['book_title'])

    if book['book_name'] != book_name:

        #New book
        if book_name:
            # Save Old book
            new['shops'] = stores
            book_data={"book": new}
            livres.append(book_data)

        book_name = book['book_name']

        new = {
            'name': book['book_name'],
            'date': book['book_date'],
            'genre': book['book_genre'],
            'isbn13': book['book_isbn13'],
            'isbn13e': book['book_isbn13e'],
            'editor': book['book_editor'],
            'baseline': book['book_baseline'],
            'exergue': book['book_exergue'],
            'incipit': book['book_incipit'],
            'blabla': book['book_blabla'],
            'details_h': book['book_details_h'],
            'lire': book['book_lire'],
            'thema': book['book_thema'],
            'shops': ""
        }

        stores = []

    result = urlparse(book['mail'])
    if book["mail"] and is_url(book['mail']) and book['prix'] and book['data'] :
        shop = {"prix": book['prix'], "shop": book["data"], "url": book["mail"]}
        stores.append(shop)
    
new['shops'] = stores
book_data={"book": new}
livres.append(book_data)

with open('books.yml', 'w') as fichier:
    yaml.dump(livres, fichier, allow_unicode=True)
