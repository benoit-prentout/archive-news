import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr
from bs4 import BeautifulSoup
import os
import re
import mimetypes
import requests
import datetime
import hashlib
import shutil
import json
import html

# --- CONFIGURATION ---
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]
TARGET_LABEL = "Github/archive-newsletters"
OUTPUT_FOLDER = "docs"
BATCH_SIZE = 9999

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- ICONS SVG ---
ICON_MOON = '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>'
ICON_SUN = '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>'
ICON_MOBILE = '<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>'
ICON_LINK = '<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>'
ICON_INFO = '<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'

def clean_subject_prefixes(subject):
    if not subject: return "Sans titre"
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
            return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    return datetime.datetime.now().strftime('%Y-%m-%d')

def get_clean_sender(msg):
    try:
        from_header = msg["From"]
        if not from_header: return "Inconnu"
        decoded_header = ""
        for part, encoding in decode_header(from_header):
            if isinstance(part, bytes):
                decoded_header += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_header += str(part)
        realname, email_addr = parseaddr(decoded_header)
        sender = realname if realname else email_addr
        return sender.strip() if sender else "Expéditeur Inconnu"
    except:
        return "Expéditeur Inconnu"

def get_decoded_email_subject(msg):
    subject_header = msg["Subject"]
    if not subject_header: return "Sans Titre"
    decoded_list = decode_header(subject_header)
    full_subject = ""
    for part, encoding in decoded_list:
        if isinstance(part, bytes):
            full_subject += part.decode(encoding or "utf-8", errors="ignore")
        else:
            full_subject += str(part)
    return full_subject.strip()

def get_page_metadata(filepath):
    title = "Sans titre"
    date_str = None
    archiving_date_str = None
    sender = "Expéditeur Inconnu"
    preheader = ""
    
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
    except Exception:
        pass

    if not date_str:
        try:
            timestamp = os.path.getmtime(filepath)
            date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        except:
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
            
    if not archiving_date_str:
        archiving_date_str = date_str

    return title, date_str, sender, archiving_date_str, preheader

