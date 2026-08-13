# Glorantha Knowledge Base — Schema Operacional

> **Este arquivo é a constituição do sistema.** Todas as sessões futuras do Qwen Code devem ler este arquivo antes de executar qualquer ação e obedecer rigorosamente às regras aqui definidas.

---

## A. Princípios Fundamentais

### Domínio

Pesquisa profunda, curadoria e síntese do universo fictício de **Glorantha** (mitologia, geografia, facções, sistemas de magia, lore, linhas temporais, cultos, runas, heroquestes).

### Idioma

**Todo o conteúdo da wiki — páginas, resumos, logs, referências cruzadas e artefatos gerados — DEVE ser escrito em Português Brasileiro (pt-BR).** Sem exceções.

### Arquitetura

```
/home/claudio/Projetos/glorantha/
├── constitution.md  ← Este arquivo (constituição, NÃO editar sem motivo)
├── raw/             ← Fonte imutável de verdade (documentos fonte, LOCAL APENAS)
│                      ⚠️ NÃO versionado no git — conteúdo protegido por direitos autorais.
│                      O LLM APENAS LÊ deste diretório.
├── wiki/            ← Artefato vivo mantido pelo LLM.
│   ├── index.md     ← Índice mestre de todas as páginas
│   ├── log.md       ← Log cronológico append-only de todas as ações
│   ├── assets/      ← Imagens e mídia local
│   └── *.md         ← Páginas individuais da wiki
├── scripts/         ← Ferramentas auxiliares de manutenção
│   └── sync_readme.py  ← Sincroniza tabelas do README.md com a wiki
└── .gitignore       ← raw/ ignorado do versionamento
```

**Regra de ouro:** O LLM **lê** de `/raw` e **escreve** em `/wiki`. Nunca o contrário.

**Referências:** Nas páginas wiki, use **URLs originais dos sites de origem** (ex: `https://godlearners.com/...`), nunca caminhos `raw/clippings/...`.

### Modo de Ingestão

Estritamente **um arquivo por vez**, com revisão humana no circuito:

1. Ler **um único** arquivo fonte de `/raw/`.
2. Extrair fatos-chave sobre Glorantha.
3. Rascunhar/atualizar páginas relevantes na wiki.
4. Mostrar resumo + diff das mudanças para o humano.
5. **AGUARDAR** aprovação explícita antes de finalizar e fazer commit.

Nunca processe múltiplos arquivos de uma vez. Sempre pause para revisão.

---

## B. Workflows

### Workflow: Ingest (Ingestão)

```
[raw/source.md]  (arquivo local, NÃO versionado)
    ↓  (leitura — um arquivo por vez)
[Extração manual de fatos, entidades, conceitos pelo LLM]
    ↓
[Rascunho/atualização de páginas em /wiki — escrita curada, página a página]
    ↓  (frontmatter sources: usa URL original do site, nunca raw/clippings/)
[Apresentar diff + resumo ao humano]
    ↓  (aguardar aprovação)
[Atualizar wiki/index.md]
[Append em wiki/log.md]
[python scripts/sync_readme.py]
[git commit com prefixo: feat: / fix: / docs: / chore:]
```

### Workflow: Transcribe (Transcrição de Vídeo)

Para fontes em vídeo (ex: painéis da Chaosium no YouTube), transcrever antes da ingestão.

**Método principal — `youtube-transcript-api`** (busca as legendas existentes do vídeo — automáticas ou manuais — sem API key, sem download de áudio, sem modelo local):

```bash
pip install youtube-transcript-api
```

```python
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

video_id = "aR0wj1SsU1Q"  # apenas o ID, não a URL completa
api = YouTubeTranscriptApi()
fetched = api.fetch(video_id, languages=["en"])  # preferir legenda manual à automática
text = TextFormatter().format_transcript(fetched.to_raw_data())
open("raw/clippings/<nome-do-video>.txt", "w").write(text)
```

- Suporta listar idiomas (`api.list(video_id)`), escolher idioma e traduzir (`translate()`); formatação txt/json/srt/vtt via `TextFormatter`.
- **Não funciona** em vídeos sem legendas, em vídeos com restrição de idade (cookie auth quebrado) ou se o YouTube mudar endpoints internos (library community-patched).

