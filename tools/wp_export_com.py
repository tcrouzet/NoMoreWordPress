import yaml
import mysql.connector
import os, sys
import html
from markdownify import markdownify as md
import re
import shutil
import unidecode
import logs
from datetime import datetime

sys.stdout = logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

os.system('clear')

with open('site.yml', 'r') as file:
    config = yaml.safe_load(file)

if config['vault']:
    export_folder = config['vault'] + os.sep
else:
    exit("No Vault")

export_folder = "/Users/thierrycrouzet/Documents/GitHub/BlogComments"

os.makedirs(export_folder, exist_ok=True)

prefix = config['WP_DB_PREFIX']

# Connexion à la base de données MySQL
conn = mysql.connector.connect(
    host=config['WP_DB_HOST'],
    port=config['WP_DB_PORT'],
    user=config['WP_DB_USER'],
    password=config['WP_DB_PASSWORD'],
    database=config['WP_DB_NAME'],
    buffered=True
)

def get_export_filepath(post):
    filename = tag_format(post['post_name'])+".md"
    title = html_to_markdown(post['post_title'])
    if post['post_type'] == 'page':
        export_path = os.path.join( "page", filename)
        return export_path, title
    elif post['post_type'] == 'post':
        year = post['post_date'].year
        month = post['post_date'].month
        export_path = os.path.join( str(year), str(month), filename)
        return export_path, title
    else:
        return False

def tag_format(tag):
    tag = unidecode.unidecode(tag.strip())
    tag = tag.lower()
    tag = tag.replace(" ", "_")
    tag = tag.replace("’", "")
    tag = tag.replace("'", "")
    tag = tag.replace("%e2%80%99", "")
    return tag
    
def html_to_markdown(html_content):
    html_content = html.unescape(html_content)
    html_content = md(html_content)
    html_content = re.sub(r'[ \t]*\n[ \t]*', '\n', html_content)
    html_content = re.sub(r'\n\s*\n', '\n', html_content)
    html_content = html_content.lstrip('\n')
    html_content = re.sub(r'\n', '\n\n', html_content)
    html_content = re.sub(r'\n{2,}', '\n\n', html_content)
    html_content = html_content.replace("'","’")
    return html_content


def fetch_comments(post_id):
    cursor = conn.cursor(dictionary=True)
    query = f"""
    SELECT comment_content, comment_date, comment_author, comment_author_email
    FROM {prefix}comments
    WHERE comment_post_ID = %s AND comment_approved = 1
    ORDER BY comment_date
    """
    cursor.execute(query, (post_id,))
    comments = cursor.fetchall()
    cursor.close()
    return comments

def clean_comment_content(comment_content):
    pattern = re.compile(r'post:.*?\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\)')
    cleaned_content = re.sub(pattern, '', comment_content).strip()
    return cleaned_content

def save_comments_to_markdown(post, export_folder):
    filepath, title =  get_export_filepath(post)
    save_file = os.path.join(export_folder, filepath)
    os.makedirs(os.path.dirname(save_file), exist_ok=True)

    with open( save_file, 'w', encoding='utf-8') as file:

        link_to_source = f"[{title}](../../../{filepath})"
        file.write(f"{link_to_source}\n\n---\nn")

        for comment in comments:
            comment_content = html_to_markdown( clean_comment_content(comment['comment_content']) )
            comment_date = comment['comment_date'].strftime('%Y-%m-%d %H:%M:%S')
            author = html_to_markdown(comment['comment_author'] or comment['comment_author_email']  or "Anonyme")
            file.write(f"{author} @ {comment_date}\n\n{comment_content}\n\n---\n\n")

cursor = conn.cursor(dictionary=True)

query = f"""
SELECT p.ID, p.post_name, p.post_date, p.post_type, p.post_title
FROM {prefix}posts AS p
WHERE p.post_status = 'publish'
"""

cursor.execute(query)

for post in cursor:
    if post['post_name'] in config['EXCLUDE']:
        continue

    comments = fetch_comments(post['ID'])
    if comments:
        save_comments_to_markdown(post, export_folder)

cursor.close()
conn.close()
