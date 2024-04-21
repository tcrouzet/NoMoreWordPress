import sqlite3
import os
import re
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir) + os.sep
script_dir = parent_dir

temp_dir = os.path.join(script_dir, "_temp")
os.makedirs(temp_dir, exist_ok=True)

db = os.path.join(temp_dir, "posts.db")

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

def create_table_posts(reset=False):
    global conn
    c = conn.cursor()

    if reset:
        c.execute('DROP TABLE IF EXISTS posts')

    c.execute(f'''CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                title TEXT,
                path_md TEXT UNIQUE,
                pub_date INTEGER,
                pub_update INTEGER,
                thumb_path TEXT DEFAULT '',
                thumb_legend TEXT DEFAULT '',
                type INTEGER CHECK(type IN (0, 1, 2)),  -- 0 pour post, 1 pour page, 2 book page
                tags TEXT DEFAULT '[]',
                updated BOOLEAN DEFAULT FALSE
              );''')
    conn.commit()

def insert_post(conn, post):

    if 'tags' in post and isinstance(post['tags'], list):
        post['tags'] = json.dumps(post['tags'])

    query = '''INSERT OR IGNORE INTO posts 
               (title, path_md, pub_date, pub_update, thumb_path, thumb_legend, type, tags)
               VALUES (:title, :path_md, :pub_date, :pub_update, :thumb_path, :thumb_legend, :type, :tags)
               ON CONFLICT(path_md) DO UPDATE SET
                    title = excluded.title,
                    pub_date = excluded.pub_date,
                    pub_update = excluded.pub_update,
                    thumb_path = excluded.thumb_path,
                    thumb_legend = excluded.thumb_legend,
                    type = excluded.type,
                    tags = excluded.tags,
                    updated = TRUE
                WHERE excluded.pub_update > pub_update;             
               '''
    c = conn.cursor()
    c.execute(query, post)
    if c.rowcount > 0:
        return True
    else:
        return False


def filter_tags(tags):
    date_pattern = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')  # Correspond à 'YYYY-M-D'
    year_pattern = re.compile(r'^y\d{4}$')  # Correspond à 'yYYYY'
    filtered_tags = [tag for tag in tags if not date_pattern.match(tag) and not year_pattern.match(tag)]    
    return filtered_tags


def markdown_extract(path):
    creation_time = round(os.path.getctime(path))
    modification_time = round(os.path.getmtime(path))
    
    # Read the file and extract title and tags
    title = None
    tags = []
    thumb_path = None
    thumb_legend = None
    with open(path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        for line in lines:
            # Find title
            if line.startswith('# ') and not title:
                title = line.strip('# ')
                title = title.strip()
            # Check tags
            if line.startswith('#') and ' ' in line:
                potential_tags = line.strip().split()
                if all(tag.startswith('#') for tag in potential_tags):
                    tags = [tag[1:] for tag in potential_tags if tag.startswith('#')]
                    tags = filter_tags(tags)
            #Thumb
            if '![' in line and thumb_path is None:
                match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
                if match:
                    thumb_legend = match.group(1)
                    thumb_path = match.group(2)

        if thumb_path and not thumb_legend:
            thumb_legend = title
        return {"pub_date":creation_time, "pub_update":modification_time, "title":title, "tags":tags, "thumb_legend":thumb_legend, "thumb_path":thumb_path}
        
    return None


def db_builder(root_dir,reset=False):
    global conn

    create_table_posts(reset)
    count_added = 0

    for root, dirs, files in os.walk(root_dir):
        # Exlude images dirs
        dirs[:] = [d for d in dirs if not d.startswith('_i')]

        for file in files:
            if file.endswith('.md'):
                md_path = os.path.join(root, file)
                #print(root,file,root.replace(root_dir,""))
                post = markdown_extract(md_path)

                post['path_md'] = os.path.join(root.replace(root_dir,"").strip("/"), file)

                if post['path_md'].startswith("page"):
                    post['type'] = 1
                else:
                    post['type'] = 0
                
                #print(post)
                #exit()

                if insert_post(conn, post):
                    count_added += 1

        conn.commit()

    return count_added


def get_posts(condition=None):
    global conn
    c = conn.cursor()

    if condition:
        where = f"WHERE {condition}"
    else:
        where = ""
    query = f"SELECT * FROM posts {where} ORDER BY pub_date DESC"
    c.execute(query)
    return c.fetchall()

def get_posts_updated():
    return get_posts("updated=1")

def list_posts(condition=None):
    posts = get_posts(condition)
    for post in posts:
        print(dict(post))

def list_posts_updated():
    list_posts("updated=1")


def get_posts_by_tag(tag):
    global conn
    c = conn.cursor()
    
    query = f'''
    SELECT * FROM posts, json_each(posts.tags)
    WHERE json_each.value = ?
    ORDER BY pub_date ASC
    '''
    c.execute(query, (tag,))
    posts = c.fetchall()
    return posts