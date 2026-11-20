import re
import csv
import json
import os
import difflib
import datetime
import unicodedata


class Substack:
    """Résout l'URL par correction manuelle, export publié puis heuristique."""

    MAX_SLUG_LENGTH = 36  # <-- corrigé (était 48)

    # Seuil de similarité (0-1) en dessous duquel le repli flou
    # est jugé trop incertain pour être utilisé.
    FUZZY_MATCH_THRESHOLD = 0.85

    def __init__(self, config):
        self.config = config
        self.substack_fr = config.get('substack_fr', '')
        self.substack_727 = config.get('substack_727', '')
        self.substack_post_csv = config.get('substack_post_csv', '')
        self._csv_entries = None  # cache: [{'slug':..., 'title':..., 'date_key':...}, ...]
        self._slug_map = None     # cache: {slug_source: slug_substack}

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.parent_dir = os.path.dirname(script_dir) + os.sep
        if self.substack_post_csv:
            self.substack_post_csv = os.path.join(self.parent_dir, os.path.expanduser(self.substack_post_csv))

        self.STOP_WORDS = {"un", "une", "le", "la", "les", "de", "des", "du", "et", "a", "en", "au", "aux", "ou", "ce", "se", "sa", "son"}

        self.slug_path = None
        if config.get('substack_slug_csv'):
            self.slug_path = os.path.join(self.parent_dir, os.path.expanduser(config['substack_slug_csv']))


    def _extract_date_key(self, value):
        """Normalise un timestamp, une date ou une chaîne ISO en jour UTC."""
        if not value:
            return None
        try:
            if isinstance(value, (int, float)):
                value = datetime.datetime.fromtimestamp(value, datetime.timezone.utc)
            elif isinstance(value, str):
                value = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            if isinstance(value, datetime.datetime):
                if value.tzinfo:
                    value = value.astimezone(datetime.timezone.utc)
                value = value.date()
            return value.isoformat() if isinstance(value, datetime.date) else None
        except (ValueError, TypeError, OverflowError, OSError):
            return None


    def _lookup_csv_slug(self, title, date=None, window_days=7):
        if self._csv_entries is None:
            self._csv_entries = self._load_csv_entries()

        if not title or not self._csv_entries:
            return None

        normalized_title = self._normalize_title(title)
        exact = [entry for entry in self._csv_entries if entry["title"] == normalized_title]
        exact_slugs = {entry["slug"] for entry in exact}
        if len(exact_slugs) == 1:
            return exact_slugs.pop()

        date_key = self._extract_date_key(date)
        if not date_key:
            return None

        target_date = datetime.date.fromisoformat(date_key)
        matches = []
        guessed_slug = self.slugify(title)
        for entry in exact or self._csv_entries:
            if not entry["date_key"]:
                continue
            entry_date = datetime.date.fromisoformat(entry["date_key"])
            distance = abs((entry_date - target_date).days)
            if distance > window_days:
                continue
            if entry["title"]:
                score = difflib.SequenceMatcher(None, normalized_title, entry["title"], autojunk=False).ratio()
            else:
                score = difflib.SequenceMatcher(None, guessed_slug, entry["slug"], autojunk=False).ratio()
            if score >= self.FUZZY_MATCH_THRESHOLD:
                matches.append((score, -distance, entry["slug"]))

        if not matches:
            return None
        best = max(matches, key=lambda match: match[:2])
        best_slugs = {slug for score, distance, slug in matches if (score, distance) == best[:2]}
        return best_slugs.pop() if len(best_slugs) == 1 else None

    def _lookup_csv_path(self, post):
        if self._slug_map is None:
            self._slug_map = self._load_slug_map()

        title = self._normalize_title((post.get('title') or '').strip())
        return self._slug_map.get(title, "")


    def _strip_accents(self, text):
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c))


    def slugifyOld(self, title):
        # Substack ne coupe PAS au premier ':' ',' ';' etc.
        # Il slugifie le titre entier puis tronque au nombre de
        # caractères max, en revenant au dernier tiret complet.
        head = self._strip_accents(title).lower()
        head = head.replace("'", "").replace("’", "")
        head = re.sub(r"[^a-z0-9]+", "-", head)
        head = re.sub(r"-{2,}", "-", head).strip("-")
        if len(head) > self.MAX_SLUG_LENGTH:
            truncated = head[: self.MAX_SLUG_LENGTH]
            # Ne reculer jusqu'au tiret précédent que si la coupe tombe
            # au milieu d'un mot (le caractère suivant n'est pas un tiret).
            # Si la coupe tombe pile sur une fin de mot, on la garde telle quelle.
            cuts_mid_word = head[self.MAX_SLUG_LENGTH] != "-"
            if cuts_mid_word and "-" in truncated:
                truncated = truncated.rsplit("-", 1)[0]
            head = truncated.strip("-")
        return head


    def slugify(self, title):
        head = self._strip_accents(title).lower()
        head = head.replace("'", "").replace("’", "")
        head = re.sub(r"[^a-z0-9]+", "-", head)
        head = re.sub(r"-{2,}", "-", head).strip("-")
        if len(head) > self.MAX_SLUG_LENGTH:
            truncated = head[: self.MAX_SLUG_LENGTH]
            cuts_mid_word = head[self.MAX_SLUG_LENGTH] != "-"
            if cuts_mid_word and "-" in truncated:
                truncated = truncated.rsplit("-", 1)[0]
            # recule encore tant que le dernier segment est un mot-outil
            parts = truncated.strip("-").split("-")
            while len(parts) > 1 and parts[-1] in self.STOP_WORDS:
                parts = parts[:-1]
            head = "-".join(parts)
        return head


    def guess(self, post):

        type = post.get('type', 0)
        if type>0:
            return ""

        raw_tags = post.get('tags', '') or ''
        try:
            tags = set(json.loads(raw_tags)) if isinstance(raw_tags, str) else set(raw_tags)
        except (TypeError, json.JSONDecodeError):
            tags = set(re.findall(r"[A-Za-z0-9_-]+", str(raw_tags)))

        base = self.substack_727 if 'velo' in tags else self.substack_fr

        title = post.get('title')
        if not (base and title):
            return ""

        # Priorité 1 : correction manuelle (titre_source -> slug_substack)
        slug = self._lookup_csv_path(post)
        if not slug:
            # Priorité 2 : titre exact, puis titre proche à ±7 jours.
            post_date = post.get('pub_date') or post.get('pub_date_str') or post.get('post_date')
            slug = self._lookup_csv_slug(title, post_date)
            if not slug:
                # Priorité 3 : slug fabriqué par l'heuristique
                slug = self.slugify(title)
        return base.rstrip("/") + f"/p/{slug}"

    def _load_csv_entries(self):
        """
        Parcourt le CSV d'export Substack et retourne la liste des
        entrées {'slug': ..., 'title': ..., 'date_key': ...}, le slug étant extrait
        de post_id ("<id>.<slug>" -> "<slug>") et la date de post_date.
        """
        entries = []
        if not self.substack_post_csv:
            return entries
        try:
            with open(self.substack_post_csv, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (row.get("is_published", "true") or "").strip().casefold() not in ("true", "1"):
                        continue
                    post_id = (row.get("post_id") or "").strip()
                    if not post_id or "." not in post_id:
                        continue
                    # post_id = "<numeric_id>.<slug>"
                    real_slug = post_id.split(".", 1)[1]
                    if not real_slug:
                        continue
                    date_key = self._extract_date_key(row.get("post_date"))
                    entries.append({"slug": real_slug, "title": self._normalize_title(row.get("title")), "date_key": date_key})
        except (OSError, csv.Error):
            return []
        return entries

    def _load_slug_map(self):
        mapping = {}
        if not self.slug_path:
            return mapping
        try:
            with open(self.slug_path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    titre_source = (row.get("titre_source") or "").strip()
                    slug_substack = (row.get("slug_substack") or "").strip()
                    if titre_source and slug_substack:
                        key = self._normalize_title(titre_source)
                        mapping[key] = slug_substack
        except (OSError, csv.Error):
            return {}
        return mapping

    def _normalize_title(self, text):
        if not text:
            return ""
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\u00a0", " ").replace("\u202f", " ")  # NBSP, NNBSP
        text = text.replace("’", "'").replace("‘", "'")
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s+([?!:;])", r"\1", text)
        return text.casefold()
