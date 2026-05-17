#!/usr/bin/env python3
"""
ingest_source.py — Ingestão automatizada de fontes para a Glorantha Knowledge Base.

Lê um arquivo fonte de /raw/, extrai entidades/fatos automaticamente,
gera páginas wiki usando templates, e produz um relatório de mudanças.

Uso:
  python scripts/ingest_source.py <caminho_do_arquivo_fonte> [--dry-run] [--output-dir <dir>]

Exemplo:
  python scripts/ingest_source.py "raw/clippings/Journal of Runic Studies 29.md"
  python scripts/ingest_source.py "raw/clippings/Journal of Runic Studies 29.md" --dry-run
"""

import re
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import date
from dataclasses import dataclass, field, asdict
from typing import Optional

# ─── Configuração ───────────────────────────────────────────────────────────

ROOT = Path("/home/claudio/Projetos/glorantha")
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"
INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"

# Categorias válidas
CATEGORIAS = ["Entidade", "Localização", "Evento", "Magia", "Conceito", "Fonte", "Cultura", "Cronologia"]

# Palavras-chave por categoria (para classificação heurística)
CAT_KEYWORDS = {
    "Entidade": [
        "deus", "deusa", "herói", "heroína", "rei", "rainha", "sacerdote",
        "sacerdotisa", "imperador", "guerreiro", "xamã", "feiticeiro",
        "necromante", "artista", "autor", "escritor", "designer", "editora",
        "personagem", "entidade", "divindade", "nasceu", "morreu", "filho",
        "filha", "pai", "mãe", "culto", "iniciado", "sumo sacerdote",
        "sumo sacerdotisa", "lord", "lady", "príncipe", "princesa",
        "comandante", "general", "capitão", "cavaleiro", "bárbaro",
        "nômade", "viajante", "explorador", "bibliotecário",
        "berserk", "shield maiden", "agente", "operativo",
    ],
    "Localização": [
        "cidade", "vila", "aldeia", "região", "reino", "província",
        "templo", "santuário", "montanha", "rio", "lago", "mar",
        "oceano", "floresta", "deserto", "planície", "colina", "vale",
        "ilha", "continente", "capital", "porto", "fortaleza",
        "castelo", "torre", "ruínas", "pântano", "caverna",
        "passagem", "estrada", "rota", "fronteira", "território",
        "ilha-continente", "bacia", "cordilheira",
    ],
    "Evento": [
        "batalha", "guerra", "cerco", "conquista", "revolta", "rebelião",
        "tratado", "aliança", "fundação", "destruição", "nascimento",
        "morte", "coroação", "ascensão", "queda", "exílio", "retorno",
        "festival", "ritual", "heroquest", "expedição", "viagem",
        "conclave", "concílio", "conferência",
    ],
    "Magia": [
        "feitiço", "magia", "runa", "ritual", "encantamento", "maldição",
        "bênção", "invocação", "conjuração", "iluminação", "transcendência",
        "sistema de magia", "magia rúnica", "magia espiritual",
        "feitiçaria", "sorcery", "battle magic", "spirit magic",
    ],
    "Conceito": [
        "filosofia", "cosmologia", "mitologia", "teologia", "conceito",
        "ideia", "princípio", "regra", "lei", "sistema", "mecânica",
        "arquétipo", "monomito", "compromisso", "ciclo", "era",
        "tempo", "iluminação", "sombra", "identidade",
    ],
    "Cultura": [
        "povo", "tribo", "clã", "nação", "organização", "sociedade",
        "cultura", "raça", "espécie", "piratas", "nômades", "cavaleiros",
        "guerreiros", "sacerdócio", "ordem", "guilda", "facção",
        "hsunchen", "bando", "confederação", "império", "reino",
    ],
    "Fonte": [
        "livro", "suplemento", "review", "resenha", "artigo", "periódico",
        "edição", "publicação", "sourcebook", "campanha", "aventura",
        "cenário", "podcast", "vídeo", "entrevista", "blog",
        "site", "referência", "wiki", "fonte",
    ],
    "Cronologia": [
        "era", "idade", "calendário", "estação", "semana", "dia",
        "ano", "século", "milênio", "timeline", "cronologia",
        "tempo sagrado", "dark season", "storm season",
    ],
}

