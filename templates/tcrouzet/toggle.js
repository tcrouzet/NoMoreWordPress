var toggle = document.getElementById('toggle');
var access = document.getElementById('access');
var accessLoaded = false;

var toggleSearch = document.getElementById('toggle-search');
var search = document.getElementById('access-search');
var searchLoaded = false;

function toggleMenu(){
    toggle.classList.toggle("close");
    access.classList.toggle("shown");

    if(accessLoaded) return;
    doAPIcall(
        "GET","/ajax-menu.html?15", false,
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
        "GET","/ajax-search.html", 2,
        function (data) {
            if(data){
                search.innerHTML=data;
            }
        }
    );
    searchLoaded=true;
};

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
var firstLoad=true;
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

    //if(scrollPoint >= totalPageHeight-500 || firstLoad) {
    if(scrollPoint >= totalPageHeight-500 && oktoload) {

        oktoload=false;
        if (!firstLoad) {
            updateNextURL();
        }
        firstLoad = false
        loadMoreContent();

    }
    window.addEventListener("scroll", scrollFire);
}

function loadMoreContent() {
    const more = document.getElementById("loadMore");
    var url = more.getAttribute('next-url');
    console.log("LoadMore " + url);
    if (url !== ""){
        console.log("URL non vide");
        if (!url.includes('.html'))
            url += "content.html";
        console.log(url);
        fetchContent(url);
    }else{
        oktoload = false
    }
}


function fetchContent(url) {
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.onreadystatechange = function () {
        if (xmlhttp.readyState == XMLHttpRequest.DONE) {
            if (xmlhttp.status == 200) {
                var infiniteContainer = document.querySelector('.infinite');
                if (infiniteContainer) {
                    infiniteContainer.insertAdjacentHTML('beforeend', xmlhttp.responseText);
                    oktoload = true;
                }else{
                    more.style.display = "none";
                }
            } else {
                more.style.display = "none";
            }
        }
    };
    xmlhttp.open("GET", url, true);
    xmlhttp.send();
}

function updateNextURL() {
    var loadMoreUrls = document.querySelectorAll('.load-more-url');
    if (loadMoreUrls.length > 0) {
        var lastUrlElement = loadMoreUrls[loadMoreUrls.length - 1]; // Prend le dernier élément de la liste
        var nextURL = lastUrlElement.getAttribute('next-url');
        //console.log("Next URL found:", nextURL);
        const more = document.getElementById("loadMore");
        more.setAttribute('next-url', nextURL);
    }
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

function copyText() {
    if (navigator.share) {
        navigator.share({
            title: document.title,
            url: window.location.href
        }).then(() => {
            console.log('Partage réussi');
        }).catch((error) => {
            console.error('Erreur lors du partage :', error);
        });
    } else {
        // Fallback : copier le lien dans le presse-papier
        navigator.clipboard.writeText(window.location.href)
            .then(() => {
                copyMessage('Adresse de l\'article copiée !<br/>À coller dans votre réseau social préféré.');
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

async function showComments(button) {
    const article = button.closest('article');
    if (article) {
        const commentsDiv = article.querySelector('.comments');
        const messageTypeSection = article.querySelector('.messageTypeSection');
        const metaUrl = article.querySelector('meta[itemprop="url"]');
        const datePublishedMeta = article.querySelector('meta[itemprop="datePublished"]');
        if (metaUrl) {
            let postUrl = metaUrl.content.split('tcrouzet.com')[1];
            postUrl = postUrl.replace(/(\d{4})\/0?(\d|1[0-2])\/\d{2}\/(.+?)\/?$/, '$1/$2/$3.md');
            // console.log('postUrl:', postUrl);

            if (commentsDiv && postUrl) {
                commentsDiv.style.display = 'block';
                commentsDiv.scrollIntoView({ behavior: 'smooth' });

                if (datePublishedMeta && messageTypeSection) {
                    const postDate = new Date(datePublishedMeta.content);
                    const currentDate = new Date();
                    const diffTime = Math.abs(currentDate - postDate);
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                    console.log('diffDays:', diffDays);
        
                    // Logic for messageTypeSection based on post age
                    if (diffDays <= 30) {
                        messageTypeSection.innerHTML = `
                            <label>
                              <input type="radio" name="messageType" value="public" checked>
                              Public
                            </label>
                            <label>
                              <input type="radio" name="messageType" value="private">
                              Privé
                            </label><br/>
                        `;
                    } else {
                        messageTypeSection.innerHTML = `
                            <input type="hidden" name="messageType" value="private">
                            <div>Fil de commentaire fermé. Vous pouvez m'envoyer un message privé.</div>
                        `;
                    }
                }

                try {
                    const comments = await loadComments(postUrl);
                    commentsDiv.innerHTML += comments;
                } catch (error) {
                }
            }else{
                console.error('Impossible de trouver comments');
            }
        }else{
            console.error('Impossible de trouver metaUrl');
        }
    }else{
        console.error('Impossible de trouver article');
    }
}

async function loadComments(postUrl) {
    console.log(postUrl);
    const response = await fetch(`https://api.github.com/repos/tcrouzet/BlogComments/contents/${postUrl}?ref=main`);
    const file = await response.json();
    const rawContent = new TextDecoder('utf-8').decode(Uint8Array.from(atob(file.content), c => c.charCodeAt(0)));
    return formatComments(rawContent);
}

function convertLinks(text) {
    return text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
}

function formatComments(rawContent) {
    // Supprimer le lien initial vers l'article
    let content = rawContent.replace(/\[.*?\]\(.*?\)\s*---\s*/, '');
    
    // Séparer les commentaires
    const comments = content.split('---').map(comment => comment.trim());
    
    const formattedComments = comments.map(comment => {
        const matches = comment.match(/^(.*?)\s*@\s*(.*?)(\d{2}:\d{2}):\d{2}\s+(.*)/s);
        if (!matches) return '';
        
        const [, author, date, time, text] = matches;
        
        // Formater la date
        const formattedDate = `${new Date(date).toLocaleDateString('fr-FR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        })} @ ${time}`;
        
        // Retourner le commentaire formaté en HTML
        return `
            <div class="comment">
                <div class="comment-header">
                    <span class="comment-author">${author}</span>
                    <span class="comment-date">${formattedDate}</span>
                </div>
                <div class="comment-content">
                    ${convertLinks(text.replace(/http:\/\/t\.co\/\w+/g, ''))}
                </div>
            </div>
        `;
    });

    return  formattedComments.join('');
}

function submitComment(form) {
    const formData = new FormData(form);
    const messageDiv = form.querySelector('.message');
    const actionUrl = "https://formspree.io/f/mgebvkwn";
  
    fetch(actionUrl, {
      method: "POST",
      body: formData,
      headers: {
        'Accept': 'application/json'
      }
    })
    .then(response => {
      if (response.ok) {
        form.reset(); // Clear the form fields
        messageDiv.innerHTML = "<div style='color: green;'>Message envoyé. Je vous répondrai au plus vite.</div>";
      } else {
        return response.json().then(data => {
          throw new Error(data.error || "Erreur lors de l'envoi.");
        });
      }
    })
    .catch(error => {
      messageDiv.innerHTML = "<div style='color: red;'>Erreur : " + error.message + "</div>";
    });
  }