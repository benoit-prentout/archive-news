// docs/viewer.js
document.addEventListener('DOMContentLoaded', () => {
    const frame = document.getElementById('emailFrame');
    const btnMobile = document.getElementById('btn-mobile');
    const btnDark = document.getElementById('btn-dark');
    const btnLinks = document.getElementById('btn-links');
    const sidebar = document.getElementById('sidebar');

    // Le contenu HTML de l'email est passé via une variable globale
    if (window.emailContent) {
        frame.srcdoc = window.emailContent;
    }

    frame.addEventListener('load', () => {
        const style = frame.contentDocument.createElement('style');
        style.textContent = `
            :root {
                color-scheme: light dark;
            }
            body {
                margin: 0 auto !important;
                padding: 12px !important;
                max-width: 800px;
                box-sizing: border-box;
                background-color: white;
            }
            img {
                max-width: 100% !important;
                height: auto !important;
                display: block;
            }
            table {
                max-width: 100% !important;
                border-spacing: 0;
            }
        `;
        frame.contentDocument.head.appendChild(style);
    });

    btnMobile.addEventListener('click', () => {
        document.body.classList.toggle('mobile-mode');
        btnMobile.classList.toggle('active');
    });

    btnDark.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        btnDark.classList.toggle('active');
    });

    btnLinks.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        btnLinks.classList.toggle('active');
    });
});