# Entidades conhecidas (para linkagem cruzada)
KNOWN_ENTITIES = set()

# ─── Dataclasses ────────────────────────────────────────────────────────────

@dataclass
class Entity:
    """Representa uma entidade extraída do fonte."""
    name: str
    category: str
    tags: list = field(default_factory=list)
    summary: str = ""
    content_sections: list = field(default_factory=list)
    cross_refs: list = field(default_factory=list)
    source_file: str = ""
    is_new: bool = True
    existing_file: Optional[str] = None

@dataclass
class IngestionResult:
    """Resultado completo da ingestão."""
    source_file: str
    source_title: str
    source_author: str
    source_published: str
    entities_new: list = field(default_factory=list)
    entities_updated: list = field(default_factory=list)
    facts_extracted: list = field(default_factory=list)
    log_entry: str = ""

# ─── Funções Auxiliares ─────────────────────────────────────────────────────

def load_known_entities():
    """Carrega entidades existentes do index.md."""
    global KNOWN_ENTITIES
    if not INDEX_FILE.exists():
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Extrai títulos de páginas do index (padrão: [[Nome da Página]])
    wiki_links = re.findall(r'\[\[([^\]]+)\]\]', content)
    KNOWN_ENTITIES = set(wiki_links)

    # Também extrai da primeira coluna das tabelas do index
    # Padrão: | [[Nome]] | ...
    table_entries = re.findall(r'\|\s*\[\[([^\]]+)\]\]\s*\|', content)
    KNOWN_ENTITIES.update(table_entries)

def classify_entity(name: str, context: str) -> str:
    """Classifica uma entidade usando heurística de palavras-chave."""
    context_lower = context.lower()
    name_lower = name.lower()

    scores = {cat: 0 for cat in CATEGORIAS}

    for cat, keywords in CAT_KEYWORDS.items():
        for kw in keywords:
            if kw in context_lower or kw in name_lower:
                scores[cat] += 1

    # Fallbacks baseados em padrões de nome
    if scores["Entidade"] == 0 and scores["Localização"] == 0:
        # Nomes próprios (capitalizados, múltiplas palavras) tendem a ser Entidade
        if re.match(r'^[A-ZÁÀÂÃÉÈÊÍÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]+(\s+[A-ZÁÀÂÃÉÈÊÍÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]+)+$', name):
            scores["Entidade"] += 2  # Peso maior para nomes próprios

    # Entidades com "God", "Deus", "Deusa", "Spirit" → Entidade
    if any(w in name_lower for w in ["god", "deus", "deusa", "spirit", "fetch", "bear god"]):
        scores["Entidade"] += 3

    # Entidades com "Book", "Text" → Conceito ou Fonte
    if "book" in name_lower:
        scores["Conceito"] += 1

    # Entidades com nomes de pessoas (padrão nome+sobrenome) → Entidade
    if len(name.split()) >= 2 and all(w[0].isupper() for w in name.split()):
        scores["Entidade"] += 1

    # Entidades com "Era", "Age", "Period" → Cronologia
    if any(w in name_lower for w in ["era", "age", "period", "idade"]):
        scores["Cronologia"] += 2

    # Entidades com "Engine", "Castings", "Games" → Fonte (empresas/produtos)
    if any(w in name_lower for w in ["engine", "castings", "games", "publishing", "press"]):
        scores["Fonte"] += 2

    # Entidades com "Maps", "Map" → Fonte
    if "map" in name_lower:
        scores["Fonte"] += 1

    # Insetos, espécies → Cultura
    if any(w in context_lower for w in ["inseto", "insect", "espécie", "species", "sentient"]):
        scores["Cultura"] += 2

    # Pessoas que fundaram cidades → Entidade
    if any(w in context_lower for w in ["fundaram", "fundou", "fundador", "founder", "founded"]):
        scores["Entidade"] += 2

    # Reis, governantes → Entidade
    if any(w in context_lower for w in ["rei", "king", "rainha", "queen", "governou", "ruled"]):
        scores["Entidade"] += 2

    # Se nenhum score > 0, default para Conceito
    best_cat = max(scores, key=scores.get)
    if scores[best_cat] == 0:
        return "Conceito"

    return best_cat

