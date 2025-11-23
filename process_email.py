import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import os
import re
import mimetypes
import requests
import datetime
import uuid

# --- CONFIGURATION ---
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]
TARGET_LABEL = "Netlify-News"
OUTPUT_FOLDER = "docs"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_page_title(filepath):
    """Ouvre un fichier HTML et récupère son titre complet"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            if soup.title and soup.title.string:
                return soup.title.string.strip()
    except Exception:
        pass
    return "Sans titre"

def generate_index():
    print("Génération du sommaire sécurisé...")
    if not os.path.exists(OUTPUT_FOLDER):
        return
        
    files = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".html") and f != "index.html"]
    # Tri par date de modification
    files.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_FOLDER, x)), reverse=True)

    links_html = ""
    for f in files:
        filepath = os.path.join(OUTPUT_FOLDER, f)
        
        # On récupère le VRAI titre complet depuis le contenu du fichier
        full_title = get_page_title(filepath)
        
        timestamp = os.path.getmtime(filepath)
        date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y')

        links_html += f'''
        <li>
            <a href="{f}">
                <div class="link-content">
                    <span class="icon">📧</span>
                    <span class="title">{full_title}</span>
                </div>
                <span class="date">{date_str}</span>
            </a>
        </li>
        '''

    index_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Archives Newsletters</title>
        <meta name="robots" content="noindex, nofollow">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f6f9fc; margin: 0; padding: 20px; color: #333; }}
            .container {{ max-width: 800px; margin: 40px auto; background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            h1 {{ text-align: center; color: #1a1a1a; margin-bottom: 40px; font-size: 1.8rem; border-bottom: 2px solid #f0f0f0; padding-bottom: 20px; }}
            ul {{ list-style: none; padding: 0; }}
            li {{ margin-bottom: 12px; }}
            a {{ display: flex; justify-content: space-between; align-items: center; padding: 18px 25px; background: #fff; border: 1px solid #eaeaea; border-radius: 10px; text-decoration: none; color: #2c3e50; transition: all 0.2s ease; }}
            a:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-color: #0070f3; color: #0070f3; }}
            .link-content {{ display: flex; align-items: center; overflow: hidden; }}
            .icon {{ font-size: 1.2rem; margin-right: 15px; flex-shrink: 0; }}
            .title {{ font-weight: 600; font-size: 1.05rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .date {{ font-size: 0.85rem; color: #888; background: #f4f4f4; padding: 5px 10px; border-radius: 20px; margin-left: 10px; flex-shrink: 0; }}
            a:hover .date {{ background: #e8f0fe; color: #0070f3; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📬 Mes Newsletters</h1>
            <ul>
                {links_html}
            </ul>
        </div>
    </body>
    </html>
    """
    
    with open(f"{OUTPUT_FOLDER}/index.html", "w", encoding='utf-8') as f:
        f.write(index_content)
    print("Sommaire généré.")

def process_emails():
    try:
        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)

        print("Connexion au serveur...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select(TARGET_LABEL)
        
        status, messages = mail.search(None, 'UNSEEN')
        
        if messages[0]:
            for num in messages[0].split():
                status, msg_data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                
                # --- SUJET COMPLET ---
                subject_header = msg["Subject"]
                if subject_header:
                    decoded_list = decode_header(subject_header)
                    subject, encoding = decoded_list[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                else:
                    subject = "Sans Titre"
                
                # Génération d'un nom de fichier aléatoire (UUID) pour l'obfuscation
                random_filename = str(uuid.uuid4().hex)[:10] # ex: a4e12b9f.html
                print(f"Traitement de : {subject} -> {random_filename}.html")

                # Extraction HTML
                html_content = ""
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    if content_type == "text/html" and "attachment" not in content_disposition:
                        html_content = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
                        break
                
                if not html_content and not msg.is_multipart():
                    html_content = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8')

                if not html_content: continue

                # Nettoyage et Images
                soup = BeautifulSoup(html_content, "html.parser")
                for s in soup(["script", "iframe", "object"]):
                    s.extract()
                
                # --- IMPORTANT : On force l'insertion du titre complet dans le HTML ---
                # Cela permet à generate_index() de le retrouver plus tard
                if soup.title:
                    soup.title.string = subject
                else:
                    new_title = soup.new_tag('title')
                    new_title.string = subject
                    if soup.head:
                        soup.head.append(new_title)
                    else:
                        new_head = soup.new_tag('head')
                        new_head.append(new_title)
                        soup.insert(0, new_head)

                # Téléchargement Images
                img_counter = 0
                for img in soup.find_all("img"):
                    src = img.get("src")
                    if not src or src.startswith("data:") or src.startswith("cid:"):
                        continue
                    try:
                        if src.startswith("//"): src = "https:" + src
                        response = requests.get(src, headers=HEADERS, timeout=10)
                        if response.status_code == 200:
                            content_type = response.headers.get('content-type')
                            ext = mimetypes.guess_extension(content_type) or ".jpg"
                            # Nom d'image lié au fichier aléatoire
                            img_name = f"{random_filename}_img_{img_counter}{ext}"
                            img_path = os.path.join(OUTPUT_FOLDER, img_name)
                            with open(img_path, "wb") as f:
                                f.write(response.content)
                            img['src'] = img_name
                            if img.has_attr('srcset'): del img['srcset']
                            img_counter += 1
                    except Exception: pass

                filename = f"{OUTPUT_FOLDER}/{random_filename}.html"
                with open(filename, "w", encoding='utf-8') as f:
                    f.write(str(soup))
                    
            print("Mails traités.")
        else:
            print("Aucun nouveau mail.")

        mail.close()
        mail.logout()
        generate_index()

    except Exception as e:
        print(f"Erreur: {e}")
        raise e

if __name__ == "__main__":
    process_emails()
