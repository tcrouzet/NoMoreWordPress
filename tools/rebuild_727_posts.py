"""Reconstruit les anciens posts Jekyll 727 sous forme de vault."""

import json
import re
import shutil
from pathlib import Path

import yaml
from PIL import Image, ImageOps


SOURCE = Path("/Users/thierrycrouzet/Documents/GitHub/727")
TARGET = Path(__file__).resolve().parent.parent / "_temp" / "727-vault-preview"
POST_PATTERN = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})-(?P<name>.+)\.md$"
)
SLIDESHOW_PATTERN = re.compile(
    r"{%\s*include\s+slideshow\.html\s*%}", re.IGNORECASE
)
MARKDOWN_IMAGE_PATTERN = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<path>/images/posts/[^)]+)\)"
)


def safe_filename(filename):
    """Évite les espaces et parenthèses ambigus dans les liens Markdown."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-")


def webp_filename(filename):
    return f"{Path(safe_filename(filename)).stem}.webp"


def load_slideshows():
    data_path = SOURCE / "_data" / "posts.yml"
    with data_path.open("r", encoding="utf-8") as data_file:
        return yaml.safe_load(data_file) or {}


def split_frontmatter(text):
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not match:
        return {}, text
    metadata = yaml.safe_load(match.group(1)) or {}
    return metadata, text[match.end():]


def image_metadata(slideshows, date, source_dir):
    ordered = []
    used = set()
    for image in slideshows.get(date, []):
        filename = str(image.get("image", "")).strip()
        if filename and (source_dir / filename).is_file():
            ordered.append((filename, str(image.get("alt", "") or "")))
            used.add(filename)

    if source_dir.is_dir():
        for source_path in sorted(source_dir.iterdir()):
            if (
                source_path.is_file()
                and not source_path.name.startswith(".")
                and source_path.name not in used
            ):
                ordered.append((source_path.name, ""))
    return ordered


def markdown_images(images, relative_image_dir):
    return "\n\n".join(
        f"![{alt}]({relative_image_dir}/{webp_filename(filename)})"
        for filename, alt in images
    )


def tags_for(title, body, year, month, day):
    searchable = f"{title} {body}".lower()
    tags = ["reco"]
    for tag in ("g727", "i727", "o727", "pou100"):
        if re.search(rf"\b{re.escape(tag)}\b", searchable):
            tags.append(tag)
    tags.append(f"{year}-{int(month)}-{int(day)}-12h00")
    return " ".join(f"#{tag}" for tag in tags)


def convert_image(source_path, target_path):
    if target_path.exists():
        return

    with Image.open(source_path) as source_image:
        image = ImageOps.exif_transpose(source_image)
        if image.width > 1600:
            height = round(image.height * 1600 / image.width)
            image = image.resize((1600, height), Image.Resampling.LANCZOS)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "transparency" in image.info else "RGB")
        image.save(target_path, "WEBP", quality=85, method=4)


def convert_images(images, source_dir, target_dir):
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename, _ in images:
        convert_image(
            source_dir / filename,
            target_dir / webp_filename(filename)
        )


def rebuild_post(post_path, slideshows):
    match = POST_PATTERN.match(post_path.name)
    if not match:
        return None

    parts = match.groupdict()
    year, month, day = parts["year"], parts["month"], parts["day"]
    date = f"{year}-{month}-{day}"
    target_month = TARGET / year / str(int(month))
    target_post = target_month / f"{int(day):02d}-{parts['name']}.md"
    relative_image_dir = "_i"
    target_image_dir = target_month / relative_image_dir

    text = post_path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(text)
    body = body.replace("\u00a0", " ").replace("\u202f", " ")
    title = str(metadata.get("title") or post_path.stem)
    source_image_dir = SOURCE / "images" / "posts" / date
    images = image_metadata(slideshows, date, source_image_dir)

    if images:
        replacement = markdown_images(images, relative_image_dir)
        body = SLIDESHOW_PATTERN.sub(replacement, body)
        convert_images(images, source_image_dir, target_image_dir)
    else:
        body = SLIDESHOW_PATTERN.sub("", body)

    def replace_direct_image(image_match):
        source_relative = image_match.group("path").lstrip("/")
        source_path = SOURCE / source_relative
        if not source_path.is_file():
            return image_match.group(0)
        target_image_dir.mkdir(parents=True, exist_ok=True)
        target_name = webp_filename(source_path.name)
        convert_image(source_path, target_image_dir / target_name)
        return f"![{image_match.group('alt')}]({relative_image_dir}/{target_name})"

    body = MARKDOWN_IMAGE_PATTERN.sub(replace_direct_image, body).strip()
    tags = tags_for(title, body, year, month, day)
    rebuilt = f"# {title}\n\n{body}\n\n{tags}\n"

    target_post.parent.mkdir(parents=True, exist_ok=True)
    target_post.write_text(rebuilt, encoding="utf-8")
    return len(images)


def main():
    if TARGET.exists():
        shutil.rmtree(TARGET)
    TARGET.mkdir(parents=True)
    vscode_dir = TARGET / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "settings.json").write_text(
        json.dumps({"editor.colorDecorators": False}, indent=2) + "\n",
        encoding="utf-8"
    )

    slideshows = load_slideshows()
    post_count = 0
    image_count = 0
    posts_without_slideshow_images = []

    for post_path in sorted((SOURCE / "_posts").glob("*.md")):
        copied_images = rebuild_post(post_path, slideshows)
        if copied_images is None:
            continue
        post_count += 1
        image_count += copied_images
        if copied_images == 0:
            posts_without_slideshow_images.append(post_path.name)

    print(f"Vault: {TARGET}")
    print(f"Posts: {post_count}")
    print(f"Slideshow images: {image_count}")
    print(f"Posts without slideshow images: {len(posts_without_slideshow_images)}")
    for filename in posts_without_slideshow_images:
        print(f"  - {filename}")


if __name__ == "__main__":
    main()
