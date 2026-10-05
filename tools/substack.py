import re
import csv
import json
import difflib
import datetime
import unicodedata


class Substack:
    """
    Trouve l'URL Substack d'un billet.

    Priorité 1 : on calcule le slug deviné (heuristique de troncature)
                 puis on cherche, dans l'export CSV des posts Substack
                 (colonne post_id = "<id>.<slug-réel>"), le slug réel
                 le plus PROCHE de cette estimation (pas une égalité
                 stricte : la vraie troncature Substack est imprévisible).
    Priorité 2 : si rien d'assez proche n'est trouvé dans le CSV
                 (post pas encore publié, pas dans l'export...), on
                 garde directement le slug deviné par l'heuristique.
    """

    MAX_SLUG_LENGTH = 36  # <-- corrigé (était 48)

    # Seuil de similarité (0-1) en dessous duquel le repli flou
    # est jugé trop incertain pour être utilisé.
    FUZZY_MATCH_THRESHOLD = 0.85

    def __init__(self, config):
        self.config = config
        self.substack_fr = config.get('substack_fr', '')
        self.substack_727 = config.get('substack_727', '')
        self.substack_post_csv = config.get('substack_post_csv', '')
        self._csv_entries = None  # cache: [{'slug':..., 'date_key':...}, ...]

    def _extract_date_key(self, value):
        """
        Normalise une date (objet date/datetime ou chaîne ISO type
        "2026-10-04T09:46:48.555Z") en clé "YYYY-MM-DD" comparable.
        """
        if not value:
            return None
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.strftime("%Y-%m-%d")
        text = str(value).strip()
        if len(text) < 10:
            return None
        return text[:10]

    def _load_csv_entries(self):
        """
        Parcourt le CSV d'export Substack et retourne la liste des
        entrées {'slug': ..., 'date_key': ...}, le slug étant extrait
        de post_id ("<id>.<slug>" -> "<slug>") et la date de post_date.
        """
        entries = []
        if not self.substack_post_csv:
            return entries
        try:
            with open(self.substack_post_csv, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    post_id = (row.get("post_id") or "").strip()
                    if not post_id or "." not in post_id:
                        continue
                    # post_id = "<numeric_id>.<slug>"
                    real_slug = post_id.split(".", 1)[1]
                    if not real_slug:
                        continue
                    date_key = self._extract_date_key(row.get("post_date"))
                    entries.append({"slug": real_slug, "date_key": date_key})
        except (OSError, csv.Error):
            return []
        return entries

    def _lookup_csv_slug(self, title, date=None):
        """
        On calcule d'abord le slug deviné (heuristique, comme avant),
        puis on cherche dans le CSV le slug réel le plus PROCHE de
        cette estimation — pas une égalité stricte, car la vraie URL
        est presque toujours une troncature imprévisible du titre
        complet, donc rarement identique au slug calculé.

        En cas d'ambiguïté (plusieurs slugs proches), la date du post
        permet de lever le doute : si fournie, on restreint d'abord
        la recherche aux entrées CSV publiées le même jour.
        """
        if self._csv_entries is None:
            self._csv_entries = self._load_csv_entries()

        if not title or not self._csv_entries:
            return None

        guessed_slug = self.slugify(title)
        date_key = self._extract_date_key(date)

        candidates = self._csv_entries
        if date_key:
            same_day = [e for e in candidates if e["date_key"] == date_key]
            if same_day:
                candidates = same_day

        slug_pool = [e["slug"] for e in candidates]

        matches = difflib.get_close_matches(
            guessed_slug, slug_pool, n=1, cutoff=self.FUZZY_MATCH_THRESHOLD
        )
        return matches[0] if matches else None

    def _strip_accents(self, text):
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    def slugify(self, title):
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

        # On cherche d'abord le slug réel le plus proche dans le CSV
        # (la date du post lève l'ambiguïté si plusieurs slugs sont
        # proches) ; si rien d'assez proche, on garde le slug deviné
        # par l'heuristique.
        post_date = post.get('post_date')
        slug = self._lookup_csv_slug(title, post_date)
        if not slug:
            slug = self.slugify(title)

        return base.rstrip("/") + f"/p/{slug}"