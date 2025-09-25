import re
import sys

def replace_datetime_calls(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace .utcnow().isoformat() with utc_now_iso()
    content = re.sub(r'datetime\.utcnow\(\)\.isoformat\(\)', 'utc_now_iso()', content)
    
    # Replace .utcnow() with utc_now()
    content = re.sub(r'datetime\.utcnow\(\)', 'utc_now()', content)
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(f"Replaced datetime.utcnow() calls in {file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python replace_datetime.py <file_path>")
        sys.exit(1)
    
    replace_datetime_calls(sys.argv[1])