
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
    "criteo.com", "matomo", "pixel.gif", "analytics", "tracking", "open.aspx"
]

RESOLVE_REDIRECTS = False
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

class EmailParser:
    def __init__(self, raw_html, output_folder):
        self.soup = BeautifulSoup(raw_html, "html.parser")
        self.output_folder = output_folder
        self.links = []
        self.detected_pixels = []

    def clean_and_process(self):
        # 1. Pixel Detection & Cleanup
        for img in self.soup.find_all("img"):
            src = img.get("src", "")
            if any(pattern in src for pattern in TRACKING_PATTERNS):
                self.detected_pixels.append(src)
                img['src'] = "" 
                img['style'] = "display:none !important;"
        
        # 2. Extract Preheader (Text approximation)
        text = self.soup.get_text(separator=" ", strip=True)
        self.preheader = text[:160] + "..." if len(text) > 160 else text
        self.reading_time = f"{max(1, round(len(text.split()) / 200))} min"

        # 3. Process Links (No resolution if Disabled)
        link_idx = 0
        for a in self.soup.find_all('a', href=True):
            link_idx += 1
            a['data-index'] = str(link_idx)
            original_url = a['href']
            
            self.links.append({
                'index': link_idx,
                'txt': a.get_text(strip=True)[:50],
                'original_url': original_url,
                'final_url': original_url # Skipping resolution as per new config
            })
            
    def download_images_parallel(self):
        images_to_download = []
        for img in self.soup.find_all("img"):
            # Handle lazy attrs
            for attr in ['data-src', 'data-original', 'data-url']:
                if img.get(attr):
                    img['src'] = img.get(attr)
                    break
            
            src = img.get("src")
            if not src or src.startswith("data:") or src.startswith("cid:"): continue
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

    def get_html(self):
        return str(self.soup)
