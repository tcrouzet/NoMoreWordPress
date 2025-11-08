// Scroll vers les ancres avec offset
window.addEventListener('load', function() {
    if (window.location.hash) {
        const offset = -3 * parseFloat(getComputedStyle(document.documentElement).fontSize);
        window.scrollBy(0, offset);
    }
});

// Infinite scroll
let oktoload = true;
document.addEventListener("DOMContentLoaded", function() {
    const more = document.getElementById("loadMore");
    if (more) window.addEventListener("scroll", scrollFire);
});

function scrollFire() {
    const more = document.getElementById("loadMore");
    if (!more || !oktoload) return;

    const scrollPoint = document.documentElement.scrollTop + window.innerHeight;
    
    if (scrollPoint >= document.body.offsetHeight - 500) {
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
    fetchContent(url);
}

function fetchContent(url) {
    fetch(url)
        .then(r => r.text())
        .then(html => {
            const main = document.querySelector('main');
            if (main) {
                main.insertAdjacentHTML('beforeend', html);
                oktoload = true;
                // Réinitialiser le listener si nécessaire
                window.addEventListener("scroll", scrollFire);
            }
        })
        .catch(e => console.error(e));
}

// Share bouton
function share(customTitle, customUrl) {
    const title = customTitle || document.title;
    const url = customUrl || window.location.href;
    
    if (navigator.share) {
        navigator.share({
            title: title,
            url: url
        }).then(() => {
            console.log('Partage réussi');
        }).catch((error) => {
            console.error('Erreur lors du partage :', error);
        });
    } else {
        // Fallback
        navigator.clipboard.writeText(url)
        alert('Adresse de la page copiée dans le presse-papier…');
    }
}