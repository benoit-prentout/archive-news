
from bs4 import BeautifulSoup
import html
import re
import requests
import mimetypes
import os
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

TRACKING_PATTERNS = [
    "api.getinside.media", "google-analytics.com", "doubleclick.net", "facebook.com/tr",
    "criteo.com", "matomo", "pixel.gif", "analytics", "tracking", "open.aspx",
    "hs-analytics.net", "hubspot.com", "marketo.com", "pardot.com"
]

# CRM Detection Patterns
CRM_PATTERNS = {
    'Mailchimp': ['list-manage.com', 'mailchimp.com', 'mc.us', 'mcusercontent.com', 'campaign-archive.com'],
    'Brevo': ['sibforms.com', 'sendinblue.com', 'brevo.com', 'sib.com'],
    'Klaviyo': ['klaviyo.com', 'klclick.com', 'kclick.com'],
    'Mailjet': ['mailjet.com', 'mjt.lu'],
    'HubSpot': ['hubspot.com', 'hs-analytics.net', 'hubspotemail.net', 'hsforms.com'],
    'Salesforce': ['salesforce.com', 'exacttarget.com', 'sfmc-content.com', 'igodigital.com'],
    'Oracle Responsys': ['responsys.net', 'rsys2.com', 'rsys5.com'],
    'Braze': ['braze.com', 'appboy.com'],
    'ActiveCampaign': ['activecampaign.com', 'activehosted.com', 'acems.com'],
    'Adobe Marketo': ['marketo.com', 'mktotrack.com'],
    'Dotdigital': ['dotdigital.com', 'dotmailer.com', 'dmptrk.com'],
    'Campaign Monitor': ['createsend.com', 'cmail'],
    'MailerLite': ['mailerlite.com', 'mlsend.com'],
    'SendPulse': ['sendpulse.com', 'sendpulse.me'],
    'Moosend': ['moosend.com'],
    'Emma': ['myemma.com', 'e2ma.net'],
    'Listrak': ['listrak.com', 'listrakbi.com'],
    'Sailthru': ['sailthru.com'],
    'Bluecore': ['bluecore.com'],
    'Mad Mimi': ['madmimi.com'],
    'iContact': ['icontact.com'],
    'AWeber': ['aweber.com'],
    'Postmark': ['postmarkapp.com', 'pstmrk.it'],
    'Sendgrid': ['sendgrid.net', 'sendgrid.com'],
    'Sarbacane': ['sarbacane.com', 'sbc'],
    'Splio': ['splio.com'],
    'Dolist': ['dolist.com', 'dolist.net'],
    'Shopify': ['shopify.com', 'shopifyemail.com'],
}

RESOLVE_REDIRECTS = True
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
}

