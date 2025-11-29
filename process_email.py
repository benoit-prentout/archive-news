import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr
from bs4 import BeautifulSoup
import os
import re
import mimetypes
import requests
from urllib.parse import urljoin
import datetime
import hashlib
import shutil
import json
import html
import time

# --- CONFIGURATION ---
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]
TARGET_LABEL = "Github/archive-newsletters"
OUTPUT_FOLDER = "docs"
BATCH_SIZE = 9999

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- LISTE DES MOTIFS DE TRACKING ---
TRACKING_PATTERNS = [
    "api.getinside.media",
    "google-analytics.com",
    "doubleclick.net",
    "facebook.com/tr",
    "criteo.com",
    "matomo",
    "pixel.gif",
    "analytics",
    "tracking",
    "open.aspx",
    "shim.gif",
    "ad.doubleclick"
]

# --- ICONS SVG ---
ICON_MOON = '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>'
ICON_SUN = '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>'
ICON_MOBILE = '<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>'
ICON_LINK = '<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>'
ICON_INFO = '<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
ICON_LANG = '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>'
ICON_TARGET = '<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><line x1="22" y1="12" x2="18" y2="12"></line><line x1="6" y1="12" x2="2" y2="12"></line><line x1="12" y1="6" x2="12" y2="2"></line><line x1="12" y1="22" x2="12" y2="18"></line></svg>'
ICON_COPY = '<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'
ICON_EYE = '<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>'
ICON_CHECK = '<svg viewBox="0 0 24 24" width="14" height="14" stroke="green" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>'
ICON_WARN = '<svg viewBox="0 0 24 24" width="14" height="14" stroke="orange" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>'
ICON_BUG = '<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
ICON_CHAIN = '<svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>'
# Nouvelles icônes pour le viewer de liens
ICON_ORIGIN = '<svg viewBox="0 0 24 24" width="12" height="12" stroke="#666" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 16 16 12 12 8"></polyline><line x1="8" y1="12" x2="16" y2="12"></line></svg>'
ICON_DEST = '<svg viewBox="0 0 24 24" width="12" height="12" stroke="#0070f3" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M2 12h20"></path><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>'
ICON_ARROW_DOWN = '<svg viewBox="0 0 24 24" width="10" height="10" stroke="#ccc" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><polyline points="19 12 12 19 5 12"></polyline></svg>'


# --- DICTIONNAIRE DE TRADUCTION ---
TRANSLATIONS = {
    "en": {
        "page_title": "Newsletter Archive",
        "search_placeholder": "Search by title, sender or date...",
        "btn_infos": "Infos",
        "btn_mobile": "Mobile",
        "btn_dark": "Dark",
        "btn_highlight": "Highlight",
        "meta_section": "Metadata",
        "pixel_section": "Tracking Pixel(s)",
        "label_sent": "Sent Date",
        "label_archived": "Archived Date",
        "label_reading": "Reading Time",
        "label_preheader": "Preheader",
        "label_pixel_status": "Summary",
        "no_pixels": "No trackers detected",
        "pixel_active_msg": "active(s) (Will be counted)",
        "links_section": "Detected Links",
        "legal_summary": "Legal Notice",
        "legal_publisher": "Publisher",
        "legal_hosting": "Hosting",
        "legal_text": "This site is a personal archive.",
        "tooltip_sent": "Received Date",
        "tooltip_archived": "Archived Date"
    },
    "fr": {
        "page_title": "Archives Newsletters",
        "search_placeholder": "Rechercher par titre, expéditeur ou date...",
        "btn_infos": "Infos",
        "btn_mobile": "Mobile",
        "btn_dark": "Sombre",
        "btn_highlight": "Surligner",
        "meta_section": "Métadonnées",
        "pixel_section": "Pixel(s) de Tracking",
        "label_sent": "Date d'envoi",
        "label_archived": "Date d'archivage",
        "label_reading": "Temps de lecture",
        "label_preheader": "Pré-header",
        "label_pixel_status": "Résumé",
        "no_pixels": "Aucun traceur détecté",
        "pixel_active_msg": "actif(s) (Sera pris en compte)",
        "links_section": "Liens détectés",
        "legal_summary": "Mentions Légales",
        "legal_publisher": "Éditeur",
        "legal_hosting": "Hébergement",
        "legal_text": "Ce site est une archive personnelle.",
        "tooltip_sent": "Date de réception",
        "tooltip_archived": "Date d'archivage"
    }
}

JS_TRANSLATION_LOGIC = f"""
const TRANSLATIONS = {json.dumps(TRANSLATIONS)};
let currentLang = localStorage.getItem('lang') || 'en';

function updateLanguage(lang) {{
    currentLang = lang;
    localStorage.setItem('lang', lang);
    const t = TRANSLATIONS[lang];
    
    document.querySelectorAll('[data-i18n]').forEach(el => {{
        const key = el.getAttribute('data-i18n');
        if (t[key]) el.textContent = t[key];
    }});
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput && t['search_placeholder']) searchInput.placeholder = t['search_placeholder'];
    
    document.querySelectorAll('[data-i18n-title]').forEach(el => {{
        const key = el.getAttribute('data-i18n-title');
        if (t[key]) el.title = t[key];
    }});

    document.querySelectorAll('.btn[data-i18n-btn]').forEach(el => {{
        const key = el.getAttribute('data-i18n-btn');
        if (t[key]) {{
            const icon = el.firstElementChild;
            el.innerHTML = ''; 
            el.appendChild(icon);
            el.appendChild(document.createTextNode(' ' + t[key]));
        }}
    }});
    
    const langBtn = document.getElementById('lang-toggle');
    if(langBtn) langBtn.innerHTML = `<span>{ICON_LANG}</span>&nbsp;${{lang === 'en' ? 'FR' : 'EN'}}`;
}}

function toggleLanguage() {{
    const newLang = currentLang === 'en' ? 'fr' : 'en';
    updateLanguage(newLang);
}}

updateLanguage(currentLang);
"""

