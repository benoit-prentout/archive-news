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

    // Auto-detect Mobile Device to Simplify UI
    if (window.innerWidth < 768) {
        // Hide device toggles on actual mobile devices, as they shouldn't simulate other devices
        const toggles = document.querySelector('.device-toggles');
        if (toggles) toggles.style.display = 'none';

        // Force mobile mode display logic without the simulator frame constraints
        // We might want to ensure the frame takes full width/height naturally
        const frame = document.getElementById('deviceFrame');
        if (frame) {
            frame.style.width = '100%';
            frame.style.height = '100%';
            frame.style.border = 'none';
            frame.style.boxShadow = 'none';
        }
    }
});

/* View Mode Logic */
function setMode(mode) {
    const frameEl = document.getElementById('deviceFrame');
    if (!frameEl) return;

    // Simplified Transition: The CSS transition handles width/max-width smoothly.
    // We just ensure the frame is ready for the switch.
    frameEl.style.maxWidth = ''; // Let CSS take over
    frameEl.setAttribute('data-mode', mode);

    const doc = frameEl.querySelector('iframe')?.contentDocument;
    if (doc) {
        // Mobile Fixes
        let mobileStyle = doc.getElementById('mobile-fix');
        if (mode !== 'desktop') {
            if (!mobileStyle) {
                mobileStyle = doc.createElement('style');
                mobileStyle.id = 'mobile-fix';
                mobileStyle.innerHTML = `
                    html, body { width: 100% !important; min-width: 0 !important; margin: 0 !important; padding: 0 !important; }
                    table, img, .mj-column-per-100 { width: 100% !important; max-width: 100% !important; }
                    img { height: auto !important; }
                `;
                doc.head.appendChild(mobileStyle);
            }
            if (mode === 'mobile') {
                if (doc.body) {
                    doc.body.style.padding = '60px 15px 30px 15px'; // Increased notch safe area
                }
                // Hide Scrollbar
                let sbStyle = doc.getElementById('sb-hide');
                if (!sbStyle) {
                    sbStyle = doc.createElement('style');
                    sbStyle.id = 'sb-hide';
                    sbStyle.innerHTML = `::-webkit-scrollbar { display: none; } body { -ms-overflow-style: none; scrollbar-width: none; }`;
                    doc.head.appendChild(sbStyle);
                }
            } else {
                if (doc.body) doc.body.style.padding = '0';
            }
        } else {
            if (mobileStyle) mobileStyle.remove();
            const sb = doc.getElementById('sb-hide');
            if (sb) sb.remove();
            if (doc.body) doc.body.style.padding = '0';
        }
    }

    // Update Buttons
    document.querySelectorAll('.device-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.device-btn[onclick="setMode('${mode}')"]`);
    if (btn) btn.classList.add('active');

    // Re-apply frame basics when switcher happens to ensure consistency
    setupFrame(doc);
}

/* Helper to setup iframe defaults globally */
function setupFrame(doc) {
    if (!doc) return;

    let baseStyle = doc.getElementById('base-frame-style');
    if (!baseStyle) {
        baseStyle = doc.createElement('style');
        baseStyle.id = 'base-frame-style';
        doc.head.appendChild(baseStyle);
    }
    baseStyle.innerHTML = `
        html, body { 
            margin: 0 !important; 
            padding: 0; 
            overflow-x: hidden; 
            -webkit-font-smoothing: antialiased;
        }
        /* Universal Scrollbar Hide INSIDE Iframe */
        ::-webkit-scrollbar { display: none !important; width: 0 !important; }
        * { scrollbar-width: none !important; -ms-overflow-style: none !important; }
    `;
}

/* Copy Utilities */
function copyLink(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
        const original = btn.innerHTML;
        btn.innerHTML = `<svg class="icon" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        btn.style.color = 'var(--accent-color)';
        setTimeout(() => {
            btn.innerHTML = original;
            btn.style.color = '';
        }, 1500);
    });
}

function copySource() {
    const text = document.getElementById('sourceText').value;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector('.copy-source-btn');
        const original = btn.innerText;
        btn.innerText = "Copied!";
        setTimeout(() => btn.innerText = original, 2000);
    });
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('closed');
    const btn = document.querySelector('.btn-icon[title="Toggle Sidebar"]'); // Ensure we target correct btn if needed
    if (event && event.currentTarget) event.currentTarget.classList.toggle('active');
}

function openSourceModal() {
    document.getElementById('sourceText').value = content;
    document.getElementById('sourceModal').style.display = 'flex';
}

function closeSourceModal() {
    document.getElementById('sourceModal').style.display = 'none';
}

function applyTheme(theme) {
    document.body.setAttribute('data-theme', theme);
    updateThemeIcon(theme);

    const frame = document.getElementById('emailFrame');
    if (frame) {
        const doc = frame.contentDocument;
        if (doc) {
            setupFrame(doc);
            const styleId = 'dm-filter';
            let oldStyle = doc.getElementById(styleId);
            if (oldStyle) oldStyle.remove();

            if (theme === 'dark') {
                // FORCE FIX: Aggressive Background Inversion
                if (doc.body) {
                    const elementsToFix = doc.querySelectorAll('body, table, .es-wrapper-color, .mj-body, div, center');
                    elementsToFix.forEach(el => {
                        el.style.backgroundColor = '#ffffff';
                        el.style.color = '#000000';
                    });
                }

                const style = doc.createElement('style');
                style.id = styleId;
                style.innerHTML = `
                    html { 
                        filter: invert(1) hue-rotate(180deg) !important; 
                        background-color: #fff !important; 
                    }
                    img, video, iframe, [style*="background-image"], .no-invert { 
                        filter: invert(1) hue-rotate(180deg) !important; 
                    }
                    /* Ensure text visibility */
                    body, table, div { background-color: #fff !important; }
                `;
                doc.head.appendChild(style);
            } else if (theme === 'light') {
                // Reset manual overrides if light theme
                if (doc.body) {
                    doc.querySelectorAll('body, table, .es-wrapper-color, .mj-body, div, center').forEach(el => {
                        el.style.backgroundColor = '';
                        el.style.color = '';
                    });
                }
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

/* Sorting Logic */
function sortList() {
    const select = document.getElementById('sortSelect');
    if (!select) return;
    const criteria = select.value;
    const list = document.getElementById('newsList');
    if (!list) return;

    const items = Array.from(list.getElementsByClassName('news-card'));

    items.sort((a, b) => {
        let valA = "", valB = "";
        if (criteria.startsWith('date')) {
            valA = a.getAttribute('data-date') || "";
            valB = b.getAttribute('data-date') || "";
            return criteria.endsWith('desc') ? valB.localeCompare(valA) : valA.localeCompare(valB);
        } else if (criteria.startsWith('sender')) {
            valA = (a.getAttribute('data-sender') || "").toLowerCase();
            valB = (b.getAttribute('data-sender') || "").toLowerCase();
            return criteria.endsWith('az') ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return 0;
    });

    // Re-append items in new order
    items.forEach(item => list.appendChild(item));
}

/* Clipboard Utilities */
function copyToClipboard(text, btn) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓';
        btn.classList.add('copy-success');
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.classList.remove('copy-success');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}

function copySource() {
    const code = document.getElementById('sourceCode');
    if (!code) return;
    const btn = document.querySelector('.modal-actions .btn-copy-source');
    copyToClipboard(code.textContent, btn);
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
