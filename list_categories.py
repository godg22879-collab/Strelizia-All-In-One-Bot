import os, re

folders = [r'AeroX/cogs/strelizia/main_menu', r'AeroX/cogs/strelizia/extra_menu']
categories = []

for folder in folders:
    for fname in sorted(os.listdir(folder)):
        if fname.endswith('.py') and fname != '__init__.py':
            fpath = os.path.join(folder, fname)
            with open(fpath, encoding='utf-8') as f:
                content = f.read()
            emoji_match = re.search(r"emoji\s*=\s*['\"]([^'\"]+)['\"]", content)
            label_match = re.search(r"label\s*=\s*['\"]([^'\"]+)['\"]", content)
            desc_match = re.search(r"description\s*=\s*['\"]([^'\"]+)['\"]", content)
            cls_match = re.search(r"class\s+([A-Za-z0-9_]+)", content)
            
            categories.append({
                'folder': os.path.basename(folder),
                'file': fname,
                'class': cls_match.group(1) if cls_match else '?',
                'emoji': emoji_match.group(1) if emoji_match else 'None',
                'label': label_match.group(1) if label_match else 'None',
                'desc': desc_match.group(1) if desc_match else 'None'
            })

for c in categories:
    print(f"[{c['folder']}] {c['file']:<16} | {c['label']:<18} | {c['emoji']:<36} | {c['desc']}")
