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

//share function
function copyText() {
    navigator.clipboard.writeText(window.location.href)
      .then(() => {
        copyMessage('Adresse de l\'article copiée !<br/>À coller dans votre réseau social préféré.');
      })
      .catch(err => {
        console.error('Erreur lors de la copie :', err);
      });
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
