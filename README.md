# 🌍 Glorantha Knowledge Base

Uma **base de conhecimento colaborativa** sobre o universo fictício de **Glorantha**, o cenário de fantasia criado por Greg Stafford para os jogos *RuneQuest*, *HeroQuest* e *QuestWorlds*.

Este repositório segue a metodologia **"Karpathy Method"** para manutenção de wikis orientadas por LLM: fontes imutáveis em `/raw`, wiki viva em `/wiki`, e revisão humana em cada etapa.

---

## 📖 Sobre Glorantha

Glorantha é um dos cenários de RPG mais antigos e ricamente detalhados do mundo. Criado por **Greg Stafford** na década de 1960, é o cenário padrão de **RuneQuest** e abrange:

- **Mitologia complexa** com panteões vivos e interativos
- **Geografia detalhada**: Sartar, Prax, Pavis, Dorastor, Passagem do Dragão e muito mais
- **Sistemas de magia** únicos: magia rúnica, xamanismo, feitiçaria e heroquestes
- **Culturas diversas**: Orlanthi, Imperadores Lunares, trolls (Uz), elfos, anões (Mostali), nômades de Prax
- **História épica** desde o Tempo dos Deuses até as Hero Wars

---

## 📂 Estrutura do Repositório

```
glorantha/
├── README.md              ← Você está aqui
├── qwen.md                ← Schema operacional (constituição do sistema)
├── raw/                   ← Fontes imutáveis (documentos, artigos, clippings)
│   ├── clippings/         ← Artigos de blogs, entrevistas, notícias
│   └── notas/             ← Notas e roadmaps de publicações
├── wiki/                  ← Wiki viva mantida pelo sistema
│   ├── index.md           ← Índice mestre de todas as páginas
│   ├── log.md             ← Log cronológico de todas as ações
│   ├── assets/            ← Imagens e mídia
│   └── *.md               ← 130+ páginas individuais
└── .gitignore
```

### Regras de Camadas

| Camada | Permissão | Descrição |
|--------|-----------|-----------|
| `/raw` | **Somente leitura** pelo LLM | Fonte imutável de verdade |
| `/wiki` | **Escrita** pelo LLM | Artefato vivo, atualizado por ingestão |

---

## 🗂️ Categorias da Wiki

A wiki está organizada em **8 categorias**:

| Categoria | Conteúdo | Páginas |
|-----------|----------|---------|
| **Entidade** | Deuses, heróis, figuras históricas, NPCs | 31 |
| **Localização** | Regiões, cidades, templos, marcos geográficos | 10 |
| **Evento** | Batalhas, heroquestes, marcos temporais | 1 |
| **Magia** | Feitiços, runas, sistemas mágicos | 0 |
| **Conceito** | Ideias abstratas, mecânicas, cosmologia | 3 |
| **Fonte** | Livros, suplementos, campanhas, aventuras | 93 |
| **Cultura** | Povos, tribos, nações, organizações | 9 |
| **Cronologia** | Linhas temporais, eras, calendários | 1 |

---

## 🔍 Como Navegar

1. **Comece pelo [`wiki/index.md`](wiki/index.md)** — índice mestre com todas as páginas organizadas por categoria
2. **Siga os links internos** — cada página usa links estilo Obsidian `[[Nome da Página]]`
3. **Consulte as referências** — cada página lista suas fontes originais em `/raw/`
4. **Verifique o status** — cada página tem um campo `status` no frontmatter:
   - `draft` — Rascunho inicial
   - `em_revisao` — Aguardando revisão
   - `estavel` — Conteúdo revisado e confiável

---

## 🏗️ Como Foi Construída

### Metodologia: Karpathy Method

Este projeto segue o modelo de **Knowledge Base assistida por LLM** com as seguintes características:

1. **Fontes imutáveis** — Documentos em `/raw` nunca são modificados pelo LLM
2. **Ingestão um-a-um** — Um arquivo fonte por vez, com revisão humana obrigatória
3. **Schema persistente** — `qwen.md` define regras, templates e workflows
4. **Log auditável** — `wiki/log.md` registra todas as ações cronologicamente
5. **Versionamento** — Git com commits convencionais (`feat:`, `fix:`, `docs:`, `chore:`)

### Fluxo de Ingestão

```
[raw/source.md]
    ↓  (leitura — um arquivo por vez)
[Extração de fatos, entidades, conceitos]
    ↓
[Rascunho/atualização de páginas em /wiki]
    ↓
[Apresentar diff + resumo ao humano]
    ↓  (aguardar aprovação explícita)
[Atualizar wiki/index.md]
[Append em wiki/log.md]
[git commit com prefixo adequado]
```

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Se você é um jogador ou mestre de Glorantha:

### Adicionando Fontes
1. Crie um arquivo `.md` em `raw/clippings/` ou `raw/notas/`
2. Use frontmatter YAML com `title`, `source`, `author`, `published`, `tags`
3. O conteúdo pode ser texto de artigos, notas, entrevistas, etc.

### Corrigindo Páginas
1. Abra uma issue descrevendo o erro ou informação faltante
2. Ou faça um Pull Request com a correção
3. Referencie suas fontes (livros, suplementos, links)

### Convenções de Markdown
- Links internos: `[[Nome da Página]]` (estilo Obsidian)
- Frontmatter YAML obrigatório: `title`, `category`, `tags`, `sources`, `last_updated`, `status`
- Seções: `Resumo`, `Conteúdo`, `Referências Cruzadas`, `Referências`, `Questões em Aberto`

---

## 📊 Estatísticas Atuais

| Métrica | Valor |
|---------|-------|
| Páginas na wiki | ~130 |
| Fontes processadas | 15+ |
| Commits | 11 |
| Última atualização | Abril 2026 |
| Idioma | Português Brasileiro (pt-BR) |

---

## 📜 Licença

Todo o conteúdo da wiki é derivado de fontes de terceiros (artigos, suplementos, entrevistas). As páginas da wiki são **resumos e sínteses** criadas para fins de pesquisa e estudo pessoal.

Para uso comercial de material de Glorantha, consulte a [Chaosium](https://www.chaosium.com/) e os termos do [Jonstown Compendium](https://www.chaosium.com/jonstowncompendium).

---

## 🔗 Links Úteis

- [Chaosium](https://www.chaosium.com/) — Editora oficial de Glorantha
- [Jonstown Compendium](https://www.drivethrurpg.com/cc/29/jonstown) — Material de fãs no DriveThruRPG
- [Well of Daliath](https://wellofdaliath.chaosium.com/) — Wiki comunitária de Glorantha
- [Glorantha Wiki (oficial)](https://glorantha.fandom.com/) — Wiki da Chaosium
- [BRP Central](https://basicroleplaying.org/) — Fórum da comunidade Basic Roleplaying

---

> *"Glorantha não é apenas um cenário — é um mundo que se revela a quem o explora."*
