# optimize.py
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
from generate_newsletter_viewer import create_viewer_html

# --- CONFIGURATION ---
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
TARGET_LABEL = "Github/archive-newsletters"
OUTPUT_FOLDER = "docs"
BATCH_SIZE = 100

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- ICONS ---
ICON_MOON = '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>'
ICON_SUN = '<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>'

# --- UTILS ---

def clean_subject(subject):
    if not subject: return "Sans titre"
    pattern = r'^\s*\[?(?:Fwd|Fw|Tr|Re|Aw|Wg)\s*:\s*\]?\s*'
    cleaned = subject
    while re.match(pattern, cleaned, re.IGNORECASE):
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def get_id(subject):
    if not subject: subject = "sans_titre"
    hash_object = hashlib.sha256(subject.encode('utf-8', errors='ignore'))
    return hash_object.hexdigest()[:12]

def get_email_date(msg):
    date_header = msg["Date"]
    if date_header:
        try:
            return parsedate_to_datetime(date_header).strftime('%Y-%m-%d')
        except Exception:
            pass
    return datetime.datetime.now().strftime('%Y-%m-%d')

def get_sender(msg):
    from_header = msg["From"]
    if not from_header: return "Inconnu"
    try:
        decoded = decode_header(from_header)
        full_sender = "".join([part.decode(encoding or "utf-8") if isinstance(part, bytes) else part for part, encoding in decoded])
        realname, email_addr = parseaddr(full_sender)
        return realname.strip() if realname else email_addr.strip()
    except Exception:
        return "Expéditeur Inconnu"

def get_subject(msg):
    subject_header = msg["Subject"]
    if not subject_header: return "Sans Titre"
    try:
        decoded = decode_header(subject_header)
        full_subject = "".join([part.decode(encoding or "utf-8", errors="ignore") if isinstance(part, bytes) else part for part, encoding in decoded])
        return full_subject.strip()
    except Exception:
        return "Sans Titre"