def extract_summary(text: str, max_sentences: int = 3) -> str:
    """Extrai um resumo das primeiras frases relevantes."""
    # Pega o primeiro parágrafo não-vazio
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return ""

    first = paragraphs[0]
    # Remove markdown formatting
    first = re.sub(r'\[!\[.*?\]\(.*?\)\]', '', first)  # remove images
    first = re.sub(r'\*\*(.*?)\*\*', r'\1', first)     # remove bold
    first = re.sub(r'\*(.*?)\*', r'\1', first)          # remove italic
    first = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', first)   # remove links, keep text

    # Limita a max_sentences
    sentences = re.split(r'(?<=[.!?])\s+', first)
    return ' '.join(sentences[:max_sentences])

def extract_facts_for_entity(name: str, content: str) -> list:
    """Extrai fatos/sentenças sobre uma entidade do conteúdo."""
    facts = []
    lines = content.split("\n")

    for i, line in enumerate(lines):
        # Busca menções ao nome da entidade
        if name.lower() in line.lower():
            # Pega a linha e contexto (linhas adjacentes)
            context_lines = []
            for j in range(max(0, i-1), min(len(lines), i+3)):
                ctx = lines[j].strip()
                if ctx and not ctx.startswith("![](") and not ctx.startswith("---"):
                    context_lines.append(ctx)

            fact_text = " ".join(context_lines)
            # Limpa markdown
            fact_text = re.sub(r'\*\*(.*?)\*\*', r'\1', fact_text)
            fact_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', fact_text)
            fact_text = re.sub(r'#{1,6}\s*', '', fact_text)

            if len(fact_text) > 20 and name.lower() in fact_text.lower():
                facts.append(fact_text)

    return facts[:10]  # Limita a 10 fatos

def extract_cross_refs(name: str, content: str) -> list:
    """Extrai referências cruzadas (wiki links) do contexto da entidade."""
    cross_refs = set()
    lines = content.split("\n")

    for i, line in enumerate(lines):
        if name.lower() in line.lower():
            # Busca wiki links nas linhas próximas
            for j in range(max(0, i-2), min(len(lines), i+4)):
                links = re.findall(r'\[\[([^\]]+)\]\]', lines[j])
                for link in links:
                    if link.lower() != name.lower():
                        cross_refs.add(link)

    # Remove a própria entidade e limita
    cross_refs.discard(name)
    return sorted(cross_refs)[:15]

def extract_tags(name: str, content: str) -> list:
    """Extrai tags relevantes para uma entidade."""
    tags = set()
    lines = content.split("\n")

    for line in lines:
        if name.lower() in line.lower():
            line_lower = line.lower()
            for cat, keywords in CAT_KEYWORDS.items():
                for kw in keywords:
                    if kw in line_lower and len(kw) > 3:
                        tags.add(kw)

    return sorted(tags)[:10]

# ─── Parser do Fonte ────────────────────────────────────────────────────────

def parse_frontmatter(content: str) -> dict:
    """Extrai o frontmatter YAML de um arquivo markdown."""
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}

    fm = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm

def extract_sections(content: str) -> list:
    """Extrai seções do conteúdo (headers e seus parágrafos)."""
    sections = []
    lines = content.split("\n")

    current_header = None
    current_content = []

    for line in lines:
        header_match = re.match(r'^(#{2,4})\s+(.+)$', line)
        if header_match:
            if current_header:
                sections.append({
                    "header": current_header,
                    "content": "\n".join(current_content).strip()
                })
            current_header = header_match.group(2)
            current_content = []
        else:
            current_content.append(line)

    if current_header:
        sections.append({
            "header": current_header,
            "content": "\n".join(current_content).strip()
        })

    return sections