def resolve_redirect_chain(start_url, max_redirects=5):
    if not start_url: return start_url, []
    if start_url.startswith("mailto:") or start_url.startswith("tel:"): return start_url, []

    chain = [start_url]
    current_url = start_url
    session = requests.Session()
    
    for _ in range(max_redirects):
        try:
            resp = session.head(current_url, allow_redirects=False, headers=HEADERS, timeout=2.0)
            if 300 <= resp.status_code < 400:
                location = resp.headers.get('Location') or resp.headers.get('location')
                if location:
                    if not location.startswith('http'):
                        location = urljoin(current_url, location)
                    if location in chain: break
                    chain.append(location)
                    current_url = location
                else: break
            else: break
        except: break
            
    return current_url, chain

def clean_subject_prefixes(subject):
    if not subject: return "Untitled"
    pattern = r'^\s*\[?(?:Fwd|Fw|Tr|Re|Aw|Wg)\s*:\s*\]?\s*'
    cleaned = subject
    while re.match(pattern, cleaned, re.IGNORECASE):
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def get_deterministic_id(subject):
    if not subject: subject = "sans_titre"
    hash_object = hashlib.sha256(subject.encode('utf-8', errors='ignore'))
    return hash_object.hexdigest()[:12]

def get_email_date(msg):
    try:
        date_header = msg["Date"]
        if date_header:
            dt = parsedate_to_datetime(date_header)
            # INCLUDE TIME
            return dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        pass
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

def get_clean_sender(msg):
    try:
        from_header = msg["From"]
        if not from_header: return "Unknown"
        decoded_header = ""
        for part, encoding in decode_header(from_header):
            if isinstance(part, bytes):
                decoded_header += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_header += str(part)
        realname, email_addr = parseaddr(decoded_header)
        sender = realname if realname else email_addr
        return sender.strip() if sender else "Unknown Sender"
    except:
        return "Unknown Sender"

def get_decoded_email_subject(msg):
    subject_header = msg["Subject"]
    if not subject_header: return "Untitled"
    decoded_list = decode_header(subject_header)
    full_subject = ""
    for part, encoding in decoded_list:
        if isinstance(part, bytes):
            full_subject += part.decode(encoding or "utf-8", errors="ignore")
        else:
            full_subject += str(part)
    return full_subject.strip()

def get_page_metadata(filepath):
    title = "Untitled"
    date_str = None
    archiving_date_str = None
    sender = "Unknown Sender"
    preheader = ""
    reading_time = "1 min"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            
            meta_date = soup.find("meta", attrs={"name": "creation_date"})
            if meta_date and meta_date.get("content"):
                date_str = meta_date["content"]
            
            meta_arch = soup.find("meta", attrs={"name": "archiving_date"})
            if meta_arch and meta_arch.get("content"):
                archiving_date_str = meta_arch["content"]
                
            meta_sender = soup.find("meta", attrs={"name": "sender"})
            if meta_sender and meta_sender.get("content"):
                sender = meta_sender["content"]

            meta_preheader = soup.find("meta", attrs={"name": "preheader"})
            if meta_preheader and meta_preheader.get("content"):
                preheader = meta_preheader["content"]
            
            meta_rt = soup.find("meta", attrs={"name": "reading_time"})
            if meta_rt and meta_rt.get("content"):
                reading_time = meta_rt["content"]

    except Exception:
        pass

    if not date_str:
        try:
            timestamp = os.path.getmtime(filepath)
            date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
        except:
            date_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            
    if not archiving_date_str:
        archiving_date_str = date_str

    return title, date_str, sender, archiving_date_str, preheader, reading_time

