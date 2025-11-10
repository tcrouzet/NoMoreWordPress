let oktoload = true;

document.addEventListener("DOMContentLoaded", function() {
  if (document.getElementById("loadMore")) {
    window.addEventListener("scroll", scrollFire, { passive: true });
    scrollFire(); // si déjà proche du bas
  }
});

function scrollFire() {
  if (!oktoload) return;
  const more = document.getElementById("loadMore");
  if (!more) return;

  const scrollY = window.scrollY || window.pageYOffset;
  const viewportH = window.innerHeight;
  const docHeight = Math.max(
    document.documentElement.scrollHeight,
    document.body.scrollHeight
  );

  if (scrollY + viewportH >= docHeight - 500) {
    oktoload = false;
    loadMoreContent();
  }
}

function loadMoreContent() {
  const more = document.getElementById("loadMore");
  if (!more) return;

  let url = more.getAttribute('next-url');
  if (!url) return;
  if (!url.includes('.html')) url += "content.html";

  more.remove();

  fetch(url)
    .then(r => r.text())
    .then(html => {
      const main = document.querySelector('main');
      if (!main) return;
      main.insertAdjacentHTML('beforeend', html);
      oktoload = true;
      // Si on est encore proche du bas (grand écran / contenu court), relance un check
      scrollFire();
    })
    .catch(e => console.error(e));
}

// Share bouton
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