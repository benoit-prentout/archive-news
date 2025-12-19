/* Main JS for Archive News */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);

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
            const styleId = 'dm-filter';
            let oldStyle = doc.getElementById(styleId);
            if (oldStyle) oldStyle.remove();

            if (theme === 'dark') {
                const style = doc.createElement('style');
                style.id = styleId;
                // Smart Inversion
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
            items[i].style.display = "";
            visibleCount++;
        } else {
            items[i].style.display = "none";
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
        // Updated style for uniformity: normal weight, small caps or uniform lower, uniform padding
        style.innerHTML = `
            a { 
                position: relative;
                outline: 2px solid #ff0000 !important; 
                cursor: help !important;
            }
            a::after {
                content: attr(href);
                position: absolute;
                bottom: 100%; left: 0;
                background: #222; color: #fff;
                padding: 4px 6px;
                font-size: 10px;
                font-weight: 400; /* Normal weight */
                font-family: monospace;
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

    doc.querySelectorAll('.highlight-temp').forEach(el => {
        el.classList.remove('highlight-temp');
        el.style.outline = '';
    });

    const link = doc.querySelector(`a[data-index="${idx}"]`);
    if (link) {
        link.scrollIntoView({ behavior: 'smooth', block: 'center' });
        link.style.outline = '3px solid #ffff00';
        link.style.transition = 'outline 0.5s';
        setTimeout(() => { link.style.outline = '2px solid red'; }, 600);
    }
}

/* Copy Links Feature */
function copyLinks(links) {
    if (!links || links.length === 0) return;
    const text = links.map(l => l.original_url).join('\n');
    navigator.clipboard.writeText(text).then(() => {
        alert('Links copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy: ', err);
        // Fallback or alert
        alert('Failed to copy links.');
    });
}
