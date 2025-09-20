var toggle = document.getElementById('toggle');
var access = document.getElementById('access');
var accessLoaded = false;

var toggleSearch = document.getElementById('toggle-search');
var search = document.getElementById('access-search');
var searchLoaded = false;

var newsletter = document.getElementById('newsletter');
var newsletterLoaded = false;


function toggleMenu(){
    toggle.classList.toggle("close");
    access.classList.toggle("shown");

    if(accessLoaded) return;
    doAPIcall(
        "GET","/ajax-menu.html?19", false,
        function (data) {
            if(data){
                access.innerHTML=data;
            }
        }
    );
    accessLoaded=true;

};

function searchMenu(){
    toggleSearch.classList.toggle("close");
    search.classList.toggle("shown");

    if(searchLoaded) return;
    doAPIcall(
        "GET","/ajax-search.html?3", 2,
        function (data) {
            if(data){
                search.innerHTML=data;
            }
        }
    );
    searchLoaded=true;
};

function toggleNewsletter() {
    // Si la newsletter est déjà visible, la cacher
    if (newsletter.style.display === 'block') {
        newsletter.style.display = 'none';
        document.body.style.overflow = 'auto'; // Réactiver le défilement
        return;
    }
    
    // Si la newsletter n'est pas encore chargée
    if (!newsletterLoaded) {
        doAPIcall(
            "GET", "/ajax-newsletter.html?15", false,
            function (data) {
                if (data) {
                    newsletter.innerHTML = data;
                    newsletter.style.display = 'block';
                    newsletterLoaded = true;
                }
            }
        );
    } else {
        // Si déjà chargée, simplement l'afficher
        newsletter.style.display = 'block';
        document.body.style.overflow = 'hidden'; // Empêcher le défilement
    }
}

toggle.addEventListener("click", toggleMenu, false);
toggleSearch.addEventListener("click", searchMenu, false);

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
                var infiniteContainer = document.querySelector('.infinite');
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
        if(flag==2){
            //Loag google search
            var cx = "d5dc254fba5984394";
            var gcse = document.createElement('script');
            gcse.type = 'text/javascript';
            gcse.async = true;
            gcse.src = 'https://cse.google.com/cse.js?cx=' + cx;
            var s = document.getElementsByTagName('script')[0];
            s.parentNode.insertBefore(gcse, s);
            
            // render the search bar
            var searchBar = document.querySelector('.gcse-search');
            if(searchBar){
                google.search.cse.element.render({gname:'search', div: searchBar, tag:'searchresults-only'});
            }
        }
      }
    };
    xmlhttp.open(type, url, true);
    xmlhttp.send();
}

// function copyText() {
//     if (navigator.share) {
//         navigator.share({
//             title: document.title,
//             url: window.location.href
//         }).then(() => {
//             console.log('Partage réussi');
//         }).catch((error) => {
//             console.error('Erreur lors du partage :', error);
//         });
//     } else {
//         // Fallback : copier le lien dans le presse-papier
//         navigator.clipboard.writeText(window.location.href)
//             .then(() => {
//                 copyMessage('Adresse de l\'article copiée !<br/>À coller dans votre réseau social préféré.');
//             })
//             .catch((error) => {
//                 console.error('Erreur lors de la copie du lien :', error);
//             });
//     }
// }

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
            .then(() => {
                copyMessage('Adresse copiée !<br/>À coller dans votre réseau social préféré.');
            })
            .catch((error) => {
                console.error('Erreur lors de la copie du lien :', error);
            });
    }
}

function copyMessage(msg) {
    var messageElement = document.getElementById('copyMessage');
    messageElement.innerHTML = msg;

    if (msg.toLowerCase().includes("erreur")) {
        messageElement.style.backgroundColor = "red"
    }

    messageElement.style.visibility = 'visible';
    setTimeout(() => {
        messageElement.style.visibility = 'hidden';
    }, 5000); 
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
    if (commentsDiv.style.display === 'block') {
        commentsDiv.scrollIntoView({ behavior: 'smooth' });
        return;
    }

    // Afficher la div des commentaires
    commentsDiv.style.display = 'block';
    commentsDiv.scrollIntoView({ behavior: 'smooth' });

    // Si le contenu est vide, charger les commentaires
    if (commentsDiv.innerHTML.trim() === '') {
        // Charger le formulaire de commentaires via doAPIcall
        doAPIcall(
            "GET", 
            "/ajax-comment.html?9", 
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


// Fonction pour fermer le popup
function closePopup() {
  const popup = document.getElementById('popup');
  popup.style.display = 'none';
  
  // Optionnel : supprimer les écouteurs d'événements pour éviter les doublons
  popup.replaceWith(popup.cloneNode(true));
}

function canShowPopup() {

    // Vérifier si l'utilisateur est déjà sur la page du livre
    const currentPath = window.location.pathname;
    if (currentPath === '/books/epicenes/' || currentPath.startsWith('/books/epicenes')) {
        return false;
    }

    // Pour le test
    // return true; 

    const now = new Date().getTime();
    const lastShown = localStorage.getItem('popupLastShown');
    const fifteenDays = 7 * 24 * 60 * 60 * 1000; // en millisecondes
    
    // Peut afficher si jamais affiché ou affiché il y a plus de 15 jours
    return !lastShown || (now - parseInt(lastShown) > fifteenDays);
}

  