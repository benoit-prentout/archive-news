/* Main JS for Archive News */

const TRANSLATIONS = {
    "en": {
        "page_title": "Newsletter Archive",
        "search_placeholder": "Search by title, sender...",
        "switch_lang": "FR",
        "stat_newsletters": "Newsletters",
        "footer_rights": "All rights reserved.",
        "legal_text": "A premium archive of newsletters.",
        "meta_btn": "Metadata",
        "meta_header": "Metadata",
        "meta_section_gen": "General Info",
        "meta_label_subject": "Subject",
        "meta_label_sender": "Sender",
        "meta_label_date": "Received",
        "meta_label_archived": "Archived",
        "meta_section_tech": "Technical",
        "meta_section_links": "Links",
        "pixels_found": "Tracking Detected",
        "pixels_none": "No tracking pixels detected."
    },
    "fr": {
        "page_title": "Archives Newsletters",
        "search_placeholder": "Rechercher par titre, expéditeur...",
        "switch_lang": "EN",
        "stat_newsletters": "Newsletters",
        "no_results": "Aucun résultat trouvé.",
        "footer_rights": "Tous droits réservés.",
        "legal_text": "Une archive premium de newsletters.",
        "meta_btn": "Métadonnées",
        "meta_header": "Métadonnées",
        "meta_section_gen": "Infos Générales",
        "meta_label_subject": "Sujet",
        "meta_label_sender": "Expéditeur",
        "meta_label_date": "Reçu le",
        "meta_label_archived": "Archivé le",
        "meta_section_tech": "Technique",
        "meta_section_links": "Liens",
        "pixels_found": "Tracking Détecté",
        "pixels_none": "Aucun pixel de tracking."
    }
};

let currentLang = localStorage.getItem('lang') || 'en';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);

    // Initialize Lang
    updateLanguage(currentLang);

    // Event Listeners
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keyup', filterList);
    }
});

function applyTheme(theme) {
    document.body.setAttribute('data-theme', theme);
    updateThemeIcon(theme);

    // Update Iframe if exists
    const frame = document.getElementById('emailFrame');
    if (frame) {
        const doc = frame.contentDocument;
        if (doc) {
            // Remove old filter if any
            const styleId = 'dm-filter';
            let oldStyle = doc.getElementById(styleId);
            if (oldStyle) oldStyle.remove();

            if (theme === 'dark') {
                const style = doc.createElement('style');
                style.id = styleId;
                // Smart Inversion: Invert all, but revert images and videos to keep them natural
                // hue-rotate filters to adjust for color shifts
                style.innerHTML = `
                    html { filter: invert(1) hue-rotate(180deg); }
                    img, video, iframe, [style*="background-image"] { filter: invert(1) hue-rotate(180deg); }
                `;
                doc.head.appendChild(style);
            }
        }
    }
}

function toggleTheme() {
    const current = document.body.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    applyTheme(next);
}

function updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    const sun = btn.querySelector('.icon-sun');
    const moon = btn.querySelector('.icon-moon');
    if (theme === 'dark') {
        if (sun) sun.style.display = 'block';
        if (moon) moon.style.display = 'none';
    } else {
        if (sun) sun.style.display = 'none';
        if (moon) moon.style.display = 'block';
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
    if (!list) return;
    const items = list.getElementsByClassName('news-card');
    let visibleCount = 0;

    for (let i = 0; i < items.length; i++) {
        const title = items[i].querySelector('.card-title')?.textContent || "";
        const sender = items[i].querySelector('.sender-pill')?.textContent || "";

        if (title.toLowerCase().includes(filter) || sender.toLowerCase().includes(filter)) {
            items[i].parentElement.style.display = "";
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

/* Highlight Toggle Logic */
let highlightsActive = false;
function toggleHighlight() {
    const frame = document.getElementById('emailFrame');
    if (!frame) return;
    const doc = frame.contentDocument;

    highlightsActive = !highlightsActive;
    const btn = document.getElementById('highlight-toggle');
    if (btn) btn.classList.toggle('active', highlightsActive);

    const styleId = 'hl-style';
    if (highlightsActive) {
        const style = doc.createElement('style');
        style.id = styleId;
        style.innerHTML = `
            a { 
                position: relative;
                outline: 2px solid #ff0000 !important; 
                outline-offset: 2px;
                cursor: help !important;
            }
            a::after {
                content: attr(href);
                position: absolute;
                bottom: 100%; left: 0;
                background: #333; color: #fff;
                padding: 4px 8px;
                font-size: 10px;
                border-radius: 4px;
                white-space: nowrap;
                z-index: 9999;
                pointer-events: none;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
        `;
        doc.head.appendChild(style);
    } else {
        const s = doc.getElementById(styleId);
        if (s) s.remove();
    }
}

/* Link Highlighting from Sidebar List */
function highlightLink(idx) {
    const frame = document.getElementById('emailFrame');
    if (!frame) return;
    const doc = frame.contentDocument;

    // Clear previous
    doc.querySelectorAll('.highlight-temp').forEach(el => {
        el.classList.remove('highlight-temp');
        el.style.outline = '';
        el.style.animation = '';
    });

    // Find link by data-index
    const link = doc.querySelector(`a[data-index="${idx}"]`);
    if (link) {
        link.scrollIntoView({ behavior: 'smooth', block: 'center' });
        link.style.outline = '3px solid #ffff00';
        link.style.transition = 'outline 0.5s';
        setTimeout(() => { link.style.outline = '2px solid red'; }, 600);
    }
}