def get_html_payload(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return part.get_payload(decode=True), part.get_content_charset()
    elif msg.get_content_type() == "text/html":
        return msg.get_payload(decode=True), msg.get_content_charset()
    return None, None

def decode_html(payload, charset):
    if not payload: return ""
    encodings = [charset, 'utf-8', 'windows-1252', 'iso-8859-1']
    for enc in encodings:
        if not enc: continue
        try:
            return payload.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return payload.decode('utf-8', errors='ignore')

def process_html_content(html_content, newsletter_path):
    soup = BeautifulSoup(html_content, "html.parser")
    
    for tag in soup(["script", "style", "iframe", "object", "meta", "link"]):
        tag.extract()

    links = [{'txt': a.get_text(strip=True)[:80] or "[Lien]", 'url': a['href']} for a in soup.find_all('a', href=True)]

    img_counter = 0
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src or src.startswith(("data:", "cid:")): continue
        try:
            if src.startswith("//"): src = "https:" + src
            
            ext = os.path.splitext(src.split('?')[0])[1] or ".jpg"
            if len(ext) > 5: ext = ".jpg"
            
            local_name = f"img_{img_counter}{ext}"
            local_path = os.path.join(newsletter_path, local_name)

            if not os.path.exists(local_path):
                r = requests.get(src, headers=HEADERS, stream=True, timeout=10)
                if r.status_code == 200:
                    with open(local_path, "wb") as f:
                        shutil.copyfileobj(r.raw, f)
            
            img['src'] = local_name
            img['loading'] = 'lazy'
            if 'srcset' in img.attrs: del img['srcset']
            img_counter += 1
        except Exception as e:
            print(f"  > Erreur image {src}: {e}")

    return soup, links

def process_emails():
    if not all([GMAIL_USER, GMAIL_PASSWORD]):
        print("ERREUR: GMAIL_USER et GMAIL_PASSWORD doivent être définis.")
        return

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    try:
        print("Connexion au serveur Gmail...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select(f'"{TARGET_LABEL}"')
        
        status, messages = mail.search(None, 'ALL')
        if not messages[0]:
            print("Aucun email trouvé.")
            return
            
        email_ids = messages[0].split()
        print(f"{len(email_ids)} emails trouvés.")

        remote_ids = set()
        for num in email_ids:
            try:
                _, msg_data = mail.fetch(num, '(BODY.PEEK[HEADER.FIELDS (SUBJECT)])')
                msg_header = email.message_from_bytes(msg_data[0][1])
                subject = clean_subject(get_subject(msg_header))
                remote_ids.add(get_id(subject))
            except Exception: continue

        local_folders = set(f.name for f in os.scandir(OUTPUT_FOLDER) if f.is_dir())
        to_delete = local_folders - remote_ids
        for folder_id in to_delete:
            shutil.rmtree(os.path.join(OUTPUT_FOLDER, folder_id))
            print(f"Supprimé (Synchro): {folder_id}")

        for num in email_ids[:BATCH_SIZE]:
            try:
                _, msg_data = mail.fetch(num, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                
                subject = clean_subject(get_subject(msg))
                sender = get_sender(msg)
                email_date = get_email_date(msg)
                folder_id = get_id(subject)
                
                newsletter_path = os.path.join(OUTPUT_FOLDER, folder_id)
                if os.path.exists(os.path.join(newsletter_path, "index.html")):
                    continue

                print(f"Traitement: {subject}")
                os.makedirs(newsletter_path, exist_ok=True)

                payload, charset = get_html_payload(msg)
                if not payload:
                    print("  > Ignoré (Pas de HTML)")
                    continue
                
                html_content = decode_html(payload, charset)
                processed_soup, links = process_html_content(html_content, newsletter_path)
                
                viewer_html = create_viewer_html(subject, sender, email_date, processed_soup, links)
                
                with open(os.path.join(newsletter_path, "index.html"), "w", encoding='utf-8') as f:
                    f.write(viewer_html)

            except Exception as e:
                print(f"Erreur traitement email ID {num.decode()}: {e}")

        mail.close()
        mail.logout()
        print("Déconnexion.")
        generate_index()
        
    except Exception as e:
        print(f"Erreur critique: {e}")

def get_page_metadata(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            title = soup.title.string.strip() if soup.title else "Sans titre"
            date_str = soup.find("meta", attrs={"name": "creation_date"})["content"]
            sender = soup.find("meta", attrs={"name": "sender"})["content"]
            archiving_date = soup.find("meta", attrs={"name": "archiving_date"})["content"]
            return title, date_str, sender, archiving_date
    except Exception:
        date_str = datetime.datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d')
        return "Titre inconnu", date_str, "Expéditeur inconnu", date_str

def format_date_fr(date_iso):
    try:
        return datetime.datetime.strptime(date_iso, '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        return date_iso

def generate_index():
    print("Génération de l'index principal...")
    subfolders = [f.path for f in os.scandir(OUTPUT_FOLDER) if f.is_dir()]
    pages_data = []
    
    for folder in subfolders:
        index_file = os.path.join(folder, "index.html")
        if not os.path.exists(index_file): continue
        title, date_rec, sender, date_arch = get_page_metadata(index_file)
        pages_data.append({
            "folder": os.path.basename(folder),
            "title": title, "sender": sender,
            "date_rec": format_date_fr(date_rec),
            "date_arch": format_date_fr(date_arch),
            "sort_key": date_rec
        })

    pages_data.sort(key=lambda x: x["sort_key"], reverse=True)

    links_html = "".join([f'''
        <li class="news-item">
            <a href="{p['folder']}/index.html" class="item-link">
                <div class="info-col">
                    <span class="sender">{p['sender']}</span>
                    <span class="title">{p['title']}</span>
                </div>
                <div class="date-col">
                    <span class="date">Reçu le {p['date_rec']}</span>
                    <span class="date-arch">Archivé le {p['date_arch']}</span>
                </div>
            </a>
        </li>''' for p in pages_data])

    index_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Archives Newsletters</title>
        <meta name="robots" content="noindex, nofollow">
        <style>
            :root {{
                --bg-body: #f6f9fc; --bg-card: #ffffff; --text-main: #333333; --text-muted: #666666;
                --border-color: #eaeaea; --accent-color: #0070f3; --hover-bg: #f8f9fa;
            }}
            [data-theme="dark"] {{
                --bg-body: #121212; --bg-card: #1e1e1e; --text-main: #e0e0e0; --text-muted: #a0a0a0;
                --border-color: #333333; --accent-color: #4da3ff; --hover-bg: #252525;
            }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background: var(--bg-card); padding: 40px; border-radius: 12px; }}
            .header-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
            h1 {{ margin: 0; font-size: 1.8rem; }}
            #theme-toggle {{ background: none; border: 1px solid var(--border-color); border-radius: 50%; width: 40px; height: 40px; cursor: pointer; display: flex; align-items: center; justify-content: center; }}
            .icon-moon {{ display: block; }} .icon-sun {{ display: none; }}
            [data-theme="dark"] .icon-moon {{ display: none; }} [data-theme="dark"] .icon-sun {{ display: block; }}
            #searchInput {{ width: 100%; padding: 12px; margin-bottom: 25px; box-sizing: border-box; border: 2px solid var(--border-color); border-radius: 8px; font-size: 16px; }}
            ul {{ list-style: none; padding: 0; margin: 0; }}
            li.news-item {{ border-bottom: 1px solid var(--border-color); }}
            li:last-child {{ border-bottom: none; }}
            a.item-link {{ display: flex; justify-content: space-between; align-items: center; padding: 16px; text-decoration: none; color: var(--text-main); transition: background 0.1s; }}
            a.item-link:hover {{ background-color: var(--hover-bg); }}
            .info-col {{ flex: 1; min-width: 0; }}
            .sender {{ font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px; font-weight: 600; }}
            .title {{ font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .date-col {{ text-align: right; margin-left: 15px; font-size: 0.85rem; color: var(--text-muted); }}
            .date-arch {{ font-size: 0.7rem; color: #999; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header-row">
                <h1>📬 Archives Newsletters</h1>
                <button id="theme-toggle" title="Changer le thème">
                    <span class="icon-moon">{ICON_MOON}</span>
                    <span class="icon-sun">{ICON_SUN}</span>
                </button>
            </div>
            <input type="text" id="searchInput" onkeyup="filterList()" placeholder="Rechercher...">
            <ul id="newsList">{links_html}</ul>
        </div>
        <script>
            const toggle = document.getElementById('theme-toggle');
            const root = document.documentElement;
            if (localStorage.getItem('theme') === 'dark') root.setAttribute('data-theme', 'dark');
            toggle.addEventListener('click', () => {{
                const newTheme = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
                root.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);
            }});
            function filterList() {{
                const filter = document.getElementById('searchInput').value.toUpperCase();
                const items = document.querySelectorAll('#newsList .news-item');
                items.forEach(item => {{
                    item.style.display = item.textContent.toUpperCase().includes(filter) ? "" : "none";
                }});
            }}
        </script>
    </body>
    </html>
    """
    with open(f"{OUTPUT_FOLDER}/index.html", "w", encoding='utf-8') as f:
        f.write(index_content)
    print("Index principal généré.")

if __name__ == "__main__":
    process_emails()
