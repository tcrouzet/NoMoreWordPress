console.log('Script de commentaires chargé');

function initCommentSystem(commentId) {
    console.log('Initialisation du système de commentaires pour ID:', commentId);
    
    // Récupérer la div des commentaires
    const commentsDiv = document.getElementById(commentId);
    if (!commentsDiv) {
        console.error('Impossible de trouver la div des commentaires avec ID:', commentId);
        return;
    }
    
    // Vérifier si ce commentaire est déjà initialisé
    if (commentsDiv.getAttribute('data-initialized') === 'true') {
        console.log('Commentaire déjà initialisé:', commentId);
        return;
    }
    
    // Récupérer les données du post depuis les attributs data-
    const postUrl = commentsDiv.getAttribute('data-post-url');
    const postTitle = commentsDiv.getAttribute('data-post-title');
    const postDate = commentsDiv.getAttribute('data-post-date');
    
    // Vérifier si les données nécessaires sont disponibles
    if (!postUrl || !postTitle || !postDate) {
        console.error('Données du post manquantes');
        return;
    }
    
    // Calculer l'âge du post
    const postDateObj = new Date(postDate);
    const currentDate = new Date();
    const diffTime = Math.abs(currentDate - postDateObj);
    const postAge = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    console.log('Age du post en jours:', postAge);
    
    // Convertir l'URL du post au format attendu pour les commentaires GitHub
    const githubPostUrl = postUrl.replace(/(\d{4})\/0?(\d|1[0-2])\/\d{2}\/(.+?)\/?$/, '$1/$2/$3.md');
    console.log('URL du post pour GitHub:', githubPostUrl);
    
    // Configurer les champs cachés avec les valeurs récupérées
    const postUrlField = commentsDiv.querySelector('.postUrlField');
    const postTitleField = commentsDiv.querySelector('.postTitleField');
    const githubPostUrlField = commentsDiv.querySelector('.githubPostUrlField');
    
    if (postUrlField) postUrlField.value = postUrl;
    if (postTitleField) postTitleField.value = postTitle;
    if (githubPostUrlField) githubPostUrlField.value = githubPostUrl;
    
    // Configurer la section de type de message en fonction de l'âge du post
    const messageTypeSection = commentsDiv.querySelector('.messageTypeSection');
    if (messageTypeSection) {
        if (postAge <= 30) {
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
    
    // Configurer le gestionnaire d'événements pour le formulaire
    const form = commentsDiv.querySelector('.commentForm');
    if (form) {
        form.onsubmit = function(event) {
            event.preventDefault();
            submitComment(this, commentsDiv);
            return false;
        };
    }
    
    // Charger les commentaires existants
    const existingComments = commentsDiv.querySelector('.existing-comments');
    if (existingComments) {
        loadComments(githubPostUrl)
            .then(comments => {
                existingComments.innerHTML = comments;
            })
            .catch(error => {
                // console.error('Erreur lors du chargement des commentaires:', error);
                existingComments.innerHTML = '<div class="error">Impossible de charger les commentaires existants</div>';
            });
    }
    
    // Marquer comme initialisé
    commentsDiv.setAttribute('data-initialized', 'true');
}

// Fonction pour charger les commentaires depuis GitHub
async function loadComments(githubPostUrl) {
  console.log('Chargement des commentaires pour:', githubPostUrl);
  try {
    const response = await fetch(`https://api.github.com/repos/tcrouzet/md/contents/comments/${githubPostUrl}?ref=main`, {
      headers: { 'Accept': 'application/vnd.github.v3+json' }
    });

    // 404 = aucun commentaire pour l'instant (cas nominal)
    if (response.status === 404) {
        console.error('Aucun commentaire trouvé (404)');
        return "<p>Aucun commentaire pour l'instant. Soyez le premier à commenter!</p>";
    }

    // Autres erreurs: message user-friendly, pas d'exception bloquante
    if (!response.ok) {
        console.error('Impossible charger');
        return "<p>Impossible de charger les commentaires pour le moment.</p>";
    }

    // 200 OK: décoder le fichier et formater
    const file = await response.json();
    const rawContent = new TextDecoder('utf-8').decode(
      Uint8Array.from(atob(file.content || ""), c => c.charCodeAt(0))
    );
    return formatComments(rawContent);

  } catch (error) {
    // Ne pas logguer d'erreur pour un 404 (déjà géré ci-dessus)
    const msg = String(error || "");
    if (msg.includes("404")) {
      return "<p>Aucun commentaire pour l'instant. Soyez le premier à commenter!</p>";
    }
    console.error('Erreur dans loadComments:', error);
    return "<p>Impossible de charger les commentaires pour le moment.</p>";
  }
}


// Fonction pour convertir les liens markdown en HTML
function convertLinks(text) {
    return text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
}

// Fonction pour formater les commentaires
function formatComments(rawContent) {
    // Supprimer le lien initial vers l'article
    let content = rawContent.replace(/\[.*?\]\(.*?\)\s*---\s*/, '');
    
    // Séparer les commentaires
    const comments = content.split('---').map(comment => comment.trim()).filter(comment => comment);
    
    if (comments.length === 0) {
        return "<p>Aucun commentaire pour l'instant. Soyez le premier à commenter!</p>";
    }
    
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
    }).filter(comment => comment);

    return formattedComments.join('');
}


