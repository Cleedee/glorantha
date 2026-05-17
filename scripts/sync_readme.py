#!/usr/bin/env python3
"""
sync_readme.py — Atualiza as tabelas "Categorias da Wiki" e "Estatísticas Atuais" no README.md

Uso:
    python scripts/sync_readme.py

Lê:
    - wiki/*.md (frontmatter para categoria)
    - git log (contagem de commits)

Escreve:
    - README.md (substitui as duas tabelas)
"""

import re
import os
import subprocess
from datetime import datetime

WIKI_DIR = "wiki"
README = "README.md"

CATEGORY_ORDER = [
    "Entidade",
    "Localização",
    "Evento",
    "Magia",
    "Conceito",
    "Fonte",
    "Cultura",
    "Cronologia",
]

CATEGORY_DESCRIPTIONS = {
    "Entidade": "Deuses, heróis, figuras históricas, NPCs",
    "Localização": "Regiões, cidades, templos, marcos geográficos",
    "Evento": "Batalhas, heroquestes, marcos temporais",
    "Magia": "Feitiços, runas, sistemas mágicos",
    "Conceito": "Ideias abstratas, mecânicas, cosmologia",
    "Fonte": "Livros, suplementos, campanhas, aventuras",
    "Cultura": "Povos, tribos, nações, organizações",
    "Cronologia": "Linhas temporais, eras, calendários",
}


def extract_category(filepath):
    """Extrai o campo 'category' do frontmatter YAML de um arquivo .md."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return None

    frontmatter = m.group(1)
    cm = re.search(r'^category:\s*"([^"]+)"', frontmatter, re.MULTILINE)
    if cm:
        return cm.group(1)
    cm = re.search(r"^category:\s*(\S+)", frontmatter, re.MULTILINE)
    if cm:
        return cm.group(1)
    return None


def count_git_commits():
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return int(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 0


def build_category_table(category_counts):
    lines = [
        "| Categoria | Conteúdo | Páginas |",
        "|-----------|----------|---------|",
    ]
    for cat in CATEGORY_ORDER:
        desc = CATEGORY_DESCRIPTIONS.get(cat, "")
        count = category_counts.get(cat, 0)
        lines.append(f"| **{cat}** | {desc} | {count} |")
    return "\n".join(lines)


def build_stats_table(total_pages, total_sources, total_commits):
    month_names = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ]
    today = datetime.now()
    date_str = f"{month_names[today.month - 1]} {today.year}"

    return "\n".join([
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| Páginas na wiki | {total_pages} |",
        f"| Fontes referenciadas | {total_sources} |",
        f"| Commits | {total_commits} |",
        f"| Última atualização | {date_str} |",
        "| Idioma | Português Brasileiro (pt-BR) |",
    ])


def replace_table(readme_path, header_line, new_table):
    """Encontra uma tabela markdown pelo cabeçalho e a substitui."""
    with open(readme_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    start_idx = None
    for i, line in enumerate(lines):
        if line.rstrip() == header_line:
            start_idx = i
            break

    if start_idx is None:
        print(f"ERRO: cabeçalho não encontrado: {header_line}")
        return False

    end_idx = start_idx
    for i in range(start_idx, len(lines)):
        if lines[i].startswith("|"):
            end_idx = i
        else:
            break

    new_lines = lines[:start_idx] + [new_table + "\n"] + lines[end_idx + 1:]

    with open(readme_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return True


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)

    category_counts = {cat: 0 for cat in CATEGORY_ORDER}
    total_pages = 0
    all_sources = set()

    for fname in os.listdir(WIKI_DIR):
        fpath = os.path.join(WIKI_DIR, fname)
        if not os.path.isfile(fpath) or not fname.endswith(".md"):
            continue
        if fname in ("index.md", "log.md"):
            continue
        total_pages += 1
        cat = extract_category(fpath)
        if cat and cat in category_counts:
            category_counts[cat] += 1

        # Coleta URLs de fontes do frontmatter
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if m:
            fm = m.group(1)
            sources_m = re.search(r'^sources:\s*\[(.*?)\]', fm, re.MULTILINE)
            if sources_m:
                sources_str = sources_m.group(1)
                for s in re.findall(r'"(https?://[^"]+)"', sources_str):
                    all_sources.add(s)

    total_sources = len(all_sources)
    total_commits = count_git_commits()

    ok = replace_table(README,
        "| Categoria | Conteúdo | Páginas |",
        build_category_table(category_counts))
    if not ok:
        return 1

    ok = replace_table(README,
        "| Métrica | Valor |",
        build_stats_table(total_pages, total_sources, total_commits))
    if not ok:
        return 1

    print(f"✓ README.md atualizado:")
    print(f"  - {total_pages} páginas na wiki")
    print(f"  - {total_sources} fontes processadas")
    print(f"  - {total_commits} commits")
    for cat in CATEGORY_ORDER:
        c = category_counts[cat]
        print(f"  - {cat}: {c} página{'s' if c != 1 else ''}")
    return 0


if __name__ == "__main__":
    exit(main())