def format_date_fr(date_iso):
    try:
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

        full_title, date_rec_str, sender, date_arch_str, preheader = get_page_metadata(index_file_path)
        
        pages_data.append({
            "folder": folder_name,
            "title": full_title,
            "sender": sender,
            "preheader": preheader,
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
                    <span class="date" title="Date de réception">📩 {page['date_rec']}</span>
                    <span class="date-arch" title="Date d'archivage">🗄️ {page['date_arch']}</span>
                </div>
            </a>
        </li>
        '''

    current_year = datetime.datetime.now().year

    index_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Archives Newsletters - Benoît Prentout</title>
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
            
            #theme-toggle {{ background: none; border: 1px solid var(--border-color); border-radius: 50%; width: 40px; height: 40px; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.2s; color: var(--text-main); }}
            #theme-toggle:hover {{ background-color: var(--hover-bg); border-color: var(--accent-color); }}
            
            .icon-moon {{ display: block; }}
            .icon-sun {{ display: none; }}
            [data-theme="dark"] .icon-moon {{ display: none; }}
            [data-theme="dark"] .icon-sun {{ display: block; }}
            
            #searchInput {{ width: 100%; padding: 12px 20px; margin-bottom: 25px; box-sizing: border-box; border: 2px solid var(--border-color); border-radius: 8px; font-size: 16px; background-color: var(--input-bg); color: var(--text-main); transition: border-color 0.3s; }}
            #searchInput:focus {{ border-color: var(--accent-color); outline: none; }}
            
            ul {{ list-style: none; padding: 0; margin: 0; border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }}
            li {{ border-bottom: 1px solid var(--border-color); margin: 0; }}
            li:last-child {{ border-bottom: none; }}
            
            a.item-link {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; background: var(--bg-card); text-decoration: none; color: var(--text-main); transition: background 0.1s ease; }}
            a.item-link:hover {{ background-color: var(--hover-bg); }}
            
            .info-col {{ display: flex; flex-direction: column; flex: 1; min-width: 0; margin-right: 15px; }}
            .sender {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-light); margin-bottom: 4px; font-weight: 600; }}
            .title {{ font-weight: 500; font-size: 1rem; color: var(--text-main); margin-bottom: 4px; }}
            .preheader-preview {{ font-size: 0.85rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }}
            
            .date-col {{ display: flex; flex-direction: column; align-items: flex-end; flex-shrink: 0; margin-left: 10px; }}
            .date {{ font-size: 0.85rem; color: var(--text-muted); white-space: nowrap; font-variant-numeric: tabular-nums; }}
            .date-arch {{ font-size: 0.7rem; color: var(--text-light); white-space: nowrap; font-variant-numeric: tabular-nums; margin-top: 3px; }}
            
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
                <div style="width: 40px;"></div>
                <h1>📬 Archives Newsletters</h1>
                <button id="theme-toggle" title="Changer le thème">
                    <span class="icon-moon">{ICON_MOON}</span>
                    <span class="icon-sun">{ICON_SUN}</span>
                </button>
            </div>
            <input type="text" id="searchInput" onkeyup="filterList()" placeholder="Rechercher par titre, expéditeur ou date...">
            <ul id="newsList">
                {links_html}
            </ul>
            <div id="pagination" class="pagination"></div>
            <footer>
                <p class="copyright">&copy; {current_year} <a href="https://github.com/benoit-prentout" target="_blank">Benoît Prentout</a>.</p>
                <details>
                    <summary>Mentions Légales</summary>
                    <p style="margin-top:10px;"><strong>Éditeur :</strong> Benoît Prentout<br><strong>Hébergement :</strong> GitHub Inc.<br>Ce site est une archive personnelle.</p>
                </details>
            </footer>
        </div>
        <script>
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
                    
                    # EXTRACTION PREHEADER (Texte brut, 160 chars)
                    raw_text = soup.get_text(separator=" ", strip=True)
                    preheader_txt = raw_text[:160] + "..." if len(raw_text) > 160 else raw_text
                    # Echappement pour le HTML attribute
                    safe_preheader_attr = html.escape(preheader_txt, quote=True)

                    links = []
                    for a in soup.find_all('a', href=True):
                        txt = a.get_text(strip=True) or "[Image/Vide]"
                        links.append({'txt': txt[:50] + "..." if len(txt)>50 else txt, 'url': a['href']})
                    
                    links_html = "".join([f'<li><a href="{l["url"]}" target="_blank"><div class="link-txt">{l["txt"]}</div><div class="link-url">{l["url"]}</div></a></li>' for l in links])

                    # IMAGES LOCALES
                    img_counter = 0
                    for img in soup.find_all("img"):
                        src = img.get("src")
                        if not src or src.startswith("data:") or src.startswith("cid:"): continue
                        try:
                            if src.startswith("//"): src = "https:" + src
                            
                            ext = os.path.splitext(src.split('?')[0])[1]
                            if not ext or len(ext) > 5: ext = ".jpg"
                            
                            local_name = f"img_{img_counter}{ext}"
                            local_path = os.path.join(newsletter_path, local_name)

                            if not os.path.exists(local_path):
                                r = requests.get(src, headers=HEADERS, timeout=5)
                                if r.status_code == 200:
                                    if 'image' in r.headers.get('content-type', ''):
                                        real_ext = mimetypes.guess_extension(r.headers.get('content-type')) or ".jpg"
                                        local_name = f"img_{img_counter}{real_ext}"
                                        local_path = os.path.join(newsletter_path, local_name)
                                        with open(local_path, "wb") as f: f.write(r.content)
                            
                            img['src'] = local_name
                            img['loading'] = 'lazy'
                            if img.has_attr('srcset'): del img['srcset']
                            img_counter += 1
                        except: pass

                    # VIEWER
                    safe_html = json.dumps(str(soup))
                    nb_links = len(links)
                    date_arch_str = datetime.datetime.now().strftime('%Y-%m-%d')
                    
                    viewer_content = f"""
                    <!DOCTYPE html>
                    <html lang="fr">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <meta name="creation_date" content="{email_date_str}">
                        <meta name="sender" content="{sender_name}">
                        <meta name="archiving_date" content="{date_arch_str}">
                        <meta name="preheader" content="{safe_preheader_attr}">
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
                            
                            /* STYLE DU CONTENEUR */
                            .iframe-wrapper {{ 
                                width: 1000px; max-width: 95%; height: 90%;
                                transition: width 0.3s ease; 
                                background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border-radius: 4px;
                            }}
                            
                            iframe {{ width: 100%; height: 100%; border: none; display: block; border-radius: inherit; }}
                            
                            /* STYLE MOBILE */
                            body.mobile-mode .iframe-wrapper {{ 
                                width: 375px; height: 812px; 
                                max-height: 85vh; 
                                border: none; 
                                box-shadow: 0 10px 40px rgba(0,0,0,0.15);
                            }}
                            
                            .sidebar {{ position: fixed; top: 60px; right: -350px; width: 350px; height: calc(100vh - 60px); background: white; border-left: 1px solid #ddd; transition: right 0.3s; overflow-y: auto; z-index: 90; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; gap: 20px; }}
                            .sidebar.open {{ right: 0; }}
                            .sidebar-section {{ }}
                            .sidebar h3 {{ margin-top: 0; font-size: 16px; color: #333; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }}
                            
                            /* Métadonnées */
                            .meta-item {{ margin-bottom: 12px; font-size: 13px; color: #555; }}
                            .meta-label {{ font-weight: 600; display: block; margin-bottom: 3px; color: #333; }}
                            .meta-val {{ word-break: break-word; line-height: 1.4; }}
                            .preheader-box {{ background: #f8f9fa; padding: 10px; border-radius: 6px; border: 1px solid #eee; font-style: italic; color: #666; font-size: 12px; }}

                            /* Liste Liens */
                            .sidebar ul {{ list-style: none; padding: 0; margin: 0; }}
                            .sidebar li {{ margin-bottom: 15px; word-break: break-all; border-bottom: 1px solid #f5f5f5; padding-bottom: 10px; }}
                            .sidebar a {{ text-decoration: none; color: inherit; font-size: 12px; }}
                            .link-txt {{ font-weight: bold; color: #0070f3; margin-bottom: 4px; }}
                            .link-url {{ color: #666; }}
                            
                            /* DARK MODE */
                            body.dark-mode .main-view {{ background: #121212; }}
                            body.dark-mode .header {{ background: #1e1e1e; border-bottom-color: #333; }}
                            body.dark-mode .title {{ color: #e0e0e0; }}
                            body.dark-mode .btn {{ background: #2c2c2c; border-color: #444; color: #ccc; }}
                            body.dark-mode .btn.active {{ background: #0070f3; color: white; }}
                            
                            /* Ombre lumineuse plus marquée en dark mode */
                            body.dark-mode .iframe-wrapper {{ 
                                box-shadow: 0 0 25px rgba(255, 255, 255, 0.15); 
                                border: 1px solid #333;
                            }}
                            
                            body.dark-mode .sidebar {{ background: #1e1e1e; border-left-color: #333; }}
                            body.dark-mode .sidebar h3 {{ color: #fff; border-bottom-color: #333; }}
                            body.dark-mode .meta-label {{ color: #ccc; }}
                            body.dark-mode .meta-item {{ color: #aaa; }}
                            body.dark-mode .preheader-box {{ background: #252525; border-color: #333; color: #aaa; }}
                            body.dark-mode .link-txt {{ color: #4da3ff; }}
                            body.dark-mode .link-url {{ color: #aaa; }}
                        </style>
                    </head>
                    <body>
                        <header class="header">
                            <div class="title">{subject}</div>
                            <div class="controls">
                                <button class="btn" onclick="toggleLinks()" id="btn-links"><span>{ICON_INFO}</span>&nbsp;Infos</button>
                                <button class="btn" onclick="toggleMobile()" id="btn-mobile"><span>{ICON_MOBILE}</span>&nbsp;Mobile</button>
                                <button class="btn" onclick="toggleDark()" id="btn-dark"><span>{ICON_MOON}</span>&nbsp;Sombre</button>
                            </div>
                        </header>
                        
                        <div class="main-view">
                            <div class="iframe-wrapper">
                                <iframe id="emailFrame"></iframe>
                            </div>
                        </div>
                        
                        <div class="sidebar" id="sidebar">
                            <div class="sidebar-section">
                                <h3>{ICON_INFO} Métadonnées</h3>
                                <div class="meta-item">
                                    <span class="meta-label">📅 Date d'envoi</span>
                                    <span class="meta-val">{format_date_fr(email_date_str)}</span>
                                </div>
                                <div class="meta-item">
                                    <span class="meta-label">🗄️ Date d'archivage</span>
                                    <span class="meta-val">{format_date_fr(date_arch_str)}</span>
                                </div>
                                <div class="meta-item">
                                    <span class="meta-label">👀 Pré-header (Aperçu)</span>
                                    <div class="preheader-box">{safe_preheader_attr}</div>
                                </div>
                            </div>

                            <div class="sidebar-section">
                                <h3>{ICON_LINK} Liens détectés ({nb_links})</h3>
                                <ul>{links_html}</ul>
                            </div>
                        </div>

                        <script>
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
                                body {{ 
                                    margin: 0; padding: 0; font-family: Roboto, Helvetica, Arial, sans-serif;
                                    color: #222; line-height: 1.5; overflow-wrap: break-word; 
                                }}
                                table {{ border-spacing: 0; border-collapse: collapse; }}
                                img {{ height: auto !important; vertical-align: middle; border: 0; }}
                                img[style*="display: block"], img[style*="display:block"] {{ margin-left: auto !important; margin-right: auto !important; }}
                                a, .link-text {{ color: #1a0dab; }}
                                html.dark-mode-internal {{ filter: invert(1) hue-rotate(180deg); }}
                                html.dark-mode-internal img, html.dark-mode-internal video, html.dark-mode-internal [style*="background-image"] {{ filter: invert(1) hue-rotate(180deg); }}
                                @media screen and (max-width: 600px) {{
                                    table, tbody, tr, td {{ width: 100% !important; min-width: 0 !important; box-sizing: border-box !important; height: auto !important; }}
                                    div[style*="width"] {{ width: 100% !important; max-width: 100% !important; }}
                                    img {{ width: auto !important; max-width: 100% !important; }}
                                }}
                            `;
                            frame.contentDocument.head.appendChild(style);

                            function toggleMobile() {{
                                document.body.classList.toggle('mobile-mode');
                                document.getElementById('btn-mobile').classList.toggle('active');
                            }}
                            
                            function toggleDark() {{
                                document.body.classList.toggle('dark-mode');
                                document.getElementById('btn-dark').classList.toggle('active');
                                if(frame.contentDocument.documentElement) {{
                                    frame.contentDocument.documentElement.classList.toggle('dark-mode-internal');
                                }}
                            }}
                            
                            function toggleLinks() {{
                                document.getElementById('sidebar').classList.toggle('open');
                                document.getElementById('btn-links').classList.toggle('active');
                            }}
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