**Método alternativo/fallback — `yt-dlp` + `openai/whisper`** (quando não houver legendas, ou quando a fidelidade de nomes próprios e termos gloranthanos for crítica — o whisper `large-v3` tende a ser mais preciso que as auto-captions do YouTube):

```bash
yt-dlp -f "bestaudio[ext=m4a]" -o "raw/clippings/<nome-do-video>.m4a" "<URL>"
whisper "raw/clippings/<nome-do-video>.m4a" --model large-v3 --language en \
  --output_dir raw/clippings/ --output_format txt
```

Regras:

1. **Escolha do método:** preferir `youtube-transcript-api` por padrão (rápido e leve); usar whisper apenas se `NoTranscriptFound`/`TranscriptsDisabled` ou se a transcrição ficar imprecisa em termos gloranthanos.
2. **Frontmatter:** converter o texto gerado em `.md` com frontmatter (title, source=URL original, author, published, created, description, tags: `["clippings", "transcrição"]`) e **guardar em `/raw/clippings/`** (não versionado). O áudio `.m4a` pode ser removido após a transcrição.
3. **⚠️ Transcrições são imprecisas** — seja auto-caption do YouTube ou whisper, nomes próprios e termos gloranthanos frequentemente saem errados (ex: "Mob" confundido com "Jeff Richard", "On the Royal Road" transcrito como "Under Oil Road"). O LLM **deve** cruzar com o contexto/lore da wiki e registrar discrepâncias nas páginas (campo "Questões em Aberto"), nunca copiar a transcrição crua como fato.
4. Após a transcrição salva, seguir o **Workflow: Ingest** normalmente.

### Workflow: Query (Consulta)

1. Consultar primeiro a wiki (`/wiki/index.md` e páginas relevantes).
2. Priorizar geração de outputs estruturados:
   - **Artigos** em Markdown
   - **Marp slide decks** para apresentações
   - **Scripts Python/Matplotlib** para gráficos/visualizações
   - **Tabelas comparativas**
   - **Linhas temporais**
3. Salvar outputs gerados de volta na wiki para compor conhecimento.

### Workflow: Sync (Sincronização do README)

Sempre que a wiki for modificada (ingestão, criação ou atualização de páginas), **execute o script de sincronização** para manter o `README.md` atualizado:

```bash
python scripts/sync_readme.py
```

O script:
1. Lê o `category` do frontmatter de todas as páginas em `/wiki/` (excluindo `index.md` e `log.md`)
2. Conta páginas por categoria e atualiza a tabela **Categorias da Wiki**
3. Conta commits git, data atual, e atualiza a tabela **Estatísticas Atuais**
4. Re-escreve apenas as duas tabelas no `README.md`, preservando o resto

**Quando executar:** após cada ingestão, antes do commit final.

### Workflow: Lint (Revisão Periódica)

Periodicamente, executar saúde da wiki:

- Buscar contradições entre páginas
- Identificar páginas órfãs (sem backlinks)
- Verificar links quebrados `[[...]]`
- Detectar lore desatualizada ou conflitante
- Sugerir novos ângulos de pesquisa ou fontes faltantes
- Verificar consistência de tags e categorias

---

## C. Indexação e Logging

### `wiki/index.md`

- Catálogo orientado por conteúdo de **todas** as páginas da wiki.
- Organizado por categorias.
- Cada entrada: título, caminho, resumo de 1 linha, tags, status.
- **Atualizado em cada ingestão.** Substitui RAG vetorial nesta escala.

### `wiki/log.md`

- Registro cronológico **append-only** de todas as ações do sistema.
- Formato obrigatório:

```markdown
## [YYYY-MM-DD] tipo_acao | Descrição da ação realizada
```

- Deve ser **grep-parsable**. Exemplos de `tipo_acao`:
  - `ingest` — novo arquivo processado
  - `update` — página existente atualizada
  - `create` — nova página criada
  - `lint` — revisão de saúde executada
  - `setup` — inicialização do sistema

---

## D. Templates e Convenções

### Template de Página da Wiki

Toda página nova deve seguir este template:

