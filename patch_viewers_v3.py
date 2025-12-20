import os
import re

# Comprehensive CRM Dictionary
# Heuristics: key = CRM Name, value = list of unique string indicators (domains, headers, specific params)
crm_signatures = {
    "Salesforce": ["sfmc-content", "exacttarget", "pardot", "salesforce", "c. exacttarget.com"],
    "HubSpot": ["hubspot", "hs-cta", "_hsenc", "hubspotemail"],
    "Marketo": ["marketo", "mkt_tok", "mkto-"],
    "Braze": ["braze", "braze.com", "appboy"],
    "Klaviyo": ["klaviyo", "klclick", "trk_id=", "manage_preferences?a="],
    "Shopify": ["shopify", "shopifyemail"],
    "Mailchimp": ["mailchimp", "list-manage.com", "mc_cid"],
    "Brevo (Sendinblue)": ["sendinblue", "brevo", "nl2go", "sib_link_id"],
    "ActiveCampaign": ["activehosted", "ac_link"],
    "Dotdigital": ["dotdigital", "dotmailer"],
    "Iterable": ["iterable", "links.iterable.com"],
    "Emarsys": ["emarsys", "sc.emarsys.com"],
    "Bloomreach": ["bloomreach", "exponea"],
    "Attentive": ["attentive", "attn.tv"],
    "Yotpo": ["yotpo", "smsbump"],
    "Recharge": ["recharge", "rechargepayments"],
    "Sailthru": ["sailthru", "cb.sailthru.com"],
    "Cordial": ["cordial", "crdl.io"],
    "Selligent": ["selligent", "emsecure.net"],
    "Adobe Campaign": ["neolane", "adobe-campaign"],
    "Oracle Responsys": ["responsys", "rsys"],
    "Mailgun": ["mailgun"],
    "SendGrid": ["sendgrid", "sg_event_id"]
}

def detect_crm(content):
    content_lower = content.lower()
    for name, signatures in crm_signatures.items():
        for sig in signatures:
            if sig in content_lower:
                return name
    return "Unknown"

def update_content(content):
    # 1. Update CRM
    detected_crm = detect_crm(content)
    
    # Check if CRM row exists
    crm_row_pattern = r'<div class="meta-row">\s*<span class="meta-key">CRM</span>\s*<span class="meta-val">.*?</span>\s*</div>'
    new_crm_row = f"""<div class="meta-row">
                    <span class="meta-key">CRM</span>
                    <span class="meta-val">{detected_crm}</span>
                </div>"""
    
    if re.search(crm_row_pattern, content):
        content = re.sub(crm_row_pattern, new_crm_row, content)
    else:
        # Insert it if missing (look for Tech section)
        insert_marker = '<div class="section-title">Technical</div>'
        if insert_marker in content:
            content = content.replace(insert_marker, insert_marker + "\n" + new_crm_row)

    # 2. Add Copy Buttons to Links
    # Logic: Find the links list container and rebuild the links with buttons
    # Existing structure:
    # <li class="link-item" onclick="highlightLink(1)">
    #    <div class="link-num">1</div>
    #    <div class="link-content">
    #        <div class="link-txt">Title</div>
    #        <div class="link-url">URL</div>
    #    </div>
    # </li>
    
    def add_copy_btn(match):
        full_match = match.group(0)
        url_match = re.search(r'<div class="link-url">\s*(.*?)\s*</div>', full_match)
        if url_match:
            url = url_match.group(1).strip()
            # If button already exists, don't add
            if 'copy-btn-icon' in full_match:
                return full_match
                
            # Insert button after number
            btn_html = f'''<button class="copy-btn-icon" onclick="copyLink('{url}', this)" title="Copy Link">
                            <svg class="icon" viewBox="0 0 24 24" style="width:14px;height:14px;">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </svg>
                           </button>'''
            
            # Find insertion point: after <div class="link-num">X</div>
            return re.sub(r'(<div class="link-num">.*?</div>)', r'\1' + btn_html, full_match)
        return full_match

    content = re.sub(r'<li class="link-item".*?</li>', add_copy_btn, content, flags=re.DOTALL)

    # 3. Add Copy Source Button in Modal
    # Look for modal header
    modal_header = '<div class="modal-header">'
    if 'copy-source-btn' not in content:
        copy_btn = '<button class="copy-source-btn" onclick="copySource()">Copy Code</button>'
        # Insert before the close button or just append to header content
        # Header usually has <span>HTML Source</span> and <button class="close-btn">
        
        # Check if we can insert it nicely
        header_pattern = r'(<div class="modal-header">\s*<span>HTML Source</span>)'
        content = re.sub(header_pattern, r'\1' + '\n' + copy_btn, content)

    return content

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
