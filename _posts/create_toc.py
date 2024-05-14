import sys

def generate_toc(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        markdown_text = file.read()

    toc = []
    for line in markdown_text.split('\n'):
        if line.startswith('#'):
            level = len(line.split(' ')[0])  # Count the '#' characters
            title = line.strip('# ').strip()
            link = title.lower().replace(' ', '-')
            toc.append('  ' * (level - 1) + f'- [{title}](#{link})')
    return '\n'.join(toc)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        toc = generate_toc(file_path)
        print(toc)
    else:
        print("Usage: python script_name.py markdown_file.md")
