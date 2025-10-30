
//rendre visible les hash
window.addEventListener('load', function() {
    if (window.location.hash) {
      const offset = -3 * parseFloat(getComputedStyle(document.documentElement).fontSize);
      window.scrollBy(0, offset);
    }
});

//Infinite scroll
var more="";
var oktoload=true;
document.addEventListener("DOMContentLoaded", function() {

    more = document.getElementById("loadMore");
    if(more){
        window.addEventListener("scroll", scrollFire);
        //alert("scroll");
    }

});

function scrollFire(){
    window.removeEventListener("scroll",scrollFire);

    //totalPageHeight
    var totalPageHeight = document.body.offsetHeight;

    //Position du scroll
    var currentScrollPosition = document.documentElement.scrollTop;
    var windowHeight = window.innerHeight;    
    var scrollPoint = currentScrollPosition + windowHeight;

    //console.log(scrollPoint);

    if(scrollPoint >= totalPageHeight-500 && oktoload) {

        oktoload=false;
        loadMoreContent();

    }
    window.addEventListener("scroll", scrollFire);
}

function loadMoreContent() {
    const more = document.getElementById("loadMore");
    if (!more) return;

    var url = more.getAttribute('next-url');
    console.log("LoadMore " + url);
    if (url !== ""){
        console.log("URL non vide");
        if (!url.includes('.html'))
            url += "content.html";
        console.log(url);
        more.parentElement.removeChild(more);
        fetchContent(url);
    }else{
        oktoload = false
    }
}


// Charge nouvelle page
function fetchContent(url) {
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.onreadystatechange = function () {
        if (xmlhttp.readyState == XMLHttpRequest.DONE) {
            if (xmlhttp.status == 200) {
                var infiniteContainer = document.querySelector('main');
                if (infiniteContainer) {
                    infiniteContainer.insertAdjacentHTML('beforeend', xmlhttp.responseText);
                    oktoload = true;
                }
            }
        }
    };
    xmlhttp.open("GET", url, true);
    xmlhttp.send();
}

function doAPIcall(type, url, flag, callback) {
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.onreadystatechange = function () {
      if (xmlhttp.readyState == XMLHttpRequest.DONE && xmlhttp.status == 200) {
        var data = xmlhttp.responseText;
        if (callback) callback(data);
      }else{
        if(flag==1){
            more.style.display = "none";
            oktoload=false;
        }
      }
    };
    xmlhttp.open(type, url, true);
    xmlhttp.send();
}

function copyText(customTitle, customUrl) {
    // Utiliser les paramètres s'ils sont fournis, sinon utiliser les valeurs par défaut
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
        // Fallback : copier le lien dans le presse-papier
        navigator.clipboard.writeText(url)
        alert('Adresse de la page copiée dans le presse-papier…');
    }
}

// Fonction pour afficher les commentaires

let commentScriptLoaded = false;

function showComments(commentId) {
    // Récupérer directement la div des commentaires par son ID
    const commentsDiv = document.getElementById(commentId);
    if (!commentsDiv) {
        console.error('Impossible de trouver la div des commentaires avec ID:', commentId);
        return;
    }

    // Si la div est déjà visible, simplement faire défiler jusqu'à elle
    if (!commentsDiv.hidden) {
        commentsDiv.scrollIntoView({ behavior: 'smooth' });
        return;
    }

    // Afficher la div des commentaires
    commentsDiv.hidden = false;
    commentsDiv.scrollIntoView({ behavior: 'smooth' });

    // Si le contenu est vide, charger les commentaires
    if (commentsDiv.innerHTML.trim() === '') {
        // Charger le formulaire de commentaires via doAPIcall
        doAPIcall(
            "GET", 
            "/ajax-comment.html?10", 
            false,
            function (htmlData) {
                if (htmlData) {
                    // Insérer le HTML
                    commentsDiv.innerHTML = htmlData;
                    
                    // Si le script est déjà chargé, initialiser directement
                    if (commentScriptLoaded && typeof initCommentSystem === 'function') {
                        initCommentSystem(commentId);
                    } else {
                        // Sinon, charger le script
                        loadCommentScript(commentId);
                    }
                }
            }
        );
    }
}

// Fonction pour charger le script des commentaires une seule fois
function loadCommentScript(commentId) {
    console.log('Chargement du script de commentaires pour ID:', commentId);
    
    // Si le script est déjà en cours de chargement, ne pas le recharger
    if (document.getElementById('comment-script')) {
        return;
    }

    // Créer un nouvel élément script
    const script = document.createElement('script');
    script.id = 'comment-script';
    script.src = '/ajax-comment.js?t=' + new Date().getTime();
    
    // Configurer l'événement onload
    script.onload = function() {
        commentScriptLoaded = true;
        
        // Initialiser la zone de commentaires actuelle
        if (typeof initCommentSystem === 'function') {
            initCommentSystem(commentId);
        }
    };
    
    // Ajouter le script au document
    document.body.appendChild(script);
}
  