class EmailParser:
    def __init__(self, raw_html, output_folder, headers=None, attachments=None):
        self.soup = BeautifulSoup(raw_html, "html.parser")
        self.output_folder = output_folder
        self.headers = headers or {}
        self.attachments = attachments or {} # {cid: bytes_content}
        self.links = []
        self.detected_pixels = []
        self.detected_crm = None

    def detect_crm(self):
        """Detect which CRM/ESP was used to send this email by analyzing URLs and headers."""
        
        # 1. Check Headers (Most reliable)
        header_mapping = {
            'X-Mailer': {
                'Mailchimp': 'mailchimp',
                'Brevo': 'brevo',
                'Sendinblue': 'sendinblue',
                'Mailjet': 'mailjet',
                'Klaviyo': 'klaviyo',
                'HubSpot': 'hubspot',
                'Salesforce': 'salesforce',
                'ActiveCampaign': 'activecampaign',
                'Shopify': 'shopify'
            },
            'X-Report-Abuse-To': {
                'Mailchimp': 'mcsv.net',
                'Brevo': 'brevo',
                'Sendinblue': 'sendinblue'
            },
            'List-Unsubscribe': {
                'Mailchimp': 'list-manage.com',
                'Brevo': 'brevo',
                'Klaviyo': 'klclick',
                'HubSpot': 'hubspot',
                'Shopify': 'shopifyemail'
            }
        }

        for header_key, mapping in header_mapping.items():
            val = str(self.headers.get(header_key, '')).lower()
            if val:
                for crm_name, marker in mapping.items():
                    if marker in val:
                        self.detected_crm = crm_name
                        return crm_name

        # 2. Check URLs as fallback
        all_urls = []
        for a in self.soup.find_all('a', href=True):
            all_urls.append(a['href'].lower())
        for img in self.soup.find_all('img', src=True):
            all_urls.append(img['src'].lower())
        
        # Priority check for specific strong markers
        for url in all_urls:
            if 'shopifyemail.com' in url or 'shopify.com' in url:
                self.detected_crm = 'Shopify'
                return 'Shopify'
            if 'klclick.com' in url or 'klaviyo' in url:
                self.detected_crm = 'Klaviyo'
                return 'Klaviyo'
            if 'mcsv.net' in url or 'list-manage.com' in url:
                self.detected_crm = 'Mailchimp'
                return 'Mailchimp'

        # Generic pattern check
        for crm_name, patterns in CRM_PATTERNS.items():
            for pattern in patterns:
                for url in all_urls:
                    if pattern in url:
                        # Extra validation: if it's sendgrid/amazonses, only set if nothing else found
                        if crm_name in ['Sendgrid', 'Amazon SES'] and self.detected_crm:
                            continue
                        self.detected_crm = crm_name
                        return crm_name
        
        return None

    def clean_and_process(self):
        # 1. Pixel Detection & Cleanup
        for img in self.soup.find_all("img"):
            src = img.get("src", "")
            width = img.get("width")
            height = img.get("height")
            
            # Detect by pattern OR dimensions (1x1)
            reason = None
            if any(pattern in src for pattern in TRACKING_PATTERNS):
                reason = "Known Tracking Domain"
            elif width == "1" and height == "1":
                reason = "1x1 Pixel Dimensions"
                
            if reason:
                # Extract domain for pixel to match link layout
                pixel_domain = ""
                try:
                    from urllib.parse import urlparse
                    pixel_domain = urlparse(src).netloc.replace('www.', '')
                except:
                    pass
                
                self.detected_pixels.append({
                    'url': src, 
                    'status': 'Integration: OK',
                    'domain': pixel_domain
                })
                img['src'] = "" 
                img['style'] = "display:none !important;"
        
        # 2. Extract Preheader (Text approximation)
        # Strip invisible characters like zero-width joiners and spacing characters used in emails
        text = self.soup.get_text(separator=" ", strip=True)
        text = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\ufeff\u2007\u034f\u2060\u2061\u2062\u2063\u2064\u206a\u206b\u206c\u206d\u206e\u206f]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        self.preheader = text[:160] + "..." if len(text) > 160 else text
        self.reading_time = f"{max(1, round(len(text.split()) / 200))} min"

        # 3. Process Links (Audit + List)
        link_idx = 0
        self.audit = {
            'subject_length': 0,
            'subject_check': 'OK',
            'unsubscribe_found': False,
            'link_count': 0,
            'images_no_alt': 0
        }
        
        # Link Audit
        for a in self.soup.find_all('a', href=True):
            link_idx += 1
            a['data-index'] = str(link_idx)
            original_url = a['href']
            
            # Domain Extraction
            domain = ""
            try:
                from urllib.parse import urlparse
                parsed = urlparse(original_url)
                domain = parsed.netloc.replace('www.', '')
            except:
                pass

            # Tracking Check
            is_tracking = any(pattern in original_url.lower() for pattern in TRACKING_PATTERNS)
            
            # Security & Dev Audit
            is_secure = original_url.startswith('https://') or original_url.startswith('//')
            dev_patterns = ['test', 'staging', 'dev.', 'localhost', 'internal', 'bat.', 'preprod']
            is_dev = any(p in original_url.lower() for p in dev_patterns)

            # Unsubscribe check
            txt = a.get_text(strip=True).lower()
            if 'unsubscribe' in txt or 'désinscrire' in txt or 'opt-out' in txt or 'manage preferences' in txt:
                self.audit['unsubscribe_found'] = True

            self.links.append({
                'index': link_idx,
                'txt': a.get_text(strip=True)[:50],
                'original_url': original_url,
                'final_url': original_url,
                'domain': domain,
                'is_tracking': is_tracking,
                'is_secure': is_secure,
                'is_dev': is_dev
            })
            
        self.audit['link_count'] = link_idx
        
        # Image Alt Audit
        for img in self.soup.find_all('img'):
            if not img.get('alt') and img.get('style') != "display:none !important;":
                self.audit['images_no_alt'] += 1

            
    def download_images_parallel(self):
        images_to_download = []
        for img in self.soup.find_all("img"):
            # Handle lazy attrs
            for attr in ['data-src', 'data-original', 'data-url']:
                if img.get(attr):
                    img['src'] = img.get(attr)
                    break
            
            src = img.get("src")
            if not src or src.startswith("data:"): continue
            
            # Special case for CID images
            if src.startswith("cid:"):
                cid = src.replace("cid:", "").strip("<>")
                if cid in self.attachments:
                    content = self.attachments[cid]
                    
                    # Detect extension from magic bytes
                    ext = ".jpg" # Default
                    if content.startswith(b'\x89PNG\r\n\x1a\n'):
                        ext = ".png"
                    elif content.startswith(b'GIF87a') or content.startswith(b'GIF89a'):
                        ext = ".gif"
                    elif content.startswith(b'\xff\xd8\xff'):
                        ext = ".jpg"
                    elif content.startswith(b'RIFF') and content[8:12] == b'WEBP':
                        ext = ".webp"
                    
                    local_name = f"img_{len(images_to_download)}{ext}"
                    path = os.path.join(self.output_folder, local_name)
                    with open(path, "wb") as f:
                        f.write(content)
                    img['src'] = local_name
                    continue # Already processed
                else:
                    print(f"Warning: CID {cid} not found in attachments.")
                    continue

            if src.startswith("//"): src = "https:" + src
            images_to_download.append((img, src))
            
        def _download(img_obj, url, idx):
            try:
                # Determine extension first (guess or default)
                # Optimization: We can't know the exact ext without HEAD/GET usually, 
                # but if we look at existing files in output_folder matching img_{idx}.*, we can skip.
                # Use a simple heuristics or just check common extensions.
                
                # Check for existing file with standard extensions
                for ext in ['.jpg', '.png', '.gif', '.jpeg', '.webp']:
                    potential_name = f"img_{idx}{ext}"
                    potential_path = os.path.join(self.output_folder, potential_name)
                    if os.path.exists(potential_path):
                        return img_obj, potential_name

                r = requests.get(url, headers=HEADERS, timeout=10)
                if r.status_code == 200:
                    ext = mimetypes.guess_extension(r.headers.get('content-type', '')) or ".jpg"
                    local_name = f"img_{idx}{ext}"
                    path = os.path.join(self.output_folder, local_name)
                    with open(path, "wb") as f: f.write(r.content)
                    return img_obj, local_name
            except: pass
            return img_obj, None

        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(_download, item[0], item[1], i): item for i, item in enumerate(images_to_download)}
            for f in as_completed(futures):
                img, local = f.result()
                if local: img['src'] = local

    def resolve_redirects_parallel(self):
        """Pre-calculate redirect chains for all links to avoid CORS issues in the statics viewer."""
        if not RESOLVE_REDIRECTS:
            return

        if not self.links:
            return

        # Use a list to maintain order if needed, but we care about unique URLs for efficiency
        unique_urls = list(set(l['original_url'] for l in self.links))
        results_cache = {}

        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def _resolve(url):
            chain = []
            try:
                session = requests.Session()
                session.headers.update(HEADERS)
                # Browser-like headers
                session.headers.update({
                    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Upgrade-Insecure-Requests': '1',
                })
                
                current_url = url
                max_redirects = 15
                for _ in range(max_redirects):
                    # Use a generous timeout for slow trackers
                    try:
                        resp = session.get(current_url, allow_redirects=False, timeout=15)
                    except requests.exceptions.Timeout:
                        chain.append({'status': 'Timeout', 'url': current_url})
                        break
                    except Exception as e:
                        chain.append({'status': 'Error', 'url': current_url})
                        break
                        
                    chain.append({
                        'status': resp.status_code,
                        'url': current_url
                    })
                    
                    if 300 <= resp.status_code < 400 and 'Location' in resp.headers:
                        next_url = resp.headers['Location']
                        from urllib.parse import urljoin
                        current_url = urljoin(current_url, next_url)
                    else:
                        break
                
                return {
                    'chain': chain,
                    'date': now
                }
                    
            except Exception as e:
                print(f"Error resolving {url}: {e}")
                return {
                    'chain': [{'status': 'Error', 'url': url}],
                    'date': now
                }

        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = {ex.submit(_resolve, url): url for url in unique_urls}
            for f in as_completed(futures):
                url = futures[f]
                results_cache[url] = f.result()

        # Apply results back to links
        for link in self.links:
            url = link['original_url']
            if url in results_cache:
                res = results_cache[url]
                link['redirect_chain'] = res['chain']
                link['audit_date'] = res['date']
                if link['redirect_chain']:
                    link['final_url'] = link['redirect_chain'][-1]['url']

    def get_html(self):
        return str(self.soup)
