#!/usr/bin/env python3
"""Génère des diaporamas géographiques à partir des images EXIF du journal."""

import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

import tools


EARTH_RADIUS = 6_371_000
GPS_IFD = 0x8825
IMAGE_PATTERN = re.compile(
    r'!\[(?P<alt>[^]]*)]\((?:\.\./)*_i/(?P<name>[^\s)]+\.webp)(?:\s+[^)]*)?\)',
    re.IGNORECASE,
)


def decimal_coordinate(values, reference):
    degrees, minutes, seconds = (float(value) for value in values)
    coordinate = degrees + minutes / 60 + seconds / 3600
    return -coordinate if reference in ('S', 'W') else coordinate


def image_metadata(path):
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            if not exif or GPS_IFD not in exif:
                return None
            gps = exif.get_ifd(GPS_IFD)
            if not all(key in gps for key in (1, 2, 3, 4)):
                return None
            latitude = decimal_coordinate(gps[2], gps[1])
            longitude = decimal_coordinate(gps[4], gps[3])
            captured = exif.get(36867) or exif.get(306) or ''
            if captured:
                try:
                    captured = datetime.strptime(
                        str(captured), '%Y:%m:%d %H:%M:%S'
                    ).isoformat()
                except ValueError:
                    captured = str(captured)
            return latitude, longitude, captured
    except (OSError, TypeError, ValueError, ZeroDivisionError):
        return None


def projected_point(latitude, longitude):
    """Projection métrique locale suffisante pour un quadrillage français."""
    reference_latitude = math.radians(46.5)
    x = EARTH_RADIUS * math.radians(longitude) * math.cos(reference_latitude)
    y = EARTH_RADIUS * math.radians(latitude)
    return x, y


def hilbert_index(x, y, size):
    distance = 0
    scale = size // 2
    while scale:
        rx = 1 if x & scale else 0
        ry = 1 if y & scale else 0
        distance += scale * scale * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x = size - 1 - x
                y = size - 1 - y
            x, y = y, x
        scale //= 2
    return distance


def distance_squared(first, second):
    return (
        (first['_x'] - second['_x']) ** 2
        + (first['_y'] - second['_y']) ** 2
    )


def order_geographically(points, grid_km):
    if not points:
        return []
    cell_size = grid_km * 1000
    cells = {}
    for point in points:
        point['_x'], point['_y'] = projected_point(point['lat'], point['lon'])
        cell = (
            math.floor(point['_x'] / cell_size),
            math.floor(point['_y'] / cell_size),
        )
        cells.setdefault(cell, []).append(point)

    min_x = min(cell[0] for cell in cells)
    min_y = min(cell[1] for cell in cells)
    width = max(
        max(cell[0] - min_x for cell in cells),
        max(cell[1] - min_y for cell in cells),
    ) + 1
    hilbert_size = 1
    while hilbert_size < width:
        hilbert_size *= 2
    ordered_cells = sorted(
        cells,
        key=lambda cell: hilbert_index(
            cell[0] - min_x, cell[1] - min_y, hilbert_size
        ),
    )

    ordered = []
    previous = None
    for sector_number, cell in enumerate(ordered_cells, start=1):
        remaining = list(cells[cell])
        if previous is None:
            current = min(remaining, key=lambda point: point.get('date') or '')
        else:
            current = min(
                remaining, key=lambda point: distance_squared(previous, point)
            )
        while remaining:
            remaining.remove(current)
            current['sector'] = sector_number
            ordered.append(current)
            previous = current
            if remaining:
                current = min(
                    remaining, key=lambda point: distance_squared(previous, point)
                )

    for point in ordered:
        point.pop('_x', None)
        point.pop('_y', None)
    return ordered


def write_if_changed(path, content):
    if path.is_file() and path.read_text(encoding='utf-8') == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return True


def ensure_page(vault, kind):
    page = vault / f'diaporama-{kind}.md'
    if page.exists():
        return False
    label = 'VTT' if kind == 'vtt' else 'gravel'
    content = f'''---
layout: diaporama
diaporama: {kind}
metatitle: "Diaporama {label}"
metadescription: "Photos géolocalisées des reconnaissances {label}."
---

# Diaporama {label}

#page #2026-8-2-12h00
'''
    return write_if_changed(page, content)


def main():
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        raise SystemExit('Usage: python3 tools/diaporama.py SITE')
    site = sys.argv[1].strip()
    config = tools.site_yml(site)
    slideshow_config = config.get('diaporamas')
    if not slideshow_config:
        print(f'Diaporamas non configurés pour {site}.')
        return

    vault = Path(config['vault'])
    static_folder = vault / config.get('static_folder', 'static')
    grid_km = int(slideshow_config.get('grid_km', 25))
    kinds = tuple(slideshow_config.get('types', ('vtt', 'gravel')))
    points = {kind: [] for kind in kinds}
    seen = {kind: set() for kind in kinds}

    for markdown in sorted(vault.glob('20*/*/*.md')):
        text = markdown.read_text(encoding='utf-8')
        selected = [
            kind for kind in kinds
            if re.search(rf'(?<!\w)#{re.escape(kind)}\b', text, re.IGNORECASE)
        ]
        if not selected:
            continue
        relative = markdown.relative_to(vault)
        year, month = (int(value) for value in relative.parts[:2])
        for match in IMAGE_PATTERN.finditer(text):
            image_path = markdown.parent / '_i' / match.group('name')
            metadata = image_metadata(image_path)
            if not metadata:
                continue
            latitude, longitude, captured = metadata
            image_url = (
                '/' + config.get('images_dir', '/images/').strip('/')
                + f'/{year:04d}/{month:02d}/{match.group("name")}'
            )
            for kind in selected:
                key = (str(image_path), latitude, longitude)
                if key in seen[kind]:
                    continue
                seen[kind].add(key)
                points[kind].append({
                    'image': image_url,
                    'lat': round(latitude, 7),
                    'lon': round(longitude, 7),
                    'date': captured,
                    'alt': match.group('alt').strip(),
                })

    for kind in kinds:
        ordered = order_geographically(points[kind], grid_km)
        payload = {
            'type': kind,
            'grid_km': grid_km,
            'count': len(ordered),
            'points': ordered,
        }
        output = static_folder / f'diaporama-{kind}.json'
        changed = write_if_changed(
            output,
            json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
        )
        ensure_page(vault, kind)
        state = 'mis à jour' if changed else 'inchangé'
        print(f'{kind}: {len(ordered)} photos, {output} {state}.')


if __name__ == '__main__':
    main()