def format_date_fr(date_iso):
    # Handles both YYYY-MM-DD and YYYY-MM-DD HH:MM
    try:
        if len(date_iso) > 10:
            dt = datetime.datetime.strptime(date_iso, '%Y-%m-%d %H:%M')
            return dt.strftime('%d/%m/%Y à %H:%M')
        else:
            dt = datetime.datetime.strptime(date_iso, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
    except:
        return date_iso

def generate_index():
    print("Génération du sommaire...")
    if not os.path.exists(OUTPUT_FOLDER):
        return
        
    subfolders = [f.path for f in os.scandir(OUTPUT_FOLDER) if f.is_dir() and not f.name.startswith('.')]
    pages_data = []
    
    for folder in subfolders:
        folder_name = os.path.basename(folder)
        index_file_path = os.path.join(folder, "index.html")
        if not os.path.exists(index_file_path): continue

        full_title, date_rec_str, sender, date_arch_str, preheader, reading_time = get_page_metadata(index_file_path)
        
        pages_data.append({
            "folder": folder_name,
            "title": full_title,
            "sender": sender,
            "preheader": preheader,
            "reading_time": reading_time,
            "date_rec": format_date_fr(date_rec_str),
            "date_arch": format_date_fr(date_arch_str),
            "sort_key": date_rec_str
        })

    pages_data.sort(key=lambda x: x["sort_key"], reverse=True)

    links_html = ""
    for page in pages_data:
        links_html += f'''
        <li class="news-item">
            <a href="{page['folder']}/index.html" class="item-link">
                <div class="info-col">
                    <span class="sender">{page['sender']}</span>
                    <span class="title">{page['title']}</span>
                    <span class="preheader-preview">{page['preheader']}</span>
                </div>
                <div class="date-col">
                    <span class="date" title="Received Date" data-i18n-title="tooltip_sent">📩 {page['date_rec']}</span>
                    <span class="date-arch" title="Archived Date" data-i18n-title="tooltip_archived">🗄️ {page['date_arch']}</span>
                </div>
            </a>
        </li>
        '''

    current_year = datetime.datetime.now().year

    index_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Newsletter Archive</title>
        <meta name="robots" content="noindex, nofollow">
        <style>
            :root {{
                --bg-body: #f6f9fc; --bg-card: #ffffff; --text-main: #333333; --text-muted: #666666; --text-light: #888888;
                --border-color: #eaeaea; --accent-color: #0070f3; --hover-bg: #f8f9fa; --input-bg: #fcfcfc; --shadow: rgba(0,0,0,0.05);
            }}
            [data-theme="dark"] {{
                --bg-body: #121212; --bg-card: #1e1e1e; --text-main: #e0e0e0; --text-muted: #a0a0a0; --text-light: #666666;
                --border-color: #333333; --accent-color: #4da3ff; --hover-bg: #252525; --input-bg: #252525; --shadow: rgba(0,0,0,0.3);
            }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 0; padding: 20px; display: flex; flex-direction: column; min-height: 100vh; box-sizing: border-box; transition: background-color 0.3s, color 0.3s; }}
            .container {{ max-width: 800px; width: 100%; margin: 0 auto; background: var(--bg-card); padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px var(--shadow); flex: 1; position: relative; }}
            .header-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 2px solid var(--border-color); padding-bottom: 20px; }}
            h1 {{ text-align: center; color: var(--text-main); margin: 0; font-size: 1.8rem; flex-grow: 1; }}
            .controls {{ display: flex; gap: 10px; }}

            #theme-toggle, #lang-toggle {{ background: none; border: 1px solid var(--border-color); border-radius: 6px; padding: 0 10px; height: 40px; cursor: pointer; font-size: 0.9rem; display: flex; align-items: center; justify-content: center; transition: all 0.2s; color: var(--text-main); }}
            #theme-toggle:hover, #lang-toggle:hover {{ background-color: var(--hover-bg); border-color: var(--accent-color); }}
            
            .icon-moon {{ display: block; }}
            .icon-sun {{ display: none; }}
            [data-theme="dark"] .icon-moon {{ display: none; }}
            [data-theme="dark"] .icon-sun {{ display: block; }}
            
            #searchInput {{ width: 100%; padding: 12px 20px; margin-bottom: 25px; box-sizing: border-box; border: 2px solid var(--border-color); border-radius: 8px; font-size: 16px; background-color: var(--input-bg); color: var(--text-main); transition: border-color 0.3s; }}
            #searchInput:focus {{ border-color: var(--accent-color); outline: none; }}
            
            ul {{ list-style: none; padding: 0; margin: 0; overflow: hidden; }}
            /* MODIF: Card Style for Index Items */
            li.news-item {{ 
                border: 1px solid var(--border-color); margin-bottom: 12px; border-radius: 8px; background: var(--bg-card);
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            li.news-item:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px var(--shadow); border-color: var(--accent-color); }}
            
            a.item-link {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; text-decoration: none; color: var(--text-main); }}
            
            .info-col {{ display: flex; flex-direction: column; flex: 1; min-width: 0; margin-right: 15px; }}
            /* MODIF: Lowercase sender + fonts */
            .sender {{ font-size: 0.8rem; text-transform: lowercase; color: var(--text-muted); margin-bottom: 6px; }}
            .title {{ font-weight: 600; font-size: 1.05rem; color: var(--text-main); margin-bottom: 6px; }}
            .preheader-preview {{ font-size: 0.85rem; color: var(--text-light); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }}
            
            .date-col {{ display: flex; flex-direction: column; align-items: flex-end; flex-shrink: 0; margin-left: 10px; }}
            .date {{ font-size: 0.8rem; color: var(--text-main); font-weight: 500; white-space: nowrap; font-variant-numeric: tabular-nums; }}
            .date-arch {{ font-size: 0.7rem; color: var(--text-light); white-space: nowrap; font-variant-numeric: tabular-nums; margin-top: 4px; }}
            
            .pagination {{ display: flex; justify-content: center; gap: 8px; margin-top: 25px; flex-wrap: wrap; }}
            .page-btn {{ background: var(--bg-card); border: 1px solid var(--border-color); color: var(--text-main); padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 0.9rem; transition: all 0.2s; }}
            .page-btn:hover {{ background: var(--hover-bg); border-color: var(--accent-color); }}
            .page-btn.active {{ background: var(--accent-color); color: white; border-color: var(--accent-color); }}
            .page-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
            
            footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border-color); text-align: center; color: var(--text-muted); font-size: 0.85rem; }}
            .copyright a {{ color: inherit; text-decoration: none; border-bottom: 1px dotted var(--text-muted); transition: color 0.2s; }}
            .copyright a:hover {{ color: var(--accent-color); border-bottom-color: var(--accent-color); }}
            details {{ margin-top: 15px; cursor: pointer; }}
            details p {{ background: var(--hover-bg); padding: 10px; border-radius: 4px; text-align: left; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header-row">
                <div style="width: 80px;"></div>
                <h1 data-i18n="page_title">Newsletter Archive</h1>
                <div class="controls">
                    <button id="lang-toggle" onclick="toggleLanguage()" title="Switch Language">
                        <span>{ICON_LANG}</span>&nbsp;FR
                    </button>
                    <button id="theme-toggle" title="Toggle Theme">
                        <span class="icon-moon">{ICON_MOON}</span>
                        <span class="icon-sun">{ICON_SUN}</span>
                    </button>
                </div>
            </div>
            <input type="text" id="searchInput" onkeyup="filterList()" placeholder="Search by title, sender or date...">
            <ul id="newsList">
                {links_html}
            </ul>
            <div id="pagination" class="pagination"></div>
            <footer>
                <p class="copyright">&copy; {current_year} <a href="https://github.com/benoit-prentout" target="_blank">Benoît Prentout</a>.</p>
                <details>
                    <summary data-i18n="legal_summary">Legal Notice</summary>
                    <p style="margin-top:10px;">
                        <strong data-i18n="legal_publisher">Publisher</strong> : Benoît Prentout<br>
                        <strong data-i18n="legal_hosting">Hosting</strong> : GitHub Inc.<br>
                        <span data-i18n="legal_text">This site is a personal archive.</span>
                    </p>
                </details>
            </footer>
        </div>
        <script>
        {JS_TRANSLATION_LOGIC}

        const toggleBtn = document.getElementById('theme-toggle');
        const root = document.documentElement;
        const savedTheme = localStorage.getItem('theme');
        const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (savedTheme === 'dark' || (!savedTheme && systemDark)) {{ root.setAttribute('data-theme', 'dark'); }}
        
        toggleBtn.addEventListener('click', () => {{
            const currentTheme = root.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }});

        const itemsPerPage = 10;
        let currentPage = 1;
        const list = document.getElementById("newsList");
        const allItems = Array.from(list.getElementsByClassName('news-item'));
        const paginationContainer = document.getElementById('pagination');

        function showPage(page) {{
            currentPage = page;
            const start = (page - 1) * itemsPerPage;
            const end = start + itemsPerPage;
            
            allItems.forEach((item, index) => {{
                if (index >= start && index < end) {{
                    item.style.display = "";
                }} else {{
                    item.style.display = "none";
                }}
            }});
            renderPaginationControls();
            window.scrollTo(0, 0);
        }}

        function renderPaginationControls() {{
            const totalPages = Math.ceil(allItems.length / itemsPerPage);
            paginationContainer.innerHTML = '';
            
            if (totalPages <= 1) return;

            const prevBtn = document.createElement('button');
            prevBtn.className = 'page-btn';
            prevBtn.innerHTML = '&laquo;';
            prevBtn.disabled = currentPage === 1;
            prevBtn.onclick = () => showPage(currentPage - 1);
            paginationContainer.appendChild(prevBtn);

            let startPage = Math.max(1, currentPage - 2);
            let endPage = Math.min(totalPages, currentPage + 2);
            
            if (startPage > 1) {{
                const firstPage = document.createElement('button');
                firstPage.className = 'page-btn';
                firstPage.innerText = '1';
                firstPage.onclick = () => showPage(1);
                paginationContainer.appendChild(firstPage);
                if (startPage > 2) paginationContainer.appendChild(document.createTextNode('...'));
            }}

            for (let i = startPage; i <= endPage; i++) {{
                const btn = document.createElement('button');
                btn.className = `page-btn ${{i === currentPage ? 'active' : ''}}`;
                btn.innerText = i;
                btn.onclick = () => showPage(i);
                paginationContainer.appendChild(btn);
            }}

            if (endPage < totalPages) {{
                if (endPage < totalPages - 1) paginationContainer.appendChild(document.createTextNode('...'));
                const lastPage = document.createElement('button');
                lastPage.className = 'page-btn';
                lastPage.innerText = totalPages;
                lastPage.onclick = () => showPage(totalPages);
                paginationContainer.appendChild(lastPage);
            }}

            const nextBtn = document.createElement('button');
            nextBtn.className = 'page-btn';
            nextBtn.innerHTML = '&raquo;';
            nextBtn.disabled = currentPage === totalPages;
            nextBtn.onclick = () => showPage(currentPage + 1);
            paginationContainer.appendChild(nextBtn);
        }}

        function filterList() {{
            const input = document.getElementById('searchInput');
            const filter = input.value.toUpperCase();
            
            if (filter === "") {{
                paginationContainer.style.display = "flex";
                showPage(1);
            }} else {{
                paginationContainer.style.display = "none";
                allItems.forEach(item => {{
                    const text = item.textContent || item.innerText;
                    if (text.toUpperCase().indexOf(filter) > -1) {{
                        item.style.display = "";
                    }} else {{
                        item.style.display = "none";
                    }}
                }});
            }}
        }}

        showPage(1);
        </script>
    </body>
    </html>
    """
    with open(f"{OUTPUT_FOLDER}/index.html", "w", encoding='utf-8') as f:
        f.write(index_content)

def process_emails():
    try:
        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)

        print("Connexion au serveur Gmail...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        
        rv, data = mail.select(f'"{TARGET_LABEL}"')
        if rv != 'OK':
            print(f"ERREUR: Impossible de trouver le libellé '{TARGET_LABEL}'.")
            return

        status, messages = mail.search(None, 'ALL')
        if messages[0]:
            email_ids = messages[0].split()
            print(f"{len(email_ids)} emails trouvés au total.")

            # PHASE 1 : Synchro
            valid_folder_ids = set()
            email_map = {}
            for num in email_ids:
                try:
                    status, msg_data = mail.fetch(num, '(BODY.PEEK[HEADER.FIELDS (SUBJECT)])')
                    msg_header = email.message_from_bytes(msg_data[0][1])
                    raw_subject = get_decoded_email_subject(msg_header)
                    subject = clean_subject_prefixes(raw_subject)
                    f_id = get_deterministic_id(subject)
                    valid_folder_ids.add(f_id)
                    email_map[f_id] = num
                except: pass

            local_folders = set([f.name for f in os.scandir(OUTPUT_FOLDER) if f.is_dir() and not f.name.startswith('.')])
            for f_id in (local_folders - valid_folder_ids):
                shutil.rmtree(os.path.join(OUTPUT_FOLDER, f_id), ignore_errors=True)
                print(f"Supprimé (Synchro): {f_id}")

            # PHASE 2 : Traitement
            folders_to_process = list(valid_folder_ids)[:BATCH_SIZE]
            
            print(f"Mise à jour de {len(folders_to_process)} emails (batch)...")

            for f_id in folders_to_process:
                num = email_map[f_id]
                try:
                    status, msg_data = mail.fetch(num, '(RFC822)')
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    raw_subject = get_decoded_email_subject(msg)
                    subject = clean_subject_prefixes(raw_subject)
                    sender_name = get_clean_sender(msg)
                    email_date_str = get_email_date(msg)
                    
                    newsletter_path = os.path.join(OUTPUT_FOLDER, f_id)
                    os.makedirs(newsletter_path, exist_ok=True)
                    
                    # EXTRACTION
                    payload = None
                    charset = None
                    html_content = ""

                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/html":
                                payload = part.get_payload(decode=True)
                                charset = part.get_content_charset()
                                break
                    else:
                        if msg.get_content_type() == "text/html":
                            payload = msg.get_payload(decode=True)
                            charset = msg.get_content_charset()

                    if not payload:
                        print(f"Ignoré (Pas de HTML): {subject}")
                        continue
                    
                    # DECODAGE
                    decoding_options = [charset, 'utf-8', 'windows-1252', 'iso-8859-1']
                    decoded = False
                    for encoding in decoding_options:
                        if not encoding: continue
                        try:
                            html_content = payload.decode(encoding)
                            decoded = True
                            break
                        except (UnicodeDecodeError, LookupError):
                            continue
                    
                    if not decoded:
                        html_content = payload.decode('utf-8', errors='ignore')

                    # PARSING
                    soup = BeautifulSoup(html_content, "html.parser")
                    
                    # --- DETECTION PIXEL ---
                    detected_pixels_list = []
                    for img in soup.find_all("img"):
                        src = img.get("src", "")
                        if any(pattern in src for pattern in TRACKING_PATTERNS):
                            detected_pixels_list.append(src)
                            img['src'] = "" 
                            img['alt'] = "[TRACKING PIXEL REMOVED]"
                            img['style'] = "display:none !important;"

                    # Nettoyage léger
                    for s in soup(["script", "iframe", "object", "meta"]): 
                        s.extract()

                    # Gestion des blocs de transfert Gmail
                    for div in soup.find_all("div"):
                        if any(k in div.get_text() for k in ["Forwarded message", "Message transféré"]) and "-----" in div.get_text():
                            new_body = soup.new_tag("body")
                            for sibling in div.next_siblings: new_body.append(sibling)
                            if soup.body:
                                soup.body.replace_with(new_body)
                            break
                    
                    # EXTRACTION PREHEADER
                    raw_text = soup.get_text(separator=" ", strip=True)
                    preheader_txt = raw_text[:160] + "..." if len(raw_text) > 160 else raw_text
                    safe_preheader_attr = html.escape(preheader_txt, quote=True)

                    # CALCUL DU TEMPS DE LECTURE
                    word_count = len(raw_text.split())
                    reading_time_min = max(1, round(word_count / 200))
                    reading_time_str = f"{reading_time_min} min"

                    # TRAITEMENT DES LIENS ET RÉSOLUTION DES REDIRECTIONS
                    links = []
                    link_idx = 0
                    
                    all_links = soup.find_all('a', href=True)
                    print(f"   -> Résolution de {len(all_links)} liens...")
                    
                    for a in all_links:
                        txt = a.get_text(strip=True) or "[Image/Vide]"
                        link_id = f"detected-link-{link_idx}"
                        a['id'] = link_id
                        
                        original_url = a['href']
                        final_dest, chain = resolve_redirect_chain(original_url)
                        
                        # --- MODIF : SAUTS DE LIGNE VERTICAUX + FLÈCHE ---
                        chain_text = "\n⬇\n".join(chain)
                        
                        links.append({
                            'id': link_id,
                            'txt': txt[:50] + "..." if len(txt)>50 else txt, 
                            'original_url': original_url,
                            'final_url': final_dest,
                            'chain_text': chain_text
                        })
                        link_idx += 1
                    
                    # Génération HTML des liens (Avec Design "Cell/Card")
                    links_html = ""
                    for l in links:
                        safe_tooltip = html.escape(l["chain_text"], quote=True)
                        links_html += f'''
                        <li class="link-card">
                            <div class="link-card-header">{l["txt"]}</div>
                            <div class="link-card-body">
                                <div class="link-line" title="Original Link">
                                    <span class="link-icon-box">{ICON_ORIGIN}</span>
                                    <span class="link-url-text orig">{l["original_url"]}</span>
                                </div>
                                <div class="link-arrow-sep">{ICON_ARROW_DOWN}</div>
                                <div class="link-line" title="Destination Link">
                                    <span class="link-icon-box">{ICON_DEST}</span>
                                    <span class="link-url-text dest">{l["final_url"]}</span>
                                </div>
                            </div>
                            <div class="link-card-footer">
                                <button class="btn-action" data-tooltip="{safe_tooltip}" title="Show Redirect Path">
                                    {ICON_CHAIN} Path
                                </button>
                                <button class="btn-action" onclick="scrollToLink('{l["id"]}')" title="Locate in Email">
                                    {ICON_EYE} Locate
                                </button>
                                <button class="btn-action" onclick="copyToClipboard('{l["final_url"]}')" title="Copy Final URL">
                                    {ICON_COPY} Copy
                                </button>
                            </div>
                        </li>
                        '''

                    # --- IMAGES LOCALES ---
                    img_counter = 0
                    for img in soup.find_all("img"):
                        lazy_attrs = ['data-src', 'data-original', 'data-lazy', 'data-url']
                        for attr in lazy_attrs:
                            if img.get(attr):
                                img['src'] = img[attr] 
                                del img[attr] 
                                break
                        
                        if img.get('srcset'):
                            if not img.get('src'):
                                try:
                                    first_url = img['srcset'].split(',')[0].split(' ')[0]
                                    img['src'] = first_url
                                except: pass
                            del img['srcset'] 

                        src = img.get("src")
                        if not src or src.startswith("data:") or src.startswith("cid:"): continue
                        
                        try:
                            if src.startswith("//"): src = "https:" + src
                            r = requests.get(src, headers=HEADERS, timeout=10)
                            if r.status_code == 200:
                                content_type = r.headers.get('content-type', '')
                                ext = mimetypes.guess_extension(content_type)
                                if not ext: ext = ".jpg"
                                if ext == ".jpe": ext = ".jpg"

                                local_name = f"img_{img_counter}{ext}"
                                local_path = os.path.join(newsletter_path, local_name)
                                with open(local_path, "wb") as f: f.write(r.content)
                                img['src'] = local_name
                                img['loading'] = 'lazy'
                                img_counter += 1
                        except Exception: pass

                    # CSS inline images
                    css_url_pattern = re.compile(r'url\s*\((?:["\']?)(.*?)(?:["\']?)\)', re.IGNORECASE)
                    for tag in soup.find_all(style=True):
                        style = tag['style']
                        if 'url' in style:
                            matches = css_url_pattern.findall(style)
                            new_style = style
                            modified = False
                            for url in matches:
                                original_url = url.strip()
                                if original_url.startswith("data:") or any(p in original_url for p in TRACKING_PATTERNS): continue
                                target_url = original_url
                                if target_url.startswith("//"): target_url = "https:" + target_url
                                try:
                                    r = requests.get(target_url, headers=HEADERS, timeout=10)
                                    if r.status_code == 200:
                                        content_type = r.headers.get('content-type', '')
                                        ext = mimetypes.guess_extension(content_type) or ".jpg"
                                        local_name = f"bg_{img_counter}{ext}"
                                        local_path = os.path.join(newsletter_path, local_name)
                                        with open(local_path, "wb") as f: f.write(r.content)
                                        new_style = new_style.replace(original_url, local_name)
                                        img_counter += 1
                                        modified = True
                                except: pass
                            if modified: tag['style'] = new_style

                    # VIEWER
                    safe_html = json.dumps(str(soup))
                    nb_links = len(links)
                    date_arch_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                    
                    pixel_html_block = ""
                    if detected_pixels_list:
                        pixels_li = ""
                        for p_url in detected_pixels_list:
                            display_url = p_url[:55] + "..." if len(p_url) > 55 else p_url
                            pixels_li += f"""
                            <li class="pixel-li">
                                <div class="pixel-row">
                                    <span class="icon-bug" style="color:green;">{ICON_CHECK}</span>
                                    <span class="pixel-url" title="{html.escape(p_url)}">{html.escape(display_url)}</span>
                                </div>
                            </li>
                            """
                        pixel_html_block = f"""
                        <div class="meta-item">
                            <span class="meta-label" data-i18n="label_pixel_status">Summary</span>
                            <span class="status-badge ok"><span class="icon-status">{ICON_CHECK}</span> <span data-i18n="pixel_active_msg">active(s) (Will be counted)</span> ({len(detected_pixels_list)})</span>
                        </div>
                        <ul class="pixel-list">
                            {pixels_li}
                        </ul>
                        """
                    else:
                         pixel_html_block = f"""
                        <div class="meta-item">
                            <span class="status-badge warn"><span class="icon-status">{ICON_INFO}</span> <span data-i18n="no_pixels">No trackers detected</span></span>
                        </div>
                        """

                    viewer_content = f"""
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <meta name="creation_date" content="{email_date_str}">
                        <meta name="sender" content="{sender_name}">
                        <meta name="archiving_date" content="{date_arch_str}">
                        <meta name="preheader" content="{safe_preheader_attr}">
                        <meta name="reading_time" content="{reading_time_str}">
                        <title>{subject}</title>
                        <style>
                            body {{ margin: 0; padding: 0; background: #eef2f5; font-family: Roboto, Helvetica, Arial, sans-serif; overflow: hidden; }}
                            .header {{ position: fixed; top: 0; left: 0; right: 0; height: 60px; background: white; border-bottom: 1px solid #ddd; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; z-index: 100; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }}
                            .title {{ font-size: 16px; font-weight: 600; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-right: 20px; }}
                            .controls {{ display: flex; gap: 10px; flex-shrink: 0; }}
                            .btn {{ padding: 6px 12px; border: 1px solid #ccc; background: #f9f9f9; border-radius: 6px; cursor: pointer; font-size: 13px; display: flex; align-items: center; gap: 6px; transition: all 0.2s; color: #333; }}
                            .btn:hover {{ background: #eee; }}
                            .btn.active {{ background: #0070f3; color: white; border-color: #0070f3; }}
                            .btn svg {{ display: block; }}
                            .main-view {{ margin-top: 60px; height: calc(100vh - 60px); display: flex; justify-content: center; align-items: flex-start; background: #eef2f5; overflow: hidden; padding-top: 20px; }}
                            .iframe-wrapper {{ width: 1000px; max-width: 95%; height: 90%; transition: width 0.3s ease; background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border-radius: 4px; }}
                            iframe {{ width: 100%; height: 100%; border: none; display: block; border-radius: inherit; }}
                            body.mobile-mode .iframe-wrapper {{ width: 375px; height: 812px; max-height: 85vh; border: none; box-shadow: 0 10px 40px rgba(0,0,0,0.15); }}
                            
                            /* --- SIDEBAR --- */
                            .sidebar {{ position: fixed; top: 60px; right: -420px; width: 420px; height: calc(100vh - 60px); background: white; border-left: 1px solid #ddd; transition: right 0.3s; overflow-y: auto; z-index: 90; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; gap: 20px; }}
                            .sidebar.open {{ right: 0; }}
                            
                            .sidebar h3 {{ margin-top: 0; font-size: 16px; color: #333; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }}
                            .meta-item {{ margin-bottom: 12px; font-size: 13px; color: #555; }}
                            .meta-label {{ font-weight: 600; display: block; margin-bottom: 3px; color: #333; }}
                            .meta-val {{ word-break: break-word; line-height: 1.4; }}
                            .preheader-box {{ background: #f8f9fa; padding: 10px; border-radius: 6px; border: 1px solid #eee; font-style: italic; color: #666; font-size: 12px; }}
                            
                            .status-badge {{ display: inline-flex; align-items: center; gap: 5px; font-weight: 500; }}
                            .status-badge.ok {{ color: green; }}
                            .status-badge.warn {{ color: orange; }}
                            
                            /* Pixel List Style */
                            .pixel-list {{ list-style: none; padding: 0; margin: 0; background: #f0fff4; border: 1px solid #c3e6cb; border-radius: 4px; }}
                            .pixel-li {{ padding: 8px; border-bottom: 1px solid #c3e6cb; }}
                            .pixel-li:last-child {{ border-bottom: none; }}
                            .pixel-row {{ display: flex; align-items: center; gap: 6px; color: #155724; font-size: 11px; }}
                            .pixel-url {{ word-break: break-all; font-family: monospace; }}
                            
                            /* --- NEW LINK CARD DESIGN --- */
                            .sidebar ul {{ list-style: none; padding: 0; margin: 0; }}
                            .link-card {{
                                border: 1px solid #eee; border-radius: 8px; background: #fff; margin-bottom: 12px;
                                box-shadow: 0 1px 3px rgba(0,0,0,0.05); overflow: hidden;
                            }}
                            .link-card-header {{
                                padding: 8px 12px; background: #fcfcfc; border-bottom: 1px solid #f0f0f0;
                                font-weight: 600; color: #333; font-size: 12px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;
                            }}
                            .link-card-body {{ padding: 10px 12px; }}
                            .link-line {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
                            .link-line:last-child {{ margin-bottom: 0; }}
                            .link-icon-box {{ width: 16px; text-align: center; display: flex; justify-content: center; }}
                            .link-url-text {{ font-family: monospace; font-size: 11px; word-break: break-all; line-height: 1.3; }}
                            .link-url-text.orig {{ color: #888; }}
                            .link-url-text.dest {{ color: #0070f3; font-weight: 600; }}
                            .link-arrow-sep {{ padding-left: 20px; color: #ccc; font-size: 10px; margin: 2px 0; }}
                            
                            .link-card-footer {{
                                padding: 6px 12px; background: #fafafa; border-top: 1px solid #f0f0f0; display: flex; gap: 10px; justify-content: flex-end;
                            }}
                            .btn-action {{
                                border: none; background: transparent; padding: 4px 8px; cursor: pointer; color: #666;
                                display: flex; align-items: center; gap: 4px; font-size: 11px; border-radius: 4px;
                            }}
                            .btn-action:hover {{ background: #eaeaea; color: #0070f3; }}
                            
                            /* Global Tooltip Fixed */
                            .global-tooltip {{
                                position: fixed; background: #333; color: white; padding: 10px; border-radius: 6px;
                                z-index: 10000; max-width: 300px; font-size: 11px; pointer-events: none; display: none;
                                box-shadow: 0 4px 10px rgba(0,0,0,0.2); white-space: pre-wrap; word-break: break-all; line-height: 1.4;
                            }}
                            .global-tooltip.visible {{ display: block; }}

                            body.dark-mode .main-view {{ background: #121212; }}
                            body.dark-mode .header {{ background: #1e1e1e; border-bottom-color: #333; }}
                            body.dark-mode .title {{ color: #e0e0e0; }}
                            body.dark-mode .btn {{ background: #2c2c2c; border-color: #444; color: #ccc; }}
                            body.dark-mode .btn.active {{ background: #0070f3; color: white; }}
                            body.dark-mode .iframe-wrapper {{ box-shadow: 0 0 25px rgba(255, 255, 255, 0.15); border: 1px solid #333; }}
                            body.dark-mode .sidebar {{ background: #1e1e1e; border-left-color: #333; }}
                            body.dark-mode .sidebar h3 {{ color: #fff; border-bottom-color: #333; }}
                            body.dark-mode .meta-label {{ color: #ccc; }}
                            body.dark-mode .meta-item {{ color: #aaa; }}
                            body.dark-mode .preheader-box {{ background: #252525; border-color: #333; color: #aaa; }}
                            
                            body.dark-mode .pixel-list {{ background: #1e2e1e; border-color: #2b4c2b; }}
                            body.dark-mode .pixel-li {{ border-bottom-color: #2b4c2b; }}
                            body.dark-mode .pixel-row {{ color: #90cea1; }}
                            
                            body.dark-mode .link-card {{ background: #252525; border-color: #333; }}
                            body.dark-mode .link-card-header {{ background: #2c2c2c; border-bottom-color: #333; color: #ddd; }}
                            body.dark-mode .link-card-footer {{ background: #2c2c2c; border-top-color: #333; }}
                            body.dark-mode .link-url-text.dest {{ color: #4da3ff; }}
                            body.dark-mode .btn-action {{ color: #aaa; }}
                            body.dark-mode .btn-action:hover {{ background: #333; color: #fff; }}
                        </style>
                    </head>
                    <body>
                        <div id="global-tooltip" class="global-tooltip"></div>
                        <header class="header">
                            <div class="title">{subject}</div>
                            <div class="controls">
                                <button class="btn" onclick="toggleLanguage()" id="lang-toggle" title="Switch Language">
                                    <span>{ICON_LANG}</span>&nbsp;FR
                                </button>
                                <button class="btn" onclick="toggleHighlight()" id="btn-highlight" data-i18n-btn="btn_highlight">
                                    <span>{ICON_TARGET}</span>&nbsp;Highlight
                                </button>
                                <button class="btn" onclick="toggleLinks()" id="btn-links" data-i18n-btn="btn_infos">
                                    <span>{ICON_INFO}</span>&nbsp;Infos
                                </button>
                                <button class="btn" onclick="toggleMobile()" id="btn-mobile" data-i18n-btn="btn_mobile">
                                    <span>{ICON_MOBILE}</span>&nbsp;Mobile
                                </button>
                                <button class="btn" onclick="toggleDark()" id="btn-dark" data-i18n-btn="btn_dark">
                                    <span>{ICON_MOON}</span>&nbsp;Dark
                                </button>
                            </div>
                        </header>
                        <div class="main-view">
                            <div class="iframe-wrapper"><iframe id="emailFrame"></iframe></div>
                        </div>
                        <div class="sidebar" id="sidebar">
                            
                            <!-- 1. METADATA (FIRST) -->
                            <div class="sidebar-section">
                                <h3 data-i18n="meta_section">{ICON_INFO} Metadata</h3>
                                <div class="meta-item"><span class="meta-label" data-i18n="label_sent">📅 Sent Date</span><span class="meta-val">{format_date_fr(email_date_str)}</span></div>
                                <div class="meta-item"><span class="meta-label" data-i18n="label_archived">🗄️ Archived Date</span><span class="meta-val">{format_date_fr(date_arch_str)}</span></div>
                                <div class="meta-item"><span class="meta-label" data-i18n="label_reading">⏱️ Reading Time</span><span class="meta-val">{reading_time_str}</span></div>
                                <div class="meta-item"><span class="meta-label" data-i18n="label_preheader">👀 Preheader (Preview)</span><div class="preheader-box">{safe_preheader_attr}</div></div>
                            </div>
                            
                            <!-- 2. PIXELS (SECOND) -->
                            <div class="sidebar-section">
                                <h3 data-i18n="pixel_section">{ICON_WARN} Tracking Pixel(s)</h3>
                                {pixel_html_block}
                            </div>
                            
                            <div class="sidebar-section">
                                <h3 data-i18n="links_section">{ICON_LINK} Detected Links ({nb_links})</h3>
                                <ul>{links_html}</ul>
                            </div>
                        </div>
                        <script>
                            {JS_TRANSLATION_LOGIC}
                            const emailContent = {safe_html};
                            const frame = document.getElementById('emailFrame');
                            frame.contentDocument.open();
                            frame.contentDocument.write(emailContent);
                            const meta = frame.contentDocument.createElement('meta');
                            meta.name = 'viewport';
                            meta.content = 'width=device-width, initial-scale=1.0';
                            frame.contentDocument.head.appendChild(meta);
                            const base = frame.contentDocument.createElement('base');
                            base.target = '_blank';
                            frame.contentDocument.head.appendChild(base);
                            frame.contentDocument.close();
                            const style = frame.contentDocument.createElement('style');
                            style.textContent = `
                                html {{ -ms-overflow-style: none; scrollbar-width: none; }}
                                html::-webkit-scrollbar {{ display: none; }}
                                body::-webkit-scrollbar {{ display: none; width: 0; }}
                                body {{ margin: 0; padding: 0; font-family: Roboto, Helvetica, Arial, sans-serif; color: #222; line-height: 1.5; overflow-wrap: break-word; }}
                                table {{ border-spacing: 0; border-collapse: collapse; }}
                                img {{ height: auto !important; vertical-align: middle; border: 0; }}
                                img[style*="display: block"], img[style*="display:block"] {{ margin-left: auto !important; margin-right: auto !important; }}
                                a, .link-text {{ color: #1a0dab; }}
                                html.dark-mode-internal {{ filter: invert(1) hue-rotate(180deg); }}
                                html.dark-mode-internal img, html.dark-mode-internal video, html.dark-mode-internal [style*="background-image"] {{ filter: invert(1) hue-rotate(180deg); }}
                                
                                body.highlight-links a {{ border: 2px solid red !important; background-color: yellow !important; color: black !important; position: relative; z-index: 9999; box-shadow: 0 0 5px rgba(255,0,0,0.5); animation: flash 1s infinite alternate; display: inline-block; }}
                                body.highlight-links a img {{ outline: 4px solid #ff0000 !important; outline-offset: -2px; opacity: 0.8; filter: grayscale(50%); }}
                                
                                @keyframes target-pulse {{ 
                                    0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }}
                                    50% {{ transform: scale(1.05); box-shadow: 0 0 20px 10px rgba(255, 0, 0, 0); }}
                                    100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }}
                                }}
                                a.flash-target {{
                                    position: relative;
                                    z-index: 99999;
                                    outline: 10px solid #ff0000 !important;
                                    background-color: rgba(255, 255, 0, 0.5) !important;
                                    animation: target-pulse 0.5s ease-in-out 4; /* 4 pulses */
                                    box-shadow: 0 0 50px rgba(255,0,0,1); /* Big glow */
                                }}

                                @media screen and (max-width: 600px) {{ table, tbody, tr, td {{ width: 100% !important; min-width: 0 !important; box-sizing: border-box !important; height: auto !important; }} div[style*="width"] {{ width: 100% !important; max-width: 100% !important; }} img {{ width: auto !important; max-width: 100% !important; }} }}
                            `;
                            frame.contentDocument.head.appendChild(style);
                            function toggleMobile() {{ document.body.classList.toggle('mobile-mode'); document.getElementById('btn-mobile').classList.toggle('active'); }}
                            function toggleDark() {{ document.body.classList.toggle('dark-mode'); document.getElementById('btn-dark').classList.toggle('active'); if(frame.contentDocument.documentElement) {{ frame.contentDocument.documentElement.classList.toggle('dark-mode-internal'); }} }}
                            function toggleLinks() {{ document.getElementById('sidebar').classList.toggle('open'); document.getElementById('btn-links').classList.toggle('active'); }}
                            function toggleHighlight() {{ const btn = document.getElementById('btn-highlight'); btn.classList.toggle('active'); if(frame.contentDocument.body) {{ frame.contentDocument.body.classList.toggle('highlight-links'); }} }}
                            function copyToClipboard(text) {{ navigator.clipboard.writeText(text).then(() => {{ }}).catch(err => {{ console.error('Failed to copy: ', err); }}); }}
                            function scrollToLink(id) {{ const el = frame.contentDocument.getElementById(id); if(el) {{ el.scrollIntoView({{behavior: 'smooth', block: 'center'}}); el.classList.add('flash-target'); setTimeout(() => el.classList.remove('flash-target'), 2000); }} else {{ console.warn('Link not found in iframe:', id); }} }}
                            
                            // TOOLTIP LOGIC
                            const tooltip = document.getElementById('global-tooltip');
                            document.querySelectorAll('[data-tooltip]').forEach(btn => {{
                                btn.addEventListener('mouseenter', e => {{
                                    const text = btn.getAttribute('data-tooltip');
                                    if(text) {{
                                        tooltip.textContent = text;
                                        tooltip.classList.add('visible');
                                        const rect = btn.getBoundingClientRect();
                                        tooltip.style.top = rect.top + 'px';
                                        tooltip.style.right = (window.innerWidth - rect.left + 10) + 'px';
                                        tooltip.style.left = 'auto';
                                    }}
                                }});
                                btn.addEventListener('mouseleave', () => {{
                                    tooltip.classList.remove('visible');
                                }});
                            }});
                        </script>
                    </body>
                    </html>
                    """
                    
                    with open(os.path.join(newsletter_path, "index.html"), "w", encoding='utf-8') as f:
                        f.write(viewer_content)

                except Exception as e:
                    print(f"Erreur traitement {f_id}: {e}")

            generate_index()
            print("Terminé.")
        else:
            print("Aucun email trouvé.")
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"Erreur critique: {e}")

if __name__ == "__main__":
    process_emails()
