
import os
import json
import jinja2
import datetime

# Setup Jinja2 environment
TEMPLATE_DIR = os.path.join(os.getcwd(), 'templates')
env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR))
env.globals.update(format_date=lambda d: d) # Placeholder, can process date filter if needed

def generate_viewer(metadata, html_content, links, output_path, lang='fr'):
    """
    Generates the viewer HTML using Jinja2 template.
    """
    template = env.get_template('viewer.html')
    
    # Calculate size for Gmail clipping warning
    email_size = len(html_content.encode('utf-8'))
    
    safe_html_json = json.dumps(html_content)
    
    rendered_html = template.render(
        subject=metadata.get('subject', 'No Subject'),
        email_date=metadata.get('date_rec', ''),
        sender_name=metadata.get('sender', 'Unknown'),
        archiving_date=metadata.get('date_arch', ''),
        preheader=metadata.get('preheader', ''),
        reading_time=metadata.get('reading_time', ''),
        links=links,
        safe_html=safe_html_json,
        email_size=email_size,
        lang=lang
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)