function submitComment(form) {
    const formData = new FormData(form);
    const messageDiv = form.querySelector('.message');
    const actionUrl = "https://formspree.io/f/mgebvkwn"; // Pour l'email
    const githubUrl = "https://blog-comment.tc8790.workers.dev/"; // URL de votre Worker Cloudflare
    
    // Afficher un message de chargement
    messageDiv.innerHTML = "<div style='color: blue;'>Envoi en cours...</div>";

    // Function to handle the response
    const handleResponse = async (response, serviceName) => {
        const data = await response.json();
        console.log(`Réponse de ${serviceName}:`, data);

        if (response.ok) {
            return data;
        } else {
            throw new Error(data.error || data.message || `Erreur lors de l'envoi à ${serviceName}.`);
        }
    };
  
    fetch(actionUrl, {
      method: "POST",
      body: formData,
      headers: {
        'Accept': 'application/json'
      }
    })
    .then(response => handleResponse(response, 'Formspree'))
    .then(() => {
        // Check if the message type is public before sending to GitHub
        if (formData.get('messageType') === 'public') {
            // Préparer les données pour le Worker
            const commentData = {
                postUrl: formData.get('postUrl'),
                postTitle: formData.get('postTitle'),
                nom: formData.get('nom'),
                email: formData.get('email'),
                message: formData.get('message')
            };
            console.log('Données envoyées :', commentData);


            return fetch(githubUrl, {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(commentData)
            })
            .then(response => handleResponse(response, 'GitHub'));
        }
    })
    .then((data) => {
        form.reset(); // Clear the form fields
        if (formData.get('messageType') === 'public') {
            messageDiv.innerHTML = "<div style='color: green;'>Le message sera vite publié.</div>";
            
            // Recharger les commentaires après soumission réussie
            setTimeout(() => {
                const githubPostUrl = form.querySelector('.githubPostUrlField').value;
                loadComments(githubPostUrl)
                    .then(comments => {
                        const commentsDiv = form.closest('[id^="com"]');
                        const existingComments = commentsDiv.querySelector('.existing-comments');
                        if (existingComments) {
                            existingComments.innerHTML = comments;
                        }
                    });
            }, 5000); // Attendre 5 secondes pour que le commentaire soit traité
        } else {
            messageDiv.innerHTML = "<div style='color: green;'>Message privé envoyé.</div>";
        }
    })
    .catch(error => {
      messageDiv.innerHTML = "<div style='color: red;'>Erreur : " + error.message + "</div>";
    });
}

// Fonction pour soumettre le commentaire
function submitCommentOlds(form) {
    const formData = new FormData(form);
    const messageDiv = form.querySelector('.message');
    const actionUrl = "https://formspree.io/f/mgebvkwn";
    const githubUrl = "https://geo.zefal.com/tools/_github_comments.php";

    // Afficher un message de chargement
    messageDiv.innerHTML = "<div style='color: blue;'>Envoi en cours...</div>";

    // Function to handle the response
    const handleResponse = async (response, serviceName) => {
        const data = await response.json();
        console.log(`Réponse de ${serviceName}:`, data);

        if (response.ok) {
            return data;
        } else {
            throw new Error(data.message || `Erreur lors de l'envoi à ${serviceName}.`);
        }
    };
  
    fetch(actionUrl, {
      method: "POST",
      body: formData,
      headers: {
        'Accept': 'application/json'
      }
    })
    .then(response => handleResponse(response, 'Formspree'))
    .then(() => {
        // Check if the message type is public before sending to GitHub
        if (formData.get('messageType') === 'public') {
            return fetch(githubUrl, {
                method: "POST",
                body: formData,
                headers: {
                    'Accept': 'application/json'
                }
            })
            .then(response => handleResponse(response, 'GitHub'));
        }
    })
    .then(() => {
        form.reset(); // Clear the form fields
        if (formData.get('messageType') === 'public') {
            messageDiv.innerHTML = "<div style='color: green;'>Le message sera vite publié.</div>";
            
            // Recharger les commentaires après soumission réussie (optionnel)
            setTimeout(() => {
                const githubPostUrl = document.getElementById('githubPostUrlField').value;
                loadComments(githubPostUrl)
                    .then(comments => {
                        document.getElementById('existingComments').innerHTML = comments;
                    });
            }, 5000); // Attendre 5 secondes pour que le commentaire soit traité
        } else {
            messageDiv.innerHTML = "<div style='color: green;'>Message privé envoyé.</div>";
        }
    })
    .catch(error => {
      messageDiv.innerHTML = "<div style='color: red;'>Erreur : " + error.message + "</div>";
    });
}
