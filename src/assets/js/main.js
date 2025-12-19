/* Main JS for Archive News */

const TRANSLATIONS = {
    "en": {
        "page_title": "Newsletter Archive",
        "search_placeholder": "Search by title, sender...",
        "switch_lang": "FR",
        "stat_newsletters": "Newsletters",
        "stat_reading_time": "Reading Time",
        "no_results": "No results found.",
        "footer_rights": "All rights reserved.",
        "legal_summary": "Legal Notice",
        "legal_publisher": "Publisher",
        "legal_hosting": "Hosting",
        "legal_text": "This site is a personal archive."
    },
    "fr": {
        "page_title": "Archives Newsletters",
        "search_placeholder": "Rechercher par titre, expéditeur...",
        "switch_lang": "EN",
        "stat_newsletters": "Newsletters",
        "stat_reading_time": "Temps de lecture",
        "no_results": "Aucun résultat trouvé.",
        "footer_rights": "Tous droits réservés.",
        "legal_summary": "Mentions Légales",
        "legal_publisher": "Éditeur",
        "legal_hosting": "Hébergement",
        "legal_text": "Ce site est une archive personnelle."
    }
};

let currentLang = localStorage.getItem('lang') || 'en';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    // Initialize Lang
    updateLanguage(currentLang);

    // Event Listeners
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keyup', filterList);
    }
});

function toggleTheme() {
    const current = document.body.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeIcon(next);
}

function updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    // Simple icon switch logic (could be improved with SVG replacements)
    // Here we assume the SVG inside the button changes or we toggle classes
    const sun = btn.querySelector('.icon-sun');
    const moon = btn.querySelector('.icon-moon');
    if (theme === 'dark') {
        if(sun) sun.style.display = 'block';
        if(moon) moon.style.display = 'none';
    } else {
        if(sun) sun.style.display = 'none';
        if(moon) moon.style.display = 'block';
    }
}

function toggleLanguage() {
    currentLang = currentLang === 'en' ? 'fr' : 'en';
    localStorage.setItem('lang', currentLang);
    updateLanguage(currentLang);
}

function updateLanguage(lang) {
    const t = TRANSLATIONS[lang];
    if (!t) return;

    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key]) el.textContent = t[key];
    });

    const searchInput = document.getElementById('searchInput');
    if (searchInput && t['search_placeholder']) {
        searchInput.placeholder = t['search_placeholder'];
    }
    
    // Update Lang Button Text if needed
    const langBtn = document.getElementById('lang-toggle-text');
    if (langBtn) langBtn.textContent = t['switch_lang'];
}

/* Filtering Logic */
function filterList() {
    const input = document.getElementById('searchInput');
    const filter = input.value.toLowerCase();
    const list = document.getElementById('newsList');
    const items = list.getElementsByClassName('news-card'); // updated class name
    let visibleCount = 0;

    for (let i = 0; i < items.length; i++) {
        const title = items[i].querySelector('.card-title')?.textContent || "";
        const sender = items[i].querySelector('.sender-pill')?.textContent || "";
        
        if (title.toLowerCase().includes(filter) || sender.toLowerCase().includes(filter)) {
            items[i].parentElement.style.display = ""; // item is wrapper usually li or div
            visibleCount++;
        } else {
            items[i].parentElement.style.display = "none";
        }
    }

    const noResults = document.getElementById('noResults');
    if (noResults) {
        noResults.style.display = visibleCount === 0 ? "block" : "none";
    }
}
