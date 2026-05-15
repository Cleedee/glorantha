#!/usr/bin/env python3
"""Verifica quais arquivos em raw/clippings ainda não foram ingeridos na wiki."""

import os
from pathlib import Path

ROOT = Path("/home/claudio/Projetos/glorantha")
CLIPPINGS_DIR = ROOT / "raw" / "clippings"
LOG_FILE = ROOT / "wiki" / "log.md"

# Mapeamento manual de arquivos que foram ingeridos com nomes diferentes no log
INGESTED_ALIASES = {
    "Welcome to Boldhome": "Welcome to Boldhome",
    "Appendix N": "Appendix N",
    "Glorantha": "Glorantha",
    "Hub do Cláudio": "Hub do Cláudio",
    "Layout of the Big Rubble": "Big Rubble",
    "Levels of The Big Rubble": "Big Rubble",
    "Notes on the Big Rubble": "Big Rubble",
    "QuestWorlds e Glorantha": "QuestWorlds",
    "Review The Lunar Way": "Lunar Way",
    "Runeblog": "Runeblog",
    "THE LUNAR WAY A REVIEW": "Lunar Way",
    "The fundamental difference between RuneQuest and 5e": "RuneQuest vs D&D",
    "Update on what's happening with RQ": "Update on RQ",
}

def main():
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log_content = f.read().lower()

    clippings = sorted(CLIPPINGS_DIR.glob("*.md"))
    nao_ingeridos = []
    ingeridos = []

    for clip in clippings:
        nome = clip.stem  # nome sem .md
        log_lower = log_content

        # Verificar se o nome (ou parte significativa) aparece no log
        # Usa palavras-chave únicas do nome
        found = False

        # Primeiro: check direto do nome
        if nome.lower() in log_lower:
            found = True
        else:
            # Segundo: check por partes significativas
            # Remove artigos/preposições e pega tokens com 5+ chars
            skip = {"the", "and", "for", "you", "are", "but", "not", "with",
                    "uma", "das", "dos", "que", "em", "de", "no", "na", "do",
                    "da", "um", "e", "a", "o", "se", "ou", "ao", "aos", "as"}
            tokens = [t.lower().strip(" .,!?;:'\"()") for t in nome.split()]
            keywords = [t for t in tokens if len(t) >= 5 and t not in skip]

            # Se 3+ keywords aparecem no log, consideramos ingerido
            matches = sum(1 for k in keywords if k in log_lower)
            if matches >= 3:
                found = True

        if found:
            ingeridos.append(nome)
        else:
            nao_ingeridos.append(nome)

    print(f"\n{'='*80}")
    print(f"TOTAL DE CLIPPINGS: {len(clippings)}")
    print(f"INGERIDOS: {len(ingeridos)}")
    print(f"NAO INGERIDOS: {len(nao_ingeridos)}")
    print(f"{'='*80}")

    if nao_ingeridos:
        print(f"\nARQUIVOS NAO INGERIDOS ({len(nao_ingeridos)}):\n")
        for i, nome in enumerate(nao_ingeridos, 1):
            print(f"  {i:3d}. {nome}.md")
        print()

if __name__ == "__main__":
    main()
