import os
import re

def clean_content(content):
    # 1. Broadly identify the redundant <style> block
    # It starts after the main style.css link and ends before the body
    # Actually, we can just look for the first <style> and last </style> in head
    head_match = re.search(r'<head>(.*?)</head>', content, re.DOTALL)
    if head_match:
        head_inner = head_match.group(1)
        # Find all <style> blocks and remove them IF they contain .device-frame (viewer specific)
        style_blocks = re.findall(r'<style.*?>.*?</style>', head_inner, re.DOTALL)
        for block in style_blocks:
            if '.device-frame' in block or '.meta-sidebar' in block:
                content = content.replace(block, '<!-- Inline Viewer Styles Moved to style.css -->')

    # 2. Cleanup Script Block
    script_pattern = r'(<script>\s*const content = .*?)(</script>)'
    match = re.search(script_pattern, content, re.DOTALL)
    if match:
        script_full = match.group(0)
        # Find 'const content' part
        content_marker = "const content ="
        init_marker = "function init()"
        
        c_start = script_full.find(content_marker)
        i_start = script_full.find(init_marker)
        
        if c_start != -1 and i_start != -1:
            content_part = script_full[c_start:i_start].rstrip()
            
            # Reconstruct minimalist script
            clean_script = f"""<script>
        {content_part}
        
        function init() {{
            const frame = document.getElementById('emailFrame');
            if (!frame) return;
            const doc = frame.contentDocument;
            doc.open();
            doc.write(content);
            doc.close();

            // Apply theme (which calls setupFrame)
            const theme = localStorage.getItem('theme') || 'light';
            applyTheme(theme);
        }}
        init();
    </script>"""
            content = content.replace(script_full, clean_script)

    return content

base_dir = r"c:\Users\prent\Github repos\archive-news\archive-news\docs"

for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file == "index.html" and root != base_dir:
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = clean_content(content)
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Cleaned {file_path}")
