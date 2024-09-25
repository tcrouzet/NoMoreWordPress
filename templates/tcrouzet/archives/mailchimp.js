document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('mailchimp')) {
        mailchimpSubscription();
    }
});


function mailchimpSubscription() {
    document.getElementById('mailchimp').addEventListener('submit', function(e) {
        e.preventDefault();
        
        var formData = new FormData();
        formData.append('mc-email', document.getElementById('mc-email').value );
        formData.append('mc-blog', document.getElementById('mc-blog').checked ? '1' : '0');
        formData.append('mc-carnet', document.getElementById('mc-carnet').checked ? '1' : '0');
        formData.append('mc-ecriture', document.getElementById('mc-ecriture').checked ? '1' : '0');
        formData.append('mc-bike', document.getElementById('mc-bike').checked ? '1' : '0');
        formData.append('b_4346e7140965015f0594fffcd_f8567ebe86', document.querySelector('input[name="b_4346e7140965015f0594fffcd_f8567ebe86"]').value );
    
        var url = "https://lab.tcrouzet.com/mailchimp/subscribe.php";

        fetch(url, {
            method: 'POST',
            body: new URLSearchParams([...formData]),
        }).then(response => {
            if (!response.ok) throw new Error('Réponse réseau non OK');
            return response.text();
        }).then(data => {
            console.log("Data:", data);
            mailchimp_message(`${data}`);
        }).catch(error => {
            console.error('Erreur:', error);
            mailchimp_message("Erreur: "+error);
        });
    
    });
}

function mailchimp_message(msg){
    var messageElement = document.getElementById('mc-message');
    messageElement.innerHTML = msg;

    if (msg.toLowerCase().includes("erreur")) {
        messageElement.style.backgroundColor = "red"
    } else{
        messageElement.style.backgroundColor = "#4CAF50"
    }
    messageElement.style.display = "block";
    messageElement.style.visibility = "visible";

}