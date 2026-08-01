"""Rapatrie les anciennes images publiques des pages 727 dans leurs `_i`."""

import re
from pathlib import Path

from PIL import Image, ImageOps


VAULT = Path("/Users/thierrycrouzet/Documents/ObsidianLocal/text/727")
OLD_SITE = Path("/Users/thierrycrouzet/Documents/GitHub/727")
IMAGE_PATTERN = re.compile(
    r"(?P<path>(?:\.\./|/)?images/[^\s)\"']+)"
)


def webp_name(source):
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", source.stem).strip("-")
    return f"{safe_stem}.webp"


def convert_image(source, target):
    with Image.open(source) as source_image:
        image = ImageOps.exif_transpose(source_image)
        if image.width > 1600:
            height = round(image.height * 1600 / image.width)
            image = image.resize((1600, height), Image.Resampling.LANCZOS)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert(
                "RGBA" if "transparency" in image.info else "RGB"
            )
        image.save(target, "WEBP", quality=85, method=4)


def migrate_markdown(markdown_path):
    content = markdown_path.read_text(encoding="utf-8")
    replacements = {}

    for match in IMAGE_PATTERN.finditer(content):
        old_reference = match.group("path")
        source_relative = old_reference.removeprefix("../").lstrip("/")
        source = OLD_SITE / source_relative
        if not source.is_file():
            raise FileNotFoundError(f"Missing old image: {source}")

        image_dir = markdown_path.parent / "_i"
        image_dir.mkdir(exist_ok=True)
        target_name = webp_name(source)
        target = image_dir / target_name
        convert_image(source, target)
        replacements[old_reference] = f"_i/{target_name}"

    for old_reference, new_reference in replacements.items():
        content = content.replace(old_reference, new_reference)

    if replacements:
        markdown_path.write_text(content, encoding="utf-8")
    return len(replacements)


def main():
    migrated = 0
    for markdown_path in VAULT.rglob("*.md"):
        migrated += migrate_markdown(markdown_path)
    print(f"Images migrated to _i: {migrated}")


if __name__ == "__main__":
    main()