def extract_entities_from_content(content: str) -> list:
    """Extrai entidades candidatas do conteúdo usando múltiplas heurísticas."""
    candidates = []

    # 1. Wiki links [[Nome]] — sempre válidos
    wiki_links = re.findall(r'\[\[([^\]]+)\]\]', content)
    for link in wiki_links:
        candidates.append({
            "name": link,
            "source": "wiki_link",
            "is_known": link in KNOWN_ENTITIES
        })

    # 2. Bold terms **Nome** que parecem entidades (exclui ênfase comum)
    bold_terms = re.findall(r'\*\*([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][^\*]{2,80})\*\*', content)
    bold_skip = {"First", "Second", "Third", "New", "Old", "Great", "High", "Low",
                 "Dark", "Light", "Red", "Blue", "White", "Black", "Golden",
                 "Note", "Important", "Warning", "Tip", "See", "Also",
                 "Disclaimer", "Copyright", "Art by", "©"}
    for term in bold_terms:
        term = term.strip()
        # Skip se começa com palavras de skip
        first_word = term.split()[0]
        if first_word in bold_skip:
            continue
        # Skip se é muito genérico
        if len(term) < 4:
            continue
        if term not in KNOWN_ENTITIES:
            candidates.append({
                "name": term,
                "source": "bold_term",
                "is_known": False
            })

    # 3. Headers — mas filtra os de newsletter boilerplate
    newsletter_headers = {
        "Chaosium News", "Jonstown Compendium", "Jeff's Notes",
        "Community Roundup", "Elsewhere on Arachne Solara's Web",
        "Thank you for reading", "God Learner Sorcery",
        "Recent Well of Daliath Additions",
    }
    headers = re.findall(r'^#{2,4}\s+(.+)$', content, re.MULTILINE)
    for header in headers:
        header = header.strip()
        if header in newsletter_headers:
            continue
        if len(header) > 2 and header not in KNOWN_ENTITIES:
            candidates.append({
                "name": header,
                "source": "header",
                "is_known": False
            })

    # 4. Nomes próprios em contexto de definição
    # Padrões: "X era...", "X foi...", "X é...", "X nasceu...", "X fundou..."
    definition_patterns = [
        r'(?:^|\n)\*\*?([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]{2,}(?:\s+[A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]+){0,4})\*\*?\s+(?:era|foi|é|nasceu|fundou|liderou|derrotou|conquistou|tornou-se|criou|inventou|descobriu)',
        r'(?:^|\n)(?:O|A|Os|As)\s+\*\*?([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]{2,}(?:\s+[A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]+){0,4})\*\*?',
        r'chamavam-se\s+(?:os\s+)?\*\*?([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]{2,})\*\*?',
        r'fundaram\s+(?:a\s+)?(?:cidade\s+de\s+)?\*\*?([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]{2,})\*\*?',
        r'rei\s+(?:seshnelano|de\s+\w+)\s+\*\*?([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]+)\*\*?',
        r'conhecido\s+(?:como\s+)?\*\*?([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][^\*]{2,40})\*\*?',
    ]
    for pattern in definition_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            match = match.strip()
            if len(match) > 3 and match not in KNOWN_ENTITIES:
                candidates.append({
                    "name": match,
                    "source": "definition",
                    "is_known": False
                })

    # 5. Entidades mencionadas em listas ou tabelas
    list_items = re.findall(r'^[-*]\s+\*\*?([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]{2,}(?:\s+[A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]+){0,3})\*\*?', content, re.MULTILINE)
    for item in list_items:
        item = item.strip()
        if len(item) > 3 and item not in KNOWN_ENTITIES:
            candidates.append({
                "name": item,
                "source": "list_item",
                "is_known": False
            })

    # 6. Nomes próprios em contexto semântico (mais agressivo)
    # Busca nomes que aparecem perto de palavras-chave de definição
    semantic_contexts = [
        (r'([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]{2,}(?:\s+[a-záàâãéèêíóôõöúüñ]+){0,3})\s+(?:era|eram|foi|foram|é|são|nasceu|fundou|fundaram|liderou|criou|inventou)', "semantic"),
        (r'(?:os|as|o|a)\s+([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]{2,}(?:\s+[a-záàâãéèêíóôõöúüñ]+){0,3})\s+(?:eram|são|foram)', "semantic"),
        (r'chamavam-se\s+(?:os\s+)?([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]{2,})', "semantic"),
        (r'fundaram\s+(?:a\s+)?(?:cidade\s+de\s+)?([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]{2,})', "semantic"),
        (r'rei\s+\w+\s+([A-ZÁÀÂÃÉÈÊÍÓÔÕÖÚÜ][a-záàâãéèêíóôõöúüñ]+)\s+(?:filho|filha)', "semantic"),
    ]
    for pattern, source_type in semantic_contexts:
        matches = re.findall(pattern, content)
        for match in matches:
            match = match.strip()
            if len(match) < 3:
                continue
            # Filtra palavras muito comuns
            skip = {"The", "This", "That", "These", "Those", "First", "Second", "Third",
                    "New", "Old", "Great", "High", "Low", "Dark", "Light", "Red",
                    "Blue", "White", "Black", "Golden", "Many", "Some", "Most",
                    "Other", "Another", "Each", "Every", "All", "Both", "Few",
                    "Several", "Such", "What", "Which", "Who", "Whose", "Where",
                    "When", "How", "Why", "Not", "But", "And", "Or", "Nor",
                    "For", "Yet", "So", "If", "Then", "Than", "Too", "Very",
                    "Just", "Only", "Even", "Also", "Still", "Already", "Always",
                    "Never", "Often", "Sometimes", "Usually", "Generally",
                    "Well", "Good", "Bad", "Big", "Small", "Long", "Short",
                    "Young", "Rich", "Poor", "Free", "True", "False", "Real",
                    "Fake", "Same", "Different", "Next", "Last", "Past",
                    "Present", "Future", "Here", "There", "Everywhere",
                    "Nowhere", "Somewhere", "Anywhere", "Nothing", "Everything",
                    "Something", "Anything", "Nobody", "Everybody", "Somebody",
                    "Anybody", "None", "One", "Two", "Three", "Four", "Five",
                    "Six", "Seven", "Eight", "Nine", "Ten", "Hundred", "Thousand",
                    "Million", "Billion", "Trillion", "Zero", "Half", "Quarter",
                    "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth",
                    "Ninth", "Tenth", "First", "Second", "Third", "Fourth",
                    "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth",
                    "About", "Above", "Across", "After", "Against", "Along",
                    "Among", "Around", "Before", "Behind", "Below", "Beneath",
                    "Beside", "Between", "Beyond", "During", "Except", "Inside",
                    "Into", "Near", "Onto", "Outside", "Over", "Past", "Since",
                    "Through", "Throughout", "Till", "Toward", "Under", "Until",
                    "Upon", "Within", "Without", "According", "As", "At", "By",
                    "Down", "From", "In", "Of", "Off", "On", "Out", "To", "Up",
                    "With", "Via", "Per", "Minus", "Plus", "Versus", "Vs"}
            first_word = match.split()[0]
            if first_word in skip:
                continue
            if match not in KNOWN_ENTITIES:
                candidates.append({
                    "name": match,
                    "source": source_type,
                    "is_known": False
                })

    # Deduplica por nome (case-insensitive), mantendo a fonte de maior prioridade
    priority = {"wiki_link": 0, "definition": 1, "bold_term": 2, "header": 3, "list_item": 4}
    seen = {}
    for c in candidates:
        key = c["name"].lower()
        if key not in seen or priority.get(c["source"], 99) < priority.get(seen[key]["source"], 99):
            seen[key] = c

    return sorted(seen.values(), key=lambda x: priority.get(x["source"], 99))

