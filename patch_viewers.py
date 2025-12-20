def update_content(content):
    import re
    # Inject Email Size row if not present
    if 'Email Size' not in content:
        # Calculate size in MB based on content string length (rough approximation)
        match = re.search(r'const content = "(.*?)";', content, re.DOTALL)
        if match:
            size_bytes = len(match.group(1))
            size_mb = f"{size_bytes / (1024 * 1024):.2f} MB"
            
            # Find insertion point after 'Archived' row
            insert_point = content.find('<div class="section-title">Technical</div>')
            if insert_point != -1:
                new_row = f"""
                <div class="meta-row">
                    <span class="meta-key">Email Size</span>
                    <span class="meta-val">{size_mb}</span>
                </div>
                """
                content = content[:insert_point] + new_row + content[insert_point:]

    # Update Tracking Pixel Explanations
    content = content.replace(
        '<div class="pixel-reason">Known Tracking Domain</div>',
        '<div class="pixel-reason">Known Tracking Domain</div>\n                        <div class="pixel-desc">Blocked because the domain is on a known list of email trackers.</div>'
    )
    content = content.replace(
        '<div class="pixel-reason">1x1 Pixel Dimensions</div>',
        '<div class="pixel-reason">1x1 Pixel Dimensions</div>\n                        <div class="pixel-desc">Blocked because this image is 1x1 pixels, a common technique for invisible open tracking.</div>'
    )
    
    # Add CSS for pixel-desc if not present
    if '.pixel-desc' not in content:
        style_insert = content.find('</style>')
        if style_insert != -1:
            css = """
        .pixel-desc {
            font-size: 0.75rem;
            color: var(--text-tertiary);
            margin-top: 2px;
            font-style: italic;
        }"""
            content = content[:style_insert] + css + content[style_insert:]

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
