#!/usr/bin/env python3
"""
migrate_sources.py — Migra referências de raw/clippings/*.md para URLs originais.

Lê o frontmatter de cada arquivo em raw/clippings/ para extrair a URL source,
e substitui nas páginas da wiki:
  1. Frontmatter: sources: ["raw/clippings/X.md"] → sources: ["https://..."]
  2. Corpo: - Fonte: [Título](raw/clippings/X.md) → - Fonte: [Título](https://...)
  3. Corpo: - Fonte original: [Título](raw/clippings/X.md) → - Fonte original: [Título](https://...)
  4. Listas: - raw/clippings/X.md → - https://...

Uso:
  python scripts/migrate_sources.py [--dry-run]
"""

import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path("/home/claudio/Projetos/glorantha")
RAW_DIR = ROOT / "raw" / "clippings"
WIKI_DIR = ROOT / "wiki"

def build_url_map():
    """Mapeia nome do arquivo raw → URL source."""
    url_map = {}
    for f in RAW_DIR.glob("*.md"):
        content = f.read_text(encoding="utf-8")
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if match:
            fm = match.group(1)
            source_match = re.search(r'^source:\s*["\']?(.+?)["\']?\s*$', fm, re.MULTILINE)
            if source_match:
                url = source_match.group(1).strip().strip('"').strip("'")
                # Chave principal: nome exato do arquivo
                url_map[f.name] = url

    # Mapeamento manual para arquivos sem frontmatter ou com problemas
    manual = {
        "Noticias D100 do blog Runeblog.md": "https://elruneblog.blogspot.com/search/label/Glorantha",
        "Noticias D100 Cthulhu, RuneQuest, Mythras, Warhammer, etc. (abr. 2026).md": "https://elruneblog.blogspot.com/2026/04/noticias-d100-cthulhu-runequest-mythras.html",
    }
    url_map.update(manual)

    return url_map

def find_url_for_ref(raw_ref: str, url_map: dict) -> str | None:
    """Encontra URL para uma referência raw/clippings, tentando várias normalizações."""
    # Extrai apenas o nome do arquivo do path
    filename = raw_ref.replace("raw/clippings/", "")

    # Tentativa 1: match exato
    if filename in url_map:
        return url_map[filename]

    # Tentativa 2: match case-insensitive
    filename_lower = filename.lower()
    for key, url in url_map.items():
        if key.lower() == filename_lower:
            return url

    # Tentativa 3: match ignorando espaços vs %20
    decoded = urllib.parse.unquote(filename)
    if decoded in url_map:
        return url_map[decoded]
    decoded_lower = decoded.lower()
    for key, url in url_map.items():
        if key.lower() == decoded_lower:
            return url

    # Tentativa 4: match parcial (remove parênteses, pontuação extra)
    import unicodedata
    def normalize(s):
        s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
        s = re.sub(r'[^\w\s.-]', '', s)
        return re.sub(r'\s+', ' ', s).strip().lower()

    norm_ref = normalize(filename)
    for key, url in url_map.items():
        if normalize(key) == norm_ref:
            return url

    return None

def migrate_file(content: str, url_map: dict) -> tuple[str, list[str]]:
    """Migra referências em um conteúdo. Retorna (novo_conteudo, lista_de_mudancas)."""
    changes = []

    # 1. Frontmatter sources
    def replace_source_in_fm(match):
        sources_str = match.group(1)
        new_str = sources_str
        for raw_name, url in url_map.items():
            pattern = rf'raw/clippings/{re.escape(raw_name)}'
            if re.search(pattern, new_str, re.IGNORECASE):
                new_str = re.sub(pattern, url, new_str, flags=re.IGNORECASE)
                changes.append(f"  frontmatter: {raw_name} → {url}")
        return f'sources: [{new_str}]'

    content = re.sub(r'sources: \[(.*?)\]', replace_source_in_fm, content)

    # 2. "- Fonte original: [Título](raw/clippings/X.md)"
    def replace_source_original(match):
        title = match.group(1)
        raw_ref = match.group(2)
        url = find_url_for_ref(raw_ref, url_map)
        if url:
            changes.append(f"  corpo (Fonte original): {title} → {url}")
            return f'- Fonte original: [{title}]({url})'
        return match.group(0)

    content = re.sub(r'- Fonte original: \[([^\]]+)\]\((raw/clippings/.+?\.md)\)', replace_source_original, content)

    # 3. "- Fonte: [Título](raw/clippings/X.md)"
    def replace_source(match):
        title = match.group(1)
        raw_ref = match.group(2)
        url = find_url_for_ref(raw_ref, url_map)
        if url:
            changes.append(f"  corpo: {title} → {url}")
            return f'- Fonte: [{title}]({url})'
        return match.group(0)

    content = re.sub(r'- Fonte: \[([^\]]+)\]\((raw/clippings/.+?\.md)\)', replace_source, content)

    # 4. "- Arquivo local: [raw/clippings/X.md](raw/clippings/X.md)"
    def replace_local_file(match):
        raw_ref = match.group(1)
        url = find_url_for_ref(raw_ref, url_map)
        if url:
            changes.append(f"  arquivo local: {raw_ref} → {url}")
            return f'- Fonte: [{url}]({url})'
        return match.group(0)

    content = re.sub(r'- Arquivo local: \[(raw/clippings/[^\]]+)\]\((raw/clippings/[^\)]+)\)', replace_local_file, content)

    # 5. "-Fonte: [Título](raw/clippings/X.md)" (sem espaço após -)
    def replace_source_nospace(match):
        title = match.group(1)
        raw_ref = match.group(2)
        url = find_url_for_ref(raw_ref, url_map)
        if url:
            changes.append(f"  corpo (-Fonte): {title} → {url}")
            return f'- Fonte: [{title}]({url})'
        return match.group(0)

    content = re.sub(r'-Fonte: \[([^\]]+)\]\((raw/clippings/[^\)]+)\)', replace_source_nospace, content)

    # 6. Listas com path direto: "  - raw/clippings/X.md"
    def replace_list_item(match):
        indent = match.group(1)
        raw_ref = match.group(2)
        url = find_url_for_ref(raw_ref, url_map)
        if url:
            changes.append(f"  lista: {raw_ref} → {url}")
            return f'{indent}- {url}'
        return match.group(0)

    content = re.sub(r'^(\s+)- (raw/clippings/[^\n]+)$', replace_list_item, content, flags=re.MULTILINE)

    return content, changes

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Migra referências raw/clippings → URLs originais")
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostra mudanças, não escreve")
    args = parser.parse_args()

    url_map = build_url_map()
    print(f"Mapeadas {len(url_map)} fontes raw → URL")

    total_changed = 0
    total_refs = 0

    for wiki_file in sorted(WIKI_DIR.glob("*.md")):
        if wiki_file.name in ("index.md", "log.md"):
            continue
        content = wiki_file.read_text(encoding="utf-8")
        new_content, changes = migrate_file(content, url_map)
        if changes:
            total_changed += 1
            total_refs += len(changes)
            if not args.dry_run:
                wiki_file.write_text(new_content, encoding="utf-8")
            else:
                print(f"\n{wiki_file.name}:")
                for c in changes:
                    print(c)

    mode = "[DRY RUN]" if args.dry_run else "✓"
    print(f"\n{mode} {total_changed} páginas modificadas, {total_refs} referências migradas")

if __name__ == "__main__":
    main()