```markdown
---
title: "Título da Página"
category: "Categoria"        # Entidade | Localização | Evento | Magia | Conceito | Fonte | Cultura | Cronologia
tags: [tag1, tag2, tag3]
sources: ["https://url-da-fonte-original.com/..."]
last_updated: YYYY-MM-DD
status: draft                # draft | em_revisao | estavel
---

# Título da Página

## Resumo
<!-- 2-3 frases que definem o tema da página. -->

## Conteúdo
<!-- Corpo principal do artigo. Use seções e subseções conforme necessário. -->

### Subseção Relevante
<!-- Detalhamento. -->

## Referências Cruzadas
- [[Página Relacionada 1]]
- [[Página Relacionada 2]]

## Referências
- Fonte: [Nome da fonte](https://url-da-fonte-original.com/...)
- <!-- Outras referências -->

## Questões em Aberto
- [ ] Pergunta ou ponto de investigação pendente
- [ ] Informação conflitante a resolver
```

### Convenções de Linkagem Interna

- Usar **Obsidian-style** `[[Nome da Página]]` para todos os links internos.
- O nome deve corresponder exatamente ao título da página de destino (case-sensitive).
- Links para páginas inexistentes indicam trabalho futuro.

### Categorias Padrão

| Categoria     | Uso                                                        |
| ------------- | ---------------------------------------------------------- |
| `Entidade`    | Deuses, heróis, figuras históricas, NPCs importantes       |
| `Localização` | Regiões, cidades, templos, marcos geográficos              |
| `Evento`      | Batalhas, grandes sessões, heroquestes, marcos temporais   |
| `Magia`       | Feitiços, runas, sistemas mágicos, paths de iluminação     |
| `Conceito`    | Ideias abstratas, mecânicas de jogo, cosmologia            |
| `Fonte`       | Referências externas, livros, artigos, materiais de origem |
| `Cultura`     | Povos, tribos, nações, organizações sociais                |
| `Cronologia`  | Linhas temporais, eras, calendários                        |

### Status de Página

| Status       | Significado                               |
| ------------ | ----------------------------------------- |
| `draft`      | Rascunho inicial, conteúdo incompleto     |
| `em_revisao` | Aguardando revisão humana                 |
| `estavel`    | Conteúdo revisado e considerado confiável |

---

## E. Convenções de Commit

Todos os commits devem usar **Conventional Commits** com prefixos:

| Prefixo     | Quando usar                                           |
| ----------- | ----------------------------------------------------- |
| `feat:`     | Nova página ou conteúdo adicionado à wiki             |
| `fix:`      | Correção de erros, contradições ou informações        |
| `docs:`     | Atualização de index, log, ou documentação do sistema |
| `chore:`    | Manutenção de estrutura, templates, configurações     |
| `refactor:` | Reorganização de conteúdo sem mudança semântica       |
| `lint:`     | Resultado de revisão periódica de saúde               |

**Exemplo:**

```bash
git commit -m "feat: adicionar página sobre o Deus Orlanz"
git commit -m "fix: corrigir data da Grande Sessão no index"
git commit -m "docs: atualizar log e index após ingest de fonte"
```

---

## F. Instruções para Sessões Futuras

1. **Leia este arquivo (`constitution.md`) primeiro.**
2. Verifique o estado atual de `/raw/` (local, não versionado) e `/wiki/`.
3. Se houver arquivos em `/raw/` ainda não processados, siga o workflow de **Ingest**.
4. Se o usuário fizer uma pergunta, siga o workflow de **Query**.
5. Se solicitado, execute o workflow de **Lint**.
6. **Nunca** pule a etapa de revisão humana no workflow de ingestão.
7. Mantenha o idioma **sempre em pt-BR**.
8. **Nunca** use caminhos `raw/clippings/...` como referência nas páginas wiki — use URLs originais dos sites de origem.
9. Ao final de cada sessão, faça commit das mudanças com o prefixo adequado.

---

*Schema versão: 1.2 | Criado em: 2026-04-13 | Atualizado em: 2026-08-12 (Workflow: Transcribe — youtube-transcript-api como método principal, yt-dlp + whisper como fallback)*