# ─── Geração de Páginas ─────────────────────────────────────────────────────

def generate_wiki_page(entity: Entity, source_info: dict) -> str:
    """Gera o conteúdo de uma página wiki usando o template."""
    today = date.today().isoformat()
    source_path = source_info.get("file_path", entity.source_file)

    # Constrói o conteúdo
    sections_text = ""
    for section in entity.content_sections:
        sections_text += f"\n### {section['header']}\n{section['content']}\n"

    # Referências cruzadas
    cross_refs_text = ""
    for ref in entity.cross_refs:
        cross_refs_text += f"- [[{ref}]]\n"
    if not cross_refs_text:
        cross_refs_text = "- <!-- Adicionar referências cruzadas -->\n"

    # Tags
    tags_str = ", ".join(f'"{t}"' for t in entity.tags) if entity.tags else '"tag_pendente"'

    page = f"""---
title: "{entity.name}"
category: "{entity.category}"
tags: [{tags_str}]
sources: ["{source_path}"]
last_updated: {today}
status: draft
---

# {entity.name}

## Resumo
{entity.summary}

## Conteúdo
{sections_text}

## Referências Cruzadas
{cross_refs_text}

## Referências
- Fonte: [{source_info.get('title', entity.source_file)}]({source_path})

## Questões em Aberto
- [ ] Revisar e expandir conteúdo
- [ ] Adicionar referências cruzadas relevantes
- [ ] Verificar consistência com outras páginas
"""
    return page

