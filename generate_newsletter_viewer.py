# generate_newsletter_viewer.py
import json
import datetime

ICON_MOBILE = '<svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>'
ICON_LINK = '<svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>'
ICON_MOON = '<svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>'

def create_viewer_html(subject, sender, email_date, html_content, links):
    links_html = "".join([f'<li><a href="{l["url"]}" target="_blank"><div class="link-txt">{l["txt"]}</div><div class="link-url">{l["url"]}</div></a></li>' for l in links])
    
    viewer_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="creation_date" content="{email_date}">
        <meta name="sender" content="{sender}">
        <meta name="archiving_date" content="{datetime.datetime.now().strftime('%Y-%m-%d')}">
        <title>{subject}</title>
        <link rel="stylesheet" href="../viewer.css">
    </head>
    <body>
        <header class="header">
            <div class="title">{subject}</div>
            <div class="controls">
                <button class="btn" id="btn-links">{ICON_LINK} Liens ({len(links)})</button>
                <button class="btn" id="btn-mobile">{ICON_MOBILE} Mobile</button>
                <button class="btn" id="btn-dark">{ICON_MOON} Sombre</button>
            </div>
        </header>
        
        <main class="main-view">
            <div class="iframe-wrapper">
                <iframe id="emailFrame" srcdoc=""></iframe>
            </div>
        </main>
        
        <aside class="sidebar" id="sidebar">
            <h3>Liens détectés</h3>
            <ul>{links_html}</ul>
        </aside>
        
        <script>
            window.emailContent = {json.dumps(str(html_content))};
        </script>
        <script src="../viewer.js"></script>
    </body>
    </html>
    """
    return viewer_content
