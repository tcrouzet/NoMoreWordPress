import subprocess
import socket
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

import db
import logs
import tools
import web


sys.stdout = logs.DualOutput("_log.txt")
sys.stderr = sys.stdout


class SubstackEditor:
    CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

    def __init__(self, config, database, template, substack_url):
        self.config = config
        self.database = database
        self.template = template
        self.substack_url = substack_url.rstrip("/")
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.chrome_process = None
        self.start_chrome()

    @property
    def editor_url(self):
        return f"{self.substack_url}/publish/post/"

    @property
    def dashboard_url(self):
        return f"{self.substack_url}/publish/home"

    @staticmethod
    def free_port():
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            return listener.getsockname()[1]

    def start_chrome(self):
        if not self.CHROME.is_file():
            raise SystemExit(f"Google Chrome introuvable : {self.CHROME}")

        port = self.free_port()
        self.chrome_process = subprocess.Popen([
            str(self.CHROME),
            f'--user-data-dir={self.config["playwright_profile"]}',
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--start-maximized",
            self.dashboard_url,
        ])
        self.playwright = sync_playwright().start()
        endpoint = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 15
        while True:
            try:
                self.browser = self.playwright.chromium.connect_over_cdp(endpoint)
                break
            except PlaywrightError:
                if time.monotonic() >= deadline:
                    raise SystemExit("Impossible de se connecter au Chrome Substack.")
                time.sleep(.25)

        if not self.browser.contexts:
            raise SystemExit("Chrome n’a fourni aucun contexte de navigation.")
        self.context = self.browser.contexts[0]
        self.page = self.context.pages[-1] if self.context.pages else self.context.new_page()

    def close(self):
        if self.browser is not None:
            self.browser.close()
            self.browser = None
        if self.playwright is not None:
            self.playwright.stop()
            self.playwright = None
        self.context = None
        self.page = None

    def login_form_visible(self, timeout=4000):
        if any(part in self.page.url.lower() for part in ("sign-in", "signin", "login")):
            return True
        try:
            self.page.wait_for_selector(
                'input[type="email"], input[name="email"]',
                timeout=timeout,
            )
            return True
        except PlaywrightTimeoutError:
            return False

    def ensure_authenticated(self):
        self.page.goto(self.dashboard_url, wait_until="domcontentloaded")
        if not self.login_form_visible():
            print("Session Substack active.")
            return

        print("Session Substack absente.")
        input(
            "Connecte-toi et termine le 2FA dans cette fenêtre Chrome. "
            "Quand le tableau de bord est affiché, appuie sur Entrée… "
        )
        self.page.goto(self.dashboard_url, wait_until="domcontentloaded")
        if self.login_form_visible():
            raise SystemExit(
                "La connexion Substack n’a pas été enregistrée dans le profil."
            )
        print("Session Substack enregistrée.")

    def prepare(self, post):
        generated = web.Web(self.config, self.database).supercharge_post(
            self.template,
            post,
        )
        html = generated["content"]
        thumb = generated.get("thumb") or {}
        thumb_url = thumb.get("url")
        if thumb_url and thumb_url not in html:
            legend = thumb.get("legend", "")
            html = f'<img src="{thumb_url}" alt="{legend}" />{html}'
        return generated, html.replace(
            'src="/',
            f'src="{self.template["domain"].rstrip("/")}/',
        )

    def paste_html(self, html):
        editor = self.page.locator('div[data-testid="editor"]')
        plain_text = BeautifulSoup(html, "html.parser").get_text("\n")
        self.context.grant_permissions(
            ["clipboard-read", "clipboard-write"],
            origin=self.substack_url,
        )
        self.page.evaluate(
            """
            async ({html, plainText}) => {
                await navigator.clipboard.write([
                    new ClipboardItem({
                        'text/html': new Blob([html], {type: 'text/html'}),
                        'text/plain': new Blob([plainText], {type: 'text/plain'})
                    })
                ]);
            }
            """,
            {"html": html, "plainText": plain_text},
        )
        editor.click()
        editor.press("Meta+A")
        editor.press("Backspace")
        editor.press("Meta+V")
        self.page.wait_for_timeout(1000)

        if not editor.inner_text().strip():
            raise RuntimeError("Le collage dans l’éditeur Substack a échoué.")

    def paste_title(self, title):
        title_field = self.page.locator("#post-title")
        self.context.grant_permissions(
            ["clipboard-read", "clipboard-write"],
            origin=self.substack_url,
        )
        self.page.evaluate(
            "title => navigator.clipboard.writeText(title)",
            title,
        )
        title_field.click()
        title_field.press("Meta+A")
        title_field.press("Meta+V")
        self.page.wait_for_timeout(300)

        inserted_title = title_field.evaluate(
            "field => field.value ?? field.innerText ?? field.textContent"
        )
        if inserted_title.strip() != title.strip():
            raise RuntimeError("Le collage du titre Substack a échoué.")

    def open_draft(self, post):
        generated, html = self.prepare(post)
        self.ensure_authenticated()
        self.page.goto(self.editor_url, wait_until="domcontentloaded")
        self.page.wait_for_selector("#post-title", timeout=30000)
        self.page.wait_for_selector('div[data-testid="editor"]', timeout=30000)
        self.paste_title(generated["title"])
        self.paste_html(html)
        input("Le brouillon est prêt. Appuie sur Entrée pour fermer Chrome… ")


def selected_post(database, args):
    if args.get("id") and int(args["id"]) > 0:
        return database.get_post_by_id(int(args["id"]))
    if args.get("path"):
        return database.get_post_by_path(args["path"])
    return database.get_last_published_post()


def publication_url(config, post):
    tags = post["tags"] or ""
    if '"us"' in tags:
        return config["substack_us"]
    if '"velo"' in tags:
        return config["substack_727"]
    return config["substack_fr"]


def main():
    config = tools.site_yml("tcrouzet")
    template = next(
        item
        for item in config["templates"]
        if item["name"] == "tcrouzet"
    )
    database = db.Db(config)
    post = selected_post(database, tools.get_args_dict())
    if not post:
        raise SystemExit("Aucun billet à envoyer vers Substack.")

    print(post["path_md"])
    editor = SubstackEditor(
        config,
        database,
        template,
        publication_url(config, post),
    )
    try:
        editor.open_draft(post)
    finally:
        editor.close()


if __name__ == "__main__":
    main()
