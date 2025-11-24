import os
import re
from datetime import datetime
from bs4 import BeautifulSoup

# --- Configuration ---
DOCS_DIR = "docs"
OUTPUT_FILE = os.path.join(DOCS_DIR, "index.html")

# --- HTML Template ---
# A clean, responsive grid layout.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Newsletter Archive</title>
    <style>
        :root {
            --bg-color: #f4f7f6;
            --card-bg: #ffffff;
            --text-primary: #2c3e50;
            --text-secondary: #95a5a6;
            --accent: #3498db;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 40px 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 60px; }
        h1 { font-size: 2.5rem; color: var(--text-primary); margin-bottom: 10px; }
        .subtitle { color: var(--text-secondary); font-size: 1.1rem; }
        
        /* Search Bar */
        .search-wrapper { margin-top: 30px; display: flex; justify-content: center; }
        input[type="text"] {
            width: 100%; max-width: 500px; padding: 15px 25px;
            border-radius: 50px; border: 1px solid #ddd;
            font-size: 16px; box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            transition: all 0.3s ease; outline: none;
        }
        input[type="text"]:focus {
            box-shadow: 0 8px 25px rgba(52, 152, 219, 0.2);
            border-color: var(--accent);
        }

        /* Grid Layout */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 30px;
            padding: 20px 0;
        }
        .card {
            background: var(--card-bg);
            border-radius: 16px;
            padding: 25px;
            text-decoration: none;
            color: inherit;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
            border: 1px solid rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.1);
            border-color: rgba(52, 152, 219, 0.3);
        }
        .card-meta {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }
        .card-title {
            font-size: 1.25rem;
            font-weight: 700;
            line-height: 1.5;
            margin: 0;
            color: var(--text-primary);
        }
        .empty-state {
            text-align: center; color: var(--text-secondary);
            margin-top: 50px; display: none; font-size: 1.2rem;
        }
        footer {
            margin-top: 80px; text-align: center;
            color: var(--text-secondary); font-size: 0.9rem;
            border-top: 1px solid #e1e1e1; padding-top: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📬 Newsletter Archive</h1>
            <div class="subtitle">A curated collection of incoming newsletters</div>
            <div class="search-wrapper">
                <input type="text" id="search" placeholder="Search archives..." onkeyup="filterGrid()">
            </div>
        </header>

        <div class="grid" id="grid">
            {content}
        </div>
        
        <div id="no-results" class="empty-state">No newsletters found.</div>

        <footer>
            <p>Archive updated automatically.</p>
        </footer>
    </div>

    <script>
        function filterGrid() {
            const input = document.getElementById('search').value.toLowerCase();
            const cards = document.getElementsByClassName('card');
            let visibleCount = 0;

            for (let card of cards) {
                const title = card.querySelector('.card-title').innerText.toLowerCase();
                const date = card.querySelector('.card-meta').innerText.toLowerCase();
                
                if (title.includes(input) || date.includes(input)) {
                    card.style.display = "flex";
                    visibleCount++;
                } else {
                    card.style.display = "none";
                }
            }
            document.getElementById('no-results').style.display = visibleCount === 0 ? "block" : "none";
        }
    </script>
</body>
</html>
"""

def get_date_from_html(soup, filepath):
    """
    Tries to find the date in <meta> tags, or falls back to file modification time.
    """
    # 1. Try meta tag
    meta_date = soup.find("meta", {"name": "date"})
    if meta_date and meta_date.get('content'):
        return meta_date['content']
    
    # 2. Fallback to file mtime
    try:
        ts = os.path.getmtime(filepath)
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except:
        return "Unknown Date"

def generate_index():
    print("Generating index.html...")
    if not os.path.exists(DOCS_DIR):
        print(f"Directory '{DOCS_DIR}' not found. Creating it.")
        os.makedirs(DOCS_DIR)
        return

    newsletters = []
    
    # Scan directories
    for entry in os.scandir(DOCS_DIR):
        if entry.is_dir():
            index_path = os.path.join(entry.path, "index.html")
            if os.path.exists(index_path):
                try:
                    with open(index_path, 'r', encoding='utf-8', errors='ignore') as f:
                        soup = BeautifulSoup(f, 'html.parser')
                        
                        title = soup.title.string if soup.title else "Untitled"
                        date_str = get_date_from_html(soup, index_path)
                        
                        link = f"./{entry.name}/index.html"
                        
                        newsletters.append({
                            "title": title.strip(),
                            "date": date_str,
                            "link": link
                        })
                except Exception as e:
                    print(f"Skipping {entry.name}: {e}")

    # Sort by date (newest first)
    newsletters.sort(key=lambda x: x['date'], reverse=True)

    # Build HTML
    cards_html = ""
    for item in newsletters:
        cards_html += f"""
        <a href="{item['link']}" class="card">
            <div class="card-meta">{item['date']}</div>
            <h2 class="card-title">{item['title']}</h2>
        </a>
        """

    final_html = HTML_TEMPLATE.format(content=cards_html)

    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"Done. Index generated with {len(newsletters)} items.")

if __name__ == "__main__":
    generate_index()
