def update_content(content):
    import re
    
    # --- CRM Detection ---
    crm = "Unknown"
    # Simple heuristic checks
    if 'klaviyo' in content.lower() or 'klclick' in content.lower():
        crm = "Klaviyo"
    elif 'nl2go' in content.lower() or 'brevo' in content.lower() or 'sendinblue' in content.lower():
        crm = "Brevo"
    elif 'shopify' in content.lower():
        crm = "Shopify"
    elif 'list-manage.com' in content.lower() or 'mailchimp' in content.lower():
        crm = "Mailchimp"
    elif 'intercom' in content.lower():
        crm = "Intercom"
    elif 'hubspot' in content.lower():
        crm = "HubSpot"

    # Inject CRM row if not present
    if 'CRM' not in content:
        insert_point = content.find('<div class="section-title">Technical</div>')
        if insert_point != -1:
            crm_row = f"""
                <div class="meta-row">
                    <span class="meta-key">CRM</span>
                    <span class="meta-val">{crm}</span>
                </div>"""
            content = content[:insert_point] + crm_row + content[insert_point:]

    # --- Pixel Simplify ---
    # The user wants less info for standard pixels.
    # We'll remove the long "Blocked because..." for 1x1 pixels and just keep it simple.
    
    # Removing the detailed description for 1x1 if present from previous patch
    content = re.sub(
        r'<div class="pixel-reason">1x1 Pixel Dimensions</div>\s*<div class="pixel-desc">.*?</div>',
        '<div class="pixel-reason">1x1 Pixel Dimensions</div>\n<div class="pixel-desc">Standard tracking pixel (Blocked).</div>',
        content, flags=re.DOTALL
    )
    
    # For Known Tracking Domain, we keep the explanation but maybe shorter?
    # User: "détaille uniquement si il présente un problème" -> "Known Tracking Domain" IS a "problem" (it's a list match).
    # "1x1" is standard.
    
    return content

import os

base_dir = r"c:\Users\prent\Github repos\archive-news\archive-news\docs"

for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file == "index.html" and root != base_dir:
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = update_content(content)
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {file_path}")
