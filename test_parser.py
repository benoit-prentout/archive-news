
import os
import shutil
from src.parser import EmailParser

def test_cid_handling():
    test_folder = "test_output"
    if os.path.exists(test_folder):
        shutil.rmtree(test_folder)
    os.makedirs(test_folder)
    
    html = '<html><body><h1>Test CID</h1><img src="cid:test_img_1"></body></html>'
    # Mock image bytes (a small red pixel gif or similar)
    # Using a 1x1 transparent gif
    mock_img_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    
    attachments = {
        "test_img_1": mock_img_bytes
    }
    
    parser = EmailParser(html, test_folder, attachments=attachments)
    parser.download_images_parallel()
    
    processed_html = parser.get_html()
    print("Processed HTML:", processed_html)
    
    # Check if image was saved and src updated
    files = os.listdir(test_folder)
    print("Files in test folder:", files)
    
    success = False
    for f in files:
        if f.startswith("img_0"):
            success = True
            print(f"SUCCESS: Found saved image {f}")
            if f'src="{f}"' in processed_html:
                print(f"SUCCESS: HTML updated with {f}")
            else:
                print("FAILURE: HTML not updated correctly")
                success = False
    
    if not success:
        print("FAILURE: Image not found in output folder")

    # Cleanup
    # shutil.rmtree(test_folder)

if __name__ == "__main__":
    test_cid_handling()
