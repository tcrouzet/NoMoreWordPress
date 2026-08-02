#!/usr/bin/env python3
"""Reconstruit les WebP d'un journal depuis ses images originales datées."""

import argparse
import os
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageChops, ImageOps, ImageStat


IMAGE_PATTERN = re.compile(
    r'!\[[^]]*]\((?:\.\./)*_i/(?P<name>[^\s)]+\.webp)(?:\s+[^)]*)?\)',
    re.IGNORECASE,
)
GPS_IFD = 0x8825


def normalized_stem(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')


def gps_data(image):
    exif = image.getexif()
    return exif.get_ifd(GPS_IFD) if exif and GPS_IFD in exif else None


def source_score(path):
    with Image.open(path) as image:
        exif = image.getexif()
        return (
            bool(gps_data(image)),
            len(exif),
            path.suffix.lower() in ('.jpg', '.jpeg', '.tif', '.tiff'),
            path.stat().st_size,
        )


def source_for(source_dir, webp_name):
    wanted = normalized_stem(Path(webp_name).stem)
    candidates = [
        path for path in source_dir.iterdir()
        if path.is_file() and normalized_stem(path.stem) == wanted
    ] if source_dir.is_dir() else []
    if not candidates:
        return None
    return candidates


def visual_distance(source, current_webp):
    with Image.open(source) as source_image, Image.open(current_webp) as current:
        source_image = ImageOps.exif_transpose(source_image).convert('RGB')
        current = ImageOps.exif_transpose(current).convert('RGB')
        source_image = source_image.resize((64, 64), Image.Resampling.LANCZOS)
        current = current.resize((64, 64), Image.Resampling.LANCZOS)
        return sum(ImageStat.Stat(ImageChops.difference(source_image, current)).rms)


def rebuild(source, destination, max_width):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.tmp.webp')
    with Image.open(source) as original:
        source_has_gps = bool(gps_data(original))
        image = ImageOps.exif_transpose(original)
        if image.width > max_width:
            height = round(image.height * max_width / image.width)
            image = image.resize((max_width, height), Image.Resampling.LANCZOS)

        exif = image.getexif()
        save_args = {'format': 'WEBP', 'quality': 85, 'method': 6}
        if exif:
            save_args['exif'] = exif.tobytes()
        if original.info.get('icc_profile'):
            save_args['icc_profile'] = original.info['icc_profile']
        image.save(temporary, **save_args)

    with Image.open(temporary) as result:
        if result.width > max_width:
            raise RuntimeError(f'Largeur invalide pour {destination}: {result.width}')
        if source_has_gps and not gps_data(result):
            raise RuntimeError(f'GPS perdu pendant la conversion de {source}')
    os.replace(temporary, destination)
    return source_has_gps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('vault', type=Path)
    parser.add_argument('original_posts', type=Path)
    parser.add_argument('--max-width', type=int, default=1600)
    args = parser.parse_args()

    converted = gps_count = reference_count = 0
    missing = []
    sources_by_target = defaultdict(set)

    for markdown in sorted(args.vault.glob('20*/*/*.md')):
        relative = markdown.relative_to(args.vault)
        year, month = relative.parts[:2]
        day = markdown.stem.split('-', 1)[0]
        date = f'{int(year):04d}-{int(month):02d}-{int(day):02d}'
        source_dir = args.original_posts / date
        text = markdown.read_text(encoding='utf-8')
        for match in IMAGE_PATTERN.finditer(text):
            reference_count += 1
            name = match.group('name')
            sources = source_for(source_dir, name)
            if not sources:
                missing.append((str(relative), name))
                continue
            destination = markdown.parent / '_i' / name
            sources_by_target[destination].update(sources)

    absent_targets = []
    collisions = 0
    for destination, sources in sorted(
        sources_by_target.items(), key=lambda item: str(item[0])
    ):
        name = destination.name
        if not destination.is_file():
            absent_targets.append(name)
            continue
        if len(sources) > 1:
            collisions += 1
            source = min(
                sources,
                key=lambda candidate: (
                    visual_distance(candidate, destination),
                    tuple(-part if isinstance(part, int) else part for part in source_score(candidate))
                )
            )
        else:
            source = next(iter(sources))
        has_gps = rebuild(source, destination, args.max_width)
        converted += 1
        gps_count += int(has_gps)

    print(f'Références analysées: {reference_count}')
    print(f'WebP reconstruits: {converted}')
    print(f'WebP avec GPS: {gps_count}')
    print(f'Noms désambiguïsés visuellement: {collisions}')
    print(f'WebP cibles absents: {len(absent_targets)}')
    for name in absent_targets:
        print(f'  absent: {name}')
    print(f'Références non reconstruites: {len(missing)}')
    for markdown, name in missing:
        print(f'  {markdown}: {name}')


if __name__ == '__main__':
    main()
