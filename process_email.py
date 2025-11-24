import imaplib
import email
import os
import hashlib
import requests
import re
import sys
from email.header import decode_header
from datetime import datetime
from bs4 import BeautifulSoup

# --- Configuration ---
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
DOCS_DIR = "docs"
IMAP_SERVER = "imap.gmail.com"
SEARCH_CRITERIA = '(LABEL "Github/archive-newsletters")' # Ensure exact label match

# --- Helper Functions ---

def decode_str(header_value):
    """
    Decodes MIME header strings safely.
    Handles 'utf-8', 'iso-8859-1', and None cases.
    """
    if not header_value:
        return ""
    
    decoded_fragments = decode_header(header_value)
    result = ""
    
    for part, encoding in decoded_fragments:
        if isinstance(part, bytes):
            try:
                if encoding:
                    result += part.decode(encoding, errors='replace')
                else:
                    result += part.decode('utf-8', errors='replace')
            except LookupError:
                # Fallback for unknown encodings
                result += part.decode('utf-8', errors='replace')
        elif isinstance(part, str):
            result += part
            
    return result.strip()

def get_safe_filename(s):
    """Creates a filesystem-safe string."""
    return "".join([c for c in s if c.isalnum() or c in (' ', '-', '_')]).strip()

def extract_html_content(msg):
    """
    Robustly extracts HTML content from an email object.
    Falls back to text if no HTML found, wrapped in <pre>.
    """
    html_content = None
    text_content = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" in content_disposition:
                continue

            try:
                payload = part.get_payload(decode=True)
                if not payload: continue
                
                charset = part.get_content_charset() or 'utf-8'
                decoded_text = payload.decode(charset, errors='replace')

                if content_type == "text/html":
                    html_content = decoded_text
                elif content_type == "text/plain":
                    text_content = decoded_text
            except Exception as e:
                print(f"Error decoding part: {e}")
    else:
        # Single part email
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            if payload:
                content = payload.decode(charset, errors='replace')
                if msg.get_content_type() == "text/html":
                    html_content = content
                else:
                    text_content = content
        except Exception as e:
            print(f"Error decoding body: {e}")

    if html_content:
        return html_content
    elif text_content:
        # Wrap plain text in simple HTML
        return f"<html><body><pre>{text_content}</pre></body></html>"
    return "<html><body><p>No readable content found.</p></body></html>"

def wrap_in_viewer(title, date_str, raw_html):
    """
    Wraps the email content in a centered container to fix display issues on wide screens.
    REMOVED: The 'Back' button navigation.
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
        /* Reset and Base Styles */
        body {{
            background-color: #e9ecef;
            margin: 0;
            padding: 0;
            font-family: sans-serif;
            min-height: 100vh;
        }}
        
        /* The Wrapper: Centers content like a paper document */
        .email-container {{
            max-width: 800px;  /* Standard email width */
            margin: 0 auto;
            background: #ffffff;
            position: relative;
            min-height: 100vh;
            box-shadow: 0 0 30px rgba(0,0,0,0.05);
        }}

        /* Content Isolation */
        .email-content {{
            padding: 20px 0; /* Vertical padding only */
        }}

        /* Responsive Fixes for Email Content */
        .email-content img {{
            max-width: 100% !important;
            height: auto !important;
        }}
        .email-content table {{
            max-width: 100% !important;
            width: auto !important; /* Allow tables to shrink */
        }}
        
        /* Mobile Tweak */
        @media (max-width: 820px) {{
            .email-container {{ width: 100%; box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-content">
            {raw_html}
        </div>
    </div>
</body>
</html>
"""

def download_images(soup, folder_path):
    """
    Downloads images referenced in <img> tags to a local 'images' folder.
    Updates the soup object in-place with relative paths.
    """
    images_dir = os.path.join(folder_path, "images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    for i, img in enumerate(soup.find_all('img')):
        src = img.get('src')
        if not src or not src.startswith('http'):
            continue

        try:
            # Simple extension detection
            ext = 'jpg'
            if '.png' in src.lower(): ext = 'png'
            elif '.gif' in src.lower(): ext = 'gif'
            elif '.svg' in src.lower(): ext = 'svg'

            filename = f"image_{i}.{ext}"
            local_path = os.path.join(images_dir, filename)

            # Check if we already have it (deduplication based on filename not content for speed)
            if not os.path.exists(local_path):
                response = requests.get(src, timeout=10, stream=True)
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
            
            # Update HTML to point to local file
            img['src'] = f"./images/{filename}"
            # Remove srcset to prevent browser loading original
            if img.has_attr('srcset'):
                del img['srcset']
                
        except Exception as e:
            print(f"Failed to download image {src}: {e}")

def process_single_email(msg_data):
    """Processes a single RFC822 email message."""
    try:
        msg = email.message_from_bytes(msg_data)
        
        # 1. Metadata extraction
        subject = decode_str(msg["Subject"]) or "No Subject"
        msg_date = msg["Date"]
        
        # Parse Date
        date_obj = datetime.now()
        if msg_date:
            try:
                date_tuple = email.utils.parsedate_tz(msg_date)
                if date_tuple:
                    date_obj = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
            except Exception:
                pass
        
        date_str = date_obj.strftime("%Y-%m-%d")
        
        # 2. Generate ID and Path
        # Use Message-ID or hash of subject+date for uniqueness
        uid = msg.get("Message-ID") or f"{subject}{date_str}"
        folder_name = hashlib.md5(uid.encode()).hexdigest()[:12]
        folder_path = os.path.join(DOCS_DIR, folder_name)

        if os.path.exists(folder_path):
            print(f"Skipping existing: {subject}")
            return # Already archived

        print(f"Processing: {subject}")
        os.makedirs(folder_path, exist_ok=True)

        # 3. Extract and Clean HTML
        raw_html = extract_html_content(msg)
        soup = BeautifulSoup(raw_html, 'html.parser')

        # 4. Download Assets
        download_images(soup, folder_path)

        # 5. Extract BODY only (remove Head/Html tags from the email to prevent conflict)
        # We want to inject the *content* of the email into our wrapper.
        email_body_content = ""
        if soup.body:
            email_body_content = soup.body.decode_contents()
        else:
            email_body_content = str(soup)

        # 6. Wrap and Save
        final_html = wrap_in_viewer(subject, date_str, email_body_content)
        
        with open(os.path.join(folder_path, "index.html"), "w", encoding='utf-8') as f:
            f.write(final_html)

    except Exception as e:
        print(f"Error processing email: {e}")

def main():
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("Error: GMAIL_USER or GMAIL_PASSWORD not set.")
        sys.exit(1)

    print(f"Connecting to {IMAP_SERVER}...")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select('inbox')

        status, messages = mail.search(None, SEARCH_CRITERIA)
        if status != "OK":
            print("No emails found or search failed.")
            return

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} emails matching criteria.")

        for e_id in email_ids:
            # Fetch the email body (RFC822)
            res, data = mail.fetch(e_id, '(RFC822)')
            if res == 'OK':
                process_single_email(data[0][1])
            else:
                print(f"Failed to fetch email ID {e_id}")

        mail.close()
        mail.logout()
        print("Done.")

    except Exception as e:
        print(f"Critical Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```[[1](https://www.google.com/url?sa=E&q=https%3A%2F%2Fgithub.com%2Fbenoit-prentout%2Farchive-news)]
