let oktoload = true;

document.addEventListener("DOMContentLoaded", function() {
  window.addEventListener("scroll", scrollFire, { passive: true });
  // Check initial (utile si la page est courte)
  scrollFire();
});

function scrollFire() {
  // Si déjà en charge, ne rien faire
  if (!oktoload) return;

  const more = document.getElementById("loadMore");
  if (!more) return; // plus rien à charger

  const scrollY = window.scrollY || window.pageYOffset;
  const viewportH = window.innerHeight;

  const docHeight = Math.max(
    document.documentElement.scrollHeight,
    document.body.scrollHeight
  );

  if (scrollY + viewportH >= docHeight - 600) {
    oktoload = false;
    loadMoreContent(more);
  }
}

function loadMoreContent(moreEl) {
  if (!moreEl) return;

  let url = moreEl.getAttribute('data-next-url');
  if (!url) return;

  if (!url.includes('.html')) url += "content.html";

  // Retire le placeholder pour éviter double déclenchement
  moreEl.remove();

  fetch(url)
    .then(r => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.text();
    })
    .then(html => {
      const main = document.querySelector('main');
      if (!main) return;

      // Insère le HTML renvoyé (il DOIT contenir à la fin un nouveau #loadMore s’il reste des pages)
      main.insertAdjacentHTML('beforeend', html);

      // Autorise un nouveau chargement et relance un check au prochain frame
      requestAnimationFrame(() => {
        oktoload = true;
        scrollFire(); // si la page est encore courte, on enchaîne
      });
    })
    .catch(e => {
      console.error(e);
      // En cas d’erreur, autorise à retenter au scroll suivant
      oktoload = true;
    });
}

function share(customTitle, customUrl) {
  const title = customTitle || document.title;
  const url = customUrl || window.location.href;

  if (navigator.share) {
    navigator.share({ title, url }).catch((error) => {
      console.error('Erreur lors du partage :', error);
    });
  } else {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).catch(() => {});
    }
    alert('Adresse de la page copiée dans le presse-papier…');
  }
}