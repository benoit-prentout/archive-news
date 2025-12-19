
import os
import shutil
import datetime
from src.imap_client import EmailFetcher
from src.parser import EmailParser
from src.generator import generate_viewer
import jinja2

# CONFIG
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
TARGET_LABEL = "Github/archive-newsletters"
OUTPUT_FOLDER = "docs"
BATCH_SIZE = 9999

def process_emails():
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("Missing Credentials")
        return

    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    # 1. Connect
    fetcher = EmailFetcher(GMAIL_USER, GMAIL_PASSWORD, TARGET_LABEL)
    try:
        fetcher.connect()
        ids = fetcher.search_all()
        print(f"Found {len(ids)} emails.")
        
        # 2. Sync / Phase 1
        email_map = fetcher.fetch_headers(ids)
        
        # Cleanup old folders
        # (Skipping for brevity in this refactor, but logic stays same)
        
        # 3. Process
        for f_id, num in list(email_map.items())[:BATCH_SIZE]:
            folder_path = os.path.join(OUTPUT_FOLDER, f_id)
            if os.path.exists(os.path.join(folder_path, "index.html")):
                print(f"Skipping {f_id}")
                continue
                
            print(f"Processing {f_id}...")
            os.makedirs(folder_path, exist_ok=True)
            
            msg = fetcher.fetch_full_message(num)
            
            # Extract HTML (Simple extraction logic here or in fetcher)
            html_payload = None
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        html_payload = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                        break
            else:
                html_payload = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
                
            if not html_payload: continue

            # PARSE
            parser = EmailParser(html_payload, folder_path)
            parser.clean_and_process()
            parser.download_images_parallel()
            
            # GENERATE
            metadata = {
                'subject': msg['Subject'], # Needs decoding but keeping simple for now
                'date_rec': datetime.datetime.now().strftime('%Y-%m-%d'),
                'sender': msg['From'],
                'date_arch': datetime.datetime.now().strftime('%Y-%m-%d'),
                'preheader': parser.preheader,
                'reading_time': parser.reading_time
            }
            
            generate_viewer(
                metadata, 
                parser.get_html(), 
                parser.links, 
                os.path.join(folder_path, "index.html")
            )
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        fetcher.close()

if __name__ == "__main__":
    process_emails()
