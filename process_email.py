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

# --- CONFIGURATION ---
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]
TARGET_LABEL = "Github/archive-newsletters"
OUTPUT_FOLDER = "docs"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def clean_subject_prefixes(subject):
    if not subject: return "Sans titre"
    pattern = r'^\s*\[?(?:Fwd|Fw|Tr|Re|Aw|Wg)\s*:\s*\]?\s*'
    cleaned = subject
    while re.match(pattern, cleaned, re.IGNORECASE):
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def get_deterministic_id(subject):
    if not subject: subject = "sans_titre"
    hash_object = hashlib.md5(subject.encode('utf-8', errors='ignore'))
    return hash_object.hexdigest()[:10]

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

def get_page_metadata(filepath):
    title = "Sans titre"
    date_str = None
    sender = "Expéditeur Inconnu"
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            meta_date = soup.find("meta", attrs={"name": "creation_date"})
            if meta_date and meta_date.get("content"):
                date_str = meta_date["content"]
            meta_sender = soup.find("meta", attrs={"name": "sender"})
            if meta_sender and meta_sender.get("content"):
                sender = meta_sender["content"]
    except Exception:
        pass
    if not date_str:
        timestamp = os.path.getmtime(filepath)
        date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    return title, date_str, sender

def clean_output_folder():
    if os.path.exists(OUTPUT_FOLDER):
        for item in os.listdir(OUTPUT_FOLDER):
            item_path = os.path.join(OUTPUT_FOLDER, item)
            if item.startswith('.') or item == "CNAME":
                continue
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            except Exception as e:
                print(f"Warning nettoyage: {e}")
    else:
        os.makedirs(OUTPUT_FOLDER)

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

        full_title, date_str, sender = get_page_metadata(index_file_path)
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            display_date = date_obj.strftime('%d/%m/%Y')
            sort_key = date_str
        except:
            display_date = date_str
            sort_key = date_str

        pages_data.append({
            "folder": folder_name,
            "title": full_title,
            "sender": sender,
            "date": display_date,
            "sort_key": sort_key
        })

    pages_data.sort(key=lambda x: x["sort_key"], reverse=True)

    links_html = ""
    for page in pages_data:
        links_html += f'''
        <li>
            <a href="{page['folder']}/index.html" class="item-link">
                <div class="info-col">
                    <span class="sender">{page['sender']}</span>
                    <span class="title">{page['title']}</span>
                </div>
                <span class="date">{page['date']}</span>
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
                --toggle-icon: "🌑";
            }}
            [data-theme="dark"] {{
                --bg-body: #121212; --bg-card: #1e1e1e; --text-main: #e0e0e0; --text-muted: #a0a0a0; --text-light: #666666;
                --border-color: #333333; --accent-color: #4da3ff; --hover-bg: #252525; --input-bg: #252525; --shadow: rgba(0,0,0,0.3);
                --toggle-icon: "☀️";
            }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 0; padding: 20px; display: flex; flex-direction: column; min-height: 100vh; box-sizing: border-box; transition: background-color 0.3s, color 0.3s; }}
            .container {{ max-width: 800px; width: 100%; margin: 0 auto; background: var(--bg-card); padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px var(--shadow); flex: 1; position: relative; }}
            .header-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 2px solid var(--border-color); padding-bottom: 20px; }}
            h1 {{ text-align: center; color: var(--text-main); margin: 0; font-size: 1.8rem; flex-grow: 1; }}
            
            #theme-toggle {{ background: none; border: 1px solid var(--border-color); border-radius: 50%; width: 40px; height: 40px; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }}
            #theme-toggle:hover {{ background-color: var(--hover-bg); border-color: var(--accent-color); }}
            #theme-toggle::after {{ content: var(--toggle-icon); }}
            
            #searchInput {{ width: 100%; padding: 12px 20px; margin-bottom: 25px; box-sizing: border-box; border: 2px solid var(--border-color); border-radius: 8px; font-size: 16px; background-color: var(--input-bg); color: var(--text-main); transition: border-color 0.3s; }}
            #searchInput:focus {{ border-color: var(--accent-color); outline: none; }}
            
            ul {{ list-style: none; padding: 0; margin: 0; border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }}
            li {{ border-bottom: 1px solid var(--border-color); margin: 0; }}
            li:last-child {{ border-bottom: none; }}
            
            a.item-link {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; background: var(--bg-card); text-decoration: none; color: var(--text-main); transition: background 0.1s ease; }}
            a.item-link:hover {{ background-color: var(--hover-bg); }}
            
            .info-col {{ display: flex; flex-direction: column; flex: 1; min-width: 0; margin-right: 15px; }}
            .sender {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-light); margin-bottom: 4px; font-weight: 600; }}
            .title {{ font-weight: 500; font-size: 1rem; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .date {{ font-size: 0.85rem; color: var(--text-muted); white-space: nowrap; flex-shrink: 0; font-variant-numeric: tabular-nums; }}
            
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
                <button id="theme-toggle" title="Changer le thème"></button>
            </div>
            <input type="text" id="searchInput" onkeyup="filterList()" placeholder="Rechercher par titre, expéditeur ou date...">
            <ul id="newsList">
                {links_html}
            </ul>
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

        function filterList() {{
            var input, filter, ul, li, a, i, txtValue;
            input = document.getElementById('searchInput');
            filter = input.value.toUpperCase();
            ul = document.getElementById("newsList");
            li = ul.getElementsByTagName('li');
            for (i = 0; i < li.length; i++) {{
                a = li[i].getElementsByTagName("a")[0];
                txtValue = a.textContent || a.innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {{ li[i].style.display = ""; }} else {{ li[i].style.display = "none"; }}
            }}
        }}
        </script>
    </body>
    </html>
    """
    with open(f"{OUTPUT_FOLDER}/index.html", "w", encoding='utf-8') as f:
        f.write(index_content)

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

def process_emails():
    try:
        clean_output_folder()
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
            print(f"{len(email_ids)} emails trouvés.")

            for num in email_ids:
                try:
                    status, msg_data = mail.fetch(num, '(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE FROM)])')
                    msg_header = email.message_from_bytes(msg_data[0][1])
                    
                    raw_subject = get_decoded_email_subject(msg_header)
                    subject = clean_subject_prefixes(raw_subject)
                    email_date_str = get_email_date(msg_header)
                    sender_name = get_clean_sender(msg_header)
                    
                    folder_id = get_deterministic_id(subject)
                    newsletter_path = os.path.join(OUTPUT_FOLDER, folder_id)
                    print(f"Traitement : {subject[:30]}... ({sender_name})")
                    
                    status, msg_data = mail.fetch(num, "(RFC822)")
                    msg = email.message_from_bytes(msg_data[0][1])
                    os.makedirs(newsletter_path, exist_ok=True)

                    html_content = ""
                    for part in msg.walk():
                        if part.get_content_type() == "text/html":
                            payload = part.get_payload(decode=True)
                            charset = part.get_content_charset() or 'utf-8'
                            html_content = payload.decode(charset, errors="ignore")
                            break
                    if not html_content and not msg.is_multipart():
                        payload = msg.get_payload(decode=True)
                        charset = msg.get_content_charset() or 'utf-8'
                        html_content = payload.decode(charset, errors="ignore")
                    if not html_content: continue

                    soup = BeautifulSoup(html_content, "html.parser")
                    for s in soup(["script", "iframe", "object"]): s.extract()

                    # Nettoyage des transferts
                    split_keywords = ["Forwarded message", "Message transféré"]
                    found_split = False
                    for div in soup.find_all("div"):
                        text = div.get_text()
                        if any(k in text for k in split_keywords) and "-----" in text:
                            real_content = []
                            for sibling in div.next_siblings: real_content.append(sibling)
                            if soup.body:
                                soup.body.clear()
                                for item in real_content:
                                    if item: soup.body.append(item)
                            found_split = True
                            break
                    if not found_split:
                        quote = soup.find(class_="gmail_quote")
                        if quote:
                            soup.body.clear()
                            soup.body.append(quote)
                            for attr in soup.find_all(class_="gmail_attr"): attr.decompose()

                    if not soup.body:
                        new_body = soup.new_tag("body")
                        new_body.extend(soup.contents)
                        soup.append(new_body)

                    # --- INJECTION UI PREVIEW (TOOLBAR & WRAPPER) ---
                    
                    # 1. CSS/JS Injection
                    style_tag = soup.new_tag("style")
                    style_tag.string = """
                        /* Reset de base */
                        body { margin: 0; padding: 0; background-color: #f4f4f4; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
                        
                        /* TOOLBAR UI */
                        #preview-toolbar {
                            position: fixed; top: 0; left: 0; right: 0;
                            height: 60px; background: #1a1a1a; color: white;
                            display: flex; align-items: center; justify-content: space-between;
                            padding: 0 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                            z-index: 999999;
                        }
                        #preview-toolbar h1 { 
                            margin: 0; font-size: 16px; font-weight: 600; 
                            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; 
                            max-width: 400px; color: #e0e0e0;
                        }
                        
                        .toolbar-actions { display: flex; gap: 12px; }
                        
                        /* BOUTONS STYLISÉS */
                        .tool-btn {
                            background: #333; border: 1px solid #555; color: #ddd;
                            padding: 8px 14px; border-radius: 6px; cursor: pointer;
                            font-size: 13px; font-weight: 500;
                            display: flex; align-items: center; gap: 6px;
                            transition: all 0.2s ease;
                        }
                        .tool-btn:hover { background: #444; border-color: #777; color: #fff; }
                        .tool-btn.active { 
                            background: #0070f3; border-color: #0070f3; color: white; 
                            box-shadow: 0 0 8px rgba(0, 112, 243, 0.4);
                        }
                        
                        /* EMAIL CONTAINER */
                        #email-wrapper {
                            margin-top: 60px; /* Espace pour la toolbar */
                            width: 100%;
                            min-height: calc(100vh - 60px);
                            display: flex; justify-content: center;
                            padding: 40px 20px;
                            box-sizing: border-box;
                            transition: background-color 0.3s;
                        }
                        
                        #email-content {
                            width: 100%; max-width: 800px;
                            background: #ffffff;
                            box-shadow: 0 5px 30px rgba(0,0,0,0.1);
                            transition: all 0.3s ease;
                            /* Isolation du CSS de l'email */
                            border-radius: 2px;
                        }

                        /* --- MOBILE MODE LOGIC --- */
                        body.mobile-active #email-content {
                            max-width: 375px !important; /* Largeur iPhone SE */
                            border: 8px solid #333;
                            border-radius: 30px;
                            overflow: hidden;
                            box-shadow: 0 20px 50px rgba(0,0,0,0.3);
                        }
                        
                        /* Force le redimensionnement des vieux mails en mode mobile */
                        body.mobile-active table, 
                        body.mobile-active img {
                            max-width: 100% !important;
                            height: auto !important;
                            width: auto !important;
                        }

                        /* --- DARK MODE LOGIC (SMART INVERT) --- */
                        body.dark-active #email-wrapper { background-color: #121212; }
                        body.dark-active #email-content {
                            /* Inversion intelligente : on inverse tout le conteneur */
                            filter: invert(1) hue-rotate(180deg);
                        }
                        /* Et on RE-inverse les images et vidéos pour qu'elles redeviennent normales */
                        body.dark-active img, 
                        body.dark-active video, 
                        body.dark-active iframe {
                            filter: invert(1) hue-rotate(180deg) !important;
                        }
                    """
                    if soup.head: soup.head.append(style_tag)
                    else:
                        new_head = soup.new_tag("head")
                        new_head.append(style_tag)
                        soup.insert(0, new_head)

                    # 2. Script JS Injection
                    script_tag = soup.new_tag("script")
                    script_tag.string = """
                        function toggleMobile() {
                            document.body.classList.toggle('mobile-active');
                            const btn = document.getElementById('btn-mobile');
                            btn.classList.toggle('active');
                        }
                        function toggleDark() {
                            document.body.classList.toggle('dark-active');
                            const btn = document.getElementById('btn-dark');
                            btn.classList.toggle('active');
                        }
                    """
                    soup.body.append(script_tag)

                    # 3. Création de la Toolbar (SANS le bouton Retour)
                    toolbar_html = BeautifulSoup(f"""
                    <div id="preview-toolbar">
                        <h1>{subject}</h1>
                        <div class="toolbar-actions">
                            <button id="btn-mobile" class="tool-btn" onclick="toggleMobile()">📱 Mobile</button>
                            <button id="btn-dark" class="tool-btn" onclick="toggleDark()">🌙 Sombre</button>
                        </div>
                    </div>
                    """, 'html.parser')

                    # 4. Wrappings
                    wrapper_div = soup.new_tag("div", id="email-wrapper")
                    content_div = soup.new_tag("div", id="email-content")
                    
                    to_move = []
                    for child in soup.body.contents:
                        if child != script_tag and child != toolbar_html:
                            to_move.append(child)
                    
                    for child in to_move:
                        content_div.append(child)
                    
                    wrapper_div.append(content_div)
                    
                    soup.body.clear()
                    soup.body.append(toolbar_html)
                    soup.body.append(wrapper_div)
                    soup.body.append(script_tag)

                    # Méta-données
                    meta_date = soup.new_tag("meta", attrs={"name": "creation_date", "content": email_date_str})
                    meta_sender = soup.new_tag("meta", attrs={"name": "sender", "content": sender_name})
                    if soup.head: 
                        soup.head.append(meta_date)
                        soup.head.append(meta_sender)

                    if soup.title: soup.title.string = subject
                    else:
                        new_title = soup.new_tag('title')
                        new_title.string = subject
                        if soup.head: soup.head.append(new_title)

                    # Images (Lazy Loading)
                    img_counter = 0
                    for img in soup.find_all("img"):
                        src = img.get("src")
                        if not src or src.startswith("data:") or src.startswith("cid:"): continue
                        try:
                            if src.startswith("//"): src = "https:" + src
                            response = requests.get(src, headers=HEADERS, timeout=10)
                            if response.status_code == 200:
                                content_type = response.headers.get('content-type')
                                ext = mimetypes.guess_extension(content_type) or ".jpg"
                                img_name = f"img_{img_counter}{ext}"
                                img_path = os.path.join(newsletter_path, img_name)
                                with open(img_path, "wb") as f: f.write(response.content)
                                img['src'] = img_name
                                img['loading'] = 'lazy'
                                if img.has_attr('srcset'): del img['srcset']
                                img_counter += 1
                        except Exception: pass

                    filename = os.path.join(newsletter_path, "index.html")
                    with open(filename, "w", encoding='utf-8') as f:
                        f.write(str(soup))
                except Exception as e_mail:
                    print(f"Erreur email {num}: {e_mail}")
                    continue
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
