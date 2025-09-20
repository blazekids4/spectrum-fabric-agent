"""md_to_csv.py

Simple utility to convert specific markdown transcripts into CSV tables.

Usage examples:
  # Convert the three known files in this folder (default)
  python md_to_csv.py

  # Convert specific files
  python md_to_csv.py path/to/4.1_synonyms.md path/to/4.1_competitors.md path/to/4.1_analysis.md

Outputs are written next to each input file with the same base name and a .csv extension.
"""
import sys
import os
import re
import csv
from typing import List


def parse_synonyms_md(content: str) -> List[dict]:
    """Parse synonyms markdown into rows of (group_id, competitor, variant).
    Expected structure:
      ### 1. COMPETITOR
      - variant A
      - variant B
    """
    rows = []
    current_id = None
    current_competitor = None
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # Heading e.g. '### 1. AT&T' or '### 1. AT&T'
        m = re.match(r'^###\s*(\d+)\.\s*(.+)$', line)
        if m:
            current_id = m.group(1).strip()
            current_competitor = m.group(2).strip()
            continue
        # Bullet lines
        if line.startswith('-') and current_competitor:
            variant = line.lstrip('-').strip()
            rows.append({'group_id': current_id, 'competitor': current_competitor, 'variant': variant})
    return rows


def parse_competitors_md(content: str) -> List[dict]:
    """Parse competitors markdown into rows of (group_id, competitor, mention_text).
    Expected structure:
      ### 1. **AT&T**
      - "line text"
    """
    rows = []
    current_id = None
    current_competitor = None
    for line in content.splitlines():
        line = line.rstrip()
        if not line:
            continue
        # Heading might be: ### 1. **AT&T** or ### 1. AT&T
        m = re.match(r'^###\s*(\d+)\.\s*(?:\*\*(.+?)\*\*|(.+))$', line)
        if m:
            current_id = m.group(1).strip()
            current_competitor = (m.group(2) or m.group(3) or '').strip()
            continue
        if line.strip().startswith('-') and current_competitor:
            mention = line.lstrip('-').strip()
            rows.append({'group_id': current_id, 'competitor': current_competitor, 'mention': mention})
    return rows


def parse_first_markdown_table(content: str) -> List[dict]:
    """Find and parse the first markdown table in the content into a list of dict rows.
    If no table present, fallback to capturing key/value top-level headers.
    """
    lines = content.splitlines()
    # Find table header line index
    table_start = None
    for i, ln in enumerate(lines):
        if '|' in ln and re.search(r'\|\s*[-:]+', lines[i+1] if i+1 < len(lines) else ''):
            table_start = i
            break
    if table_start is None:
        # No table -- output whole file as single-column CSV
        return [{'text': l} for l in lines if l.strip()]

    header_line = lines[table_start]
    sep_line = lines[table_start + 1]
    data_lines = []
    for ln in lines[table_start + 2:]:
        if not ln.strip() or (not ln.strip().startswith('|') and '|' not in ln):
            break
        data_lines.append(ln)

    headers = [h.strip() for h in header_line.strip().strip('|').split('|')]
    rows = []
    for dl in data_lines:
        cells = [c.strip() for c in dl.strip().strip('|').split('|')]
        # Pad cells to headers length
        while len(cells) < len(headers):
            cells.append('')
        row = {headers[idx]: cells[idx] for idx in range(len(headers))}
        rows.append(row)
    return rows


def write_csv(rows: List[dict], out_path: str):
    if not rows:
        print(f"No rows for {out_path}, creating empty file with no headers")
        open(out_path, 'w', encoding='utf-8').close()
        return
    # Determine fieldnames from union of keys preserving order from first row
    fieldnames = list(rows[0].keys())
    # Add any missing keys in later rows
    for r in rows:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"Wrote {len(rows)} rows to {out_path}")


def convert_file(md_path: str):
    basename = os.path.basename(md_path)
    name, _ = os.path.splitext(basename)
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'synonyms' in name.lower():
        rows = parse_synonyms_md(content)
        out = os.path.join(os.path.dirname(md_path), name + '.csv')
        write_csv(rows, out)
    elif 'competitor' in name.lower():
        rows = parse_competitors_md(content)
        out = os.path.join(os.path.dirname(md_path), name + '.csv')
        write_csv(rows, out)
    else:
        # analysis or any other markdown
        rows = parse_first_markdown_table(content)
        out = os.path.join(os.path.dirname(md_path), name + '.csv')
        write_csv(rows, out)


def main(argv):
    if len(argv) > 1:
        files = argv[1:]
    else:
        # default: convert the three known files in this folder
        base_dir = os.path.dirname(__file__)
        files = [
            os.path.join(base_dir, '4.1_synonyms.md'),
            os.path.join(base_dir, '4.1_competitors.md'),
            os.path.join(base_dir, '4.1_analysis.md'),
        ]
    for p in files:
        if not os.path.exists(p):
            print(f"File not found: {p}")
            continue
        try:
            convert_file(p)
        except Exception as e:
            print(f"Failed to convert {p}: {e}")


if __name__ == '__main__':
    main(sys.argv)