def check_existing_page(name: str) -> Optional[str]:
    """Verifica se já existe uma página para esta entidade."""
    # Busca por nome exato
    for f in WIKI_DIR.glob("*.md"):
        if f.name in ("index.md", "log.md"):
            continue
        # Compara sem .md e case-insensitive
        if f.stem.lower() == name.lower():
            return str(f)
    return None

# ─── Pipeline Principal ─────────────────────────────────────────────────────

def ingest_source(source_path: str, dry_run: bool = False) -> IngestionResult:
    """Pipeline completo de ingestão de um arquivo fonte."""
    source_path = Path(source_path)
    if not source_path.exists():
        # Tenta como path relativo ao ROOT
        source_path = ROOT / source_path
    if not source_path.exists():
        print(f"ERRO: Arquivo não encontrado: {source_path}")
        sys.exit(1)

    # Carrega entidades conhecidas
    load_known_entities()

    # Lê o fonte
    with open(source_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # Parser frontmatter
    fm = parse_frontmatter(raw_content)
    source_title = fm.get("title", source_path.stem)
    source_author = fm.get("author", "Desconhecido")
    source_published = fm.get("published", "Desconhecida")

    # Remove frontmatter do conteúdo para análise
    content = re.sub(r'^---\n.*?\n---\n?', '', raw_content, flags=re.DOTALL)

    # Extrai seções
    sections = extract_sections(content)

    # Extrai entidades candidatas
    raw_entities = extract_entities_from_content(content)

    print(f"\n{'='*80}")
    print(f"INGESTÃO: {source_title}")
    print(f"Fonte: {source_path}")
    print(f"Entidades candidatas encontradas: {len(raw_entities)}")
    print(f"{'='*80}\n")

    result = IngestionResult(
        source_file=str(source_path),
        source_title=source_title,
        source_author=source_author,
        source_published=source_published,
    )

    # Processa cada entidade candidata
    for candidate in raw_entities:
        name = candidate["name"]

        # Pula entidades muito curtas ou genéricas
        if len(name) < 3:
            continue

        # Skip palavras muito comuns
        skip = {"The", "A", "O", "Um", "Uma", "This", "That", "These", "Those",
                "First", "Second", "Third", "New", "Old", "Great", "High", "Low",
                "Dark", "Light", "Red", "Blue", "White", "Black", "Golden",
                "Jeff Richard", "Facebook", "Twitter", "YouTube", "DriveThruRPG",
                "Chaosium", "RuneQuest", "Glorantha", "Dragon Pass", "Sartar",
                "Jonstown Compendium", "Well of Daliath", "God Learners",
                "Journal of Runic Studies", "Ludovic", "Jeff", "Greg Stafford",
                # Seções de newsletter (não são entidades)
                "Chaosium News", "Community Roundup", "Thank you for reading",
                "Jeff's Notes", "Jonstown Compendium", "Elsewhere on Arachne Solara's Web",
                "Gloranthan Maps", "Recent Well of Daliath Additions",
                "Starter Set Pre-gen Miniatures", "Glorantha Skirmish War Updates",
                "Painted Mad Knight Pre-gens", "Felix Figure Paintings' Gloranthan Works",
                "RuneQuest Year Zero Podcast",
                # Títulos genéricos de seções
                "Memes in the Second Age", "Summarizing the Second Age",
                "How Mythology Underpins Glorantha",
                "Teaser of the Periplus of Southern Genertela",
                "Cults Friendly or Neutral to Chaos",
                "To Hunt a God", "Holiday Dorastor: Joulupukki",
                # Falsos positivos comuns
                "Wars", "War", "Battle", "Fight", "Conflict",
        }
        if name in skip:
            continue

        # Verifica se já existe página
        existing = check_existing_page(name)
        is_new = existing is None

        # Extrai fatos e contexto
        facts = extract_facts_for_entity(name, content)
        if not facts:
            continue  # Pula se não encontrou fatos relevantes

        cross_refs = extract_cross_refs(name, content)
        tags = extract_tags(name, content)

        # Classifica
        context_text = " ".join(facts[:3])
        category = classify_entity(name, context_text)

        # Resumo
        summary = extract_summary(facts[0] if facts else content)

        # Seções relevantes
        relevant_sections = []
        for section in sections:
            if name.lower() in section["content"].lower() or name.lower() in section["header"].lower():
                relevant_sections.append(section)

        try:
            rel_path = str(source_path.relative_to(ROOT))
        except ValueError:
            rel_path = str(source_path)
        entity = Entity(
            name=name,
            category=category,
            tags=tags,
            summary=summary,
            content_sections=relevant_sections,
            cross_refs=cross_refs,
            source_file=rel_path,
            is_new=is_new,
            existing_file=existing,
        )

        if is_new:
            result.entities_new.append(entity)
        else:
            result.entities_updated.append(entity)

    # Gera log entry
    new_count = len(result.entities_new)
    updated_count = len(result.entities_updated)
    result.log_entry = (
        f"## [{date.today().isoformat()}] ingest | Processado "
        f'"{source_title}" — {new_count} páginas criadas, '
        f'{updated_count} páginas atualizadas. Index e log atualizados.'
    )

    return result

def write_pages(result: IngestionResult, dry_run: bool = False):
    """Escreve as páginas geradas no filesystem."""
    if dry_run:
        print("\n[DRY RUN] Nenhuma página será escrita.\n")
        return

    source_info = {
        "title": result.source_title,
        "file_path": result.source_file,
    }

    # Páginas novas
    for entity in result.entities_new:
        page_content = generate_wiki_page(entity, source_info)
        # Sanitiza nome do arquivo
        filename = entity.name.replace("/", "-").replace("\\", "-")
        filepath = WIKI_DIR / f"{filename}.md"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(page_content)
        print(f"  ✓ Criada: {filepath.name}")

    # Páginas atualizadas (apenas reporta, não sobrescreve)
    for entity in result.entities_updated:
        print(f"  ↻ Atualizar: {entity.name} (em {entity.existing_file})")
        print(f"    Fatos novos: {len(entity.content_sections)} seções relevantes")

def print_report(result: IngestionResult):
    """Imprime relatório detalhado da ingestão."""
    print(f"\n{'='*80}")
    print(f"RELATÓRIO DE INGESTÃO")
    print(f"{'='*80}")
    print(f"Fonte: {result.source_title}")
    print(f"Publicado: {result.source_published}")
    print(f"Novas páginas: {len(result.entities_new)}")
    print(f"Páginas para atualizar: {len(result.entities_updated)}")
    print(f"{'='*80}")

    if result.entities_new:
        print(f"\n📄 NOVAS PÁGINAS ({len(result.entities_new)}):")
        for e in result.entities_new:
            print(f"  • {e.name} [{e.category}]")
            if e.tags:
                print(f"    Tags: {', '.join(e.tags[:5])}")
            if e.cross_refs:
                print(f"    Referências: {', '.join(e.cross_refs[:5])}")

    if result.entities_updated:
        print(f"\n🔄 ATUALIZAR ({len(result.entities_updated)}):")
        for e in result.entities_updated:
            print(f"  • {e.name}")
            if e.content_sections:
                print(f"    +{len(e.content_sections)} seções novas")

    print(f"\n📝 LOG ENTRY:")
    print(f"  {result.log_entry}")
    print(f"{'='*80}\n")

def export_json(result: IngestionResult, output_path: str):
    """Exporta resultado como JSON para revisão."""
    data = {
        "source": {
            "title": result.source_title,
            "file": result.source_file,
            "author": result.source_author,
            "published": result.source_published,
        },
        "new_entities": [
            {
                "name": e.name,
                "category": e.category,
                "tags": e.tags,
                "summary": e.summary,
                "cross_refs": e.cross_refs,
                "sections": [{"header": s["header"], "content_preview": s["content"][:200]} for s in e.content_sections],
            }
            for e in result.entities_new
        ],
        "updated_entities": [
            {
                "name": e.name,
                "existing_file": e.existing_file,
                "new_sections": len(e.content_sections),
            }
            for e in result.entities_updated
        ],
        "log_entry": result.log_entry,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"JSON exportado: {output_path}")

# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingestão automatizada de fontes para Glorantha KB")
    parser.add_argument("source", help="Caminho do arquivo fonte em /raw/")
    parser.add_argument("--dry-run", action="store_true", help="Não escreve arquivos, apenas mostra relatório")
    parser.add_argument("--json", type=str, help="Exporta resultado como JSON para revisão")
    parser.add_argument("--entities", nargs="+", help="Lista de entidades para extrair manualmente (além das automáticas)")
    parser.add_argument("--min-facts", type=int, default=1, help="Mínimo de fatos para considerar entidade (default: 1)")
    args = parser.parse_args()

    result = ingest_source(args.source, dry_run=args.dry_run)

    # Adiciona entidades manuais se especificadas
    if args.entities:
        content = ""
        with open(result.source_file, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r'^---\n.*?\n---\n?', '', content, flags=re.DOTALL)

        for name in args.entities:
            existing = check_existing_page(name)
            facts = extract_facts_for_entity(name, content)
            if not facts:
                print(f"  ⚠ Sem fatos encontrados para '{name}', pulando")
                continue

            cross_refs = extract_cross_refs(name, content)
            tags = extract_tags(name, content)
            category = classify_entity(name, " ".join(facts[:3]))
            summary = extract_summary(facts[0])

            sections = extract_sections(content)
            relevant_sections = [s for s in sections if name.lower() in s["content"].lower() or name.lower() in s["header"].lower()]

            try:
                rel_path = str(Path(result.source_file).relative_to(ROOT))
            except ValueError:
                rel_path = result.source_file

            entity = Entity(
                name=name,
                category=category,
                tags=tags,
                summary=summary,
                content_sections=relevant_sections,
                cross_refs=cross_refs,
                source_file=rel_path,
                is_new=(existing is None),
                existing_file=existing,
            )

            if entity.is_new:
                result.entities_new.append(entity)
            else:
                result.entities_updated.append(entity)

    print_report(result)

    if args.json:
        export_json(result, args.json)

    if not args.dry_run:
        write_pages(result)
        print("\nPróximos passos:")
        print("  1. Revisar páginas geradas")
        print("  2. Atualizar wiki/index.md manualmente")
        print("  3. Append em wiki/log.md")
        print("  4. python scripts/sync_readme.py")
        print("  5. git commit")

if __name__ == "__main__":
    main()
