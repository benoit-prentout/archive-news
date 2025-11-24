import imaplib
import email
import os
import hashlib
import requests
import re
from email.header import decode_header
from bs4 import BeautifulSoup
from datetime import datetime

# --- Configuration ---
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
DOCS_DIR = "docs"
IMAP_SERVER = "imap.gmail.com"
SEARCH_CRITERIA = '(LABEL "Github/archive-newsletters")' # Ensure this matches your Gmail Label

def connect_imap():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(GMAIL_USER, GMAIL_PASSWORD)
    return mail

def clean_filename(s):
    return "".join(c for c in s if c.isalnum() or c in (' ', '-', '_')).strip()

def get_body_content(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            if ctype == 'text/html' and 'attachment' not in cdispo:
                return part.get_payload(decode=True).decode('utf-8', errors='ignore')
    else:
        return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    return ""

def wrap_email_html(title, date_str, content):
    """
    Wraps the raw email content in a responsive, centered viewer.
    """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="date" content="{date_str}">
    <title>{title}</title>
    <style>
        body {{
            background-color: #f0f2f5;
            margin: 0;
            padding: 0;
            font-family: sans-serif;
        }}
        .navbar {{
            background: #2c3e50;
            color: white;
            padding: 15px;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .navbar a {{
            color: white;
            text-decoration: none;
            font-weight: bold;
            font-size: 16px;
        }}
        .email-container {{
            max-width: 800px;
            margin: 30px auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            overflow: hidden;
        }}
        .email-content {{
            padding: 20px;
            /* Force images to not overflow */
        }}
        .email-content img {{
            max-width: 100% !important;
            height: auto !important;
        }}
        /* Reset common email table styles that break layout */
        table {{ max-width: 100% !important; }}
    </style>
</head>
<body>
    <div class="navbar">
        <a href="../index.html">← Back to Archive</a>
    </div>
    <div class="email-container">
        <!-- Original Email Content Start -->
        <div class="email-content">
            {content}
        </div>
        <!-- Original Email Content End -->
    </div>
</body>
</html>
"""

def save_email(subject, date_str, html_content, message_id):
    # Create deterministic folder name
    folder_name = hashlib.md5(message_id.encode()).hexdigest()[:12]
    folder_path = os.path.join(DOCS_DIR, folder_name)
    
    if os.path.exists(folder_path):
        print(f"Skipping already archived: {subject}")
        return

    os.makedirs(folder_path, exist_ok=True)
    
    # Process Images (Download and replace links)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Sanitize: Extract only body content if full HTML is present
    if soup.body:
        body_content = soup.body.decode_contents()
    else:
        body_content = str(soup)

    # 2. Download Images
    images_dir = os.path.join(folder_path, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    for i, img in enumerate(soup.find_all('img')):
        if img.get('src') and img['src'].startswith('http'):
            try:
                img_url = img['src']
                ext = img_url.split('.')[-1].split('?')[0]
                if len(ext) > 4: ext = 'jpg'
                
                img_name = f"img_{i}.{ext}"
                local_path = os.path.join(images_dir, img_name)
                
                # Download
                response = requests.get(img_url, timeout=10)
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    # Update HTML src to relative path
                    img['src'] = f"./images/{img_name}"
            except Exception as e:
                print(f"Failed to download image: {e}")

    # 3. Wrap and Save
    final_html = wrap_email_html(subject, date_str, str(soup))
    
    with open(os.path.join(folder_path, "index.html"), "w", encoding="utf-8") as f:
        f.write(final_html)
    
    print(f"Archived: {subject}")

def main():
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)

    mail = connect_imap()
    mail.select('inbox')
    
    # Search for emails
    status, messages = mail.search(None, SEARCH_CRITERIA)
    email_ids = messages[0].split()

    print(f"Found {len(email_ids)} emails to process...")

    for e_id in email_ids:
        res, msg_data = mail.fetch(e_id, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # Decode Subject
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                # Get Date
                date_tuple = email.utils.parsedate_tz(msg['Date'])
                if date_tuple:
                    local_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                    date_str = local_date.strftime("%Y-%m-%d")
                else:
                    date_str = datetime.now().strftime("%Y-%m-%d")

                # Get Body
                html_body = get_body_content(msg)
                
                if html_body:
                    # Message-ID for unique folder generation
                    msg_id = msg.get("Message-ID") or subject + date_str
                    save_email(subject, date_str, html_body, msg_id)
    
    mail.close()
    mail.logout()

if __name__ == "__main__":
    main()
