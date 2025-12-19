
import os
import shutil
from datetime import datetime
from src.imap_client import EmailFetcher
from src.parser import EmailParser
from src.generator import generate_viewer, generate_index
from email.utils import parsedate_to_datetime
import json

# CONFIG
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
TARGET_LABEL = "Github/archive-newsletters"
OUTPUT_FOLDER = "docs"
BATCH_SIZE = 9999
FORCE_UPDATE = os.environ.get("FORCE_UPDATE", "false").lower() == "true"


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
        ids.reverse() # Process newest first
        print(f"Found {len(ids)} emails.")
        
        # 2. Sync / Phase 1
        email_map = fetcher.fetch_headers(ids)
        
        # 3. Process
        all_metadata = []
        
        folders = [d for d in os.listdir(OUTPUT_FOLDER) if os.path.isdir(os.path.join(OUTPUT_FOLDER, d))]
        
        for f_id, num in list(email_map.items())[:BATCH_SIZE]:
            folder_path = os.path.join(OUTPUT_FOLDER, f_id)
            meta_path = os.path.join(folder_path, "metadata.json")
            
            if os.path.exists(meta_path) and not FORCE_UPDATE:
                print(f"Skipping {f_id}")
                with open(meta_path, 'r', encoding='utf-8') as f:
                    all_metadata.append(json.load(f))
                continue
                
            print(f"Processing {f_id}...")
            os.makedirs(folder_path, exist_ok=True)
            
            msg = fetcher.fetch_full_message(num)
            
            # Extract HTML
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
            
            # Extract Date from headers
            date_str = msg.get('Date')
            if date_str:
                try:
                    dt = parsedate_to_datetime(date_str)
                    date_rec = dt.strftime('%d/%m/%Y à %H:%M')
                    date_iso = dt.isoformat()
                except:
                    date_rec = date_str
                    date_iso = datetime.datetime.now().isoformat()
            else:
                date_rec = datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')
                date_iso = datetime.datetime.now().isoformat()
            
            # Metadata structure
            metadata = {
                'id': f_id,
                'subject': fetcher.get_decoded_subject(msg), 
                'date_rec': date_rec,
                'date_iso': date_iso,
                'sender': msg['From'],
                'date_arch': datetime.datetime.now().strftime('%d/%m/%Y à %H:%M'),
                'preheader': parser.preheader,
                'reading_time': parser.reading_time
            }
            
            # Save metadata for index
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)
            
            all_metadata.append(metadata)
            
            generate_viewer(
                metadata, 
                parser.get_html(), 
                parser.links, 
                os.path.join(folder_path, "index.html"),
                detected_pixels=parser.detected_pixels
            )
            
        # 4. Generate Main Index
        # Sort by date ISO (descending)
        all_metadata.sort(key=lambda x: x.get('date_iso', ''), reverse=True)
    print("Generating index...")
    
    # Calculate Stats
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(OUTPUT_FOLDER):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    
    size_mb = f"{total_size / (1024*1024):.1f} MB"
    last_updated = datetime.now().strftime("%d %b %Y, %H:%M")
    
    stats = {
        'last_updated': last_updated,
        'archive_size': size_mb,
        'count': len(all_metadata)
    }

    generate_index(all_metadata, os.path.join(OUTPUT_FOLDER, "index.html"), stats)
    
    print("Done!")
        
        # 5. Copy Assets
        from src.generator import copy_assets
        copy_assets(OUTPUT_FOLDER)
        print("Assets copied.")
        
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        fetcher.close()

if __name__ == "__main__":
    process_emails()
