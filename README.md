# IA Agent Developer

Agente local de desenvolvimento com Ollama: planeja, edita arquivos com sandbox, executa comandos seguros, valida e reflete sobre falhas.

## Requisitos
- Python 3.11+
- [Ollama](https://ollama.com/)
- Modelo local recomendado: `qwen2.5-coder:7b` (leve) ou `qwen3-coder:30b` (mais capaz)

## Instalação rápida

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Linux/macOS:

```bash
bash scripts/setup.sh
```

Manual:

```bash
python -m pip install -e ".[dev]"
cp .env.example .env
ollama serve
ollama pull qwen2.5-coder:7b
```

## Execução

```bash
# Nova CLI modular
python -m local_agent "Crie um arquivo demo.txt com hello" --workspace ./sandbox --verbose

# Somente plano
python -m local_agent "Refatore o módulo X" --plan-only

# Dry-run
python -m local_agent "Crie um projeto python demo_py" --dry-run --verbose

# Entrypoint legado
python ollama_agent.py --workspace ./sandbox "Create a file called demo.txt with the content hello"
```

Flags principais: `--workspace`, `--model`, `--planner-model`, `--reflection-model`, `--max-steps`, `--max-task-attempts`, `--command-timeout`, `--dry-run`, `--verbose`, `--debug`, `--plan-only`, `--no-memory`, `--no-git`, `--config`.

## Arquitetura

```text
local_agent/
  agent.py           # loop principal
  planner.py         # plano estruturado
  executor.py        # execução de tools
  validator.py       # testes/build/lint
  reflector.py       # decisão retry/replan/finish
  memory.py          # memória curto/longo prazo (.agent/memory.json)
  project_index.py   # índice lexical/estrutural
  security.py        # sandbox de paths
  ollama_client.py   # cliente HTTP Ollama
  tools/             # filesystem, terminal, patch, search, git, project
```

## Ferramentas
- Arquivos: `read_file`, `read_file_range`, `write_file`, `append_file`, `apply_patch`, `replace_in_file` (legado), `list_directory`, `validate_path`, ...
- Busca: `search_text`, `search_files`, `search_symbol`
- Terminal: `run_command` com classificação de risco e bloqueios
- Projeto: `scaffold_project`, `create_multiple_files`
- Git (somente leitura): `git_status`, `git_diff`, `git_log`, ...

## Segurança
- Paths confinados ao `--workspace` (inclui proteção contra symlink escape)
- Comandos perigosos bloqueados (`rm -rf /`, `git reset --hard`, `curl | sh`, etc.)
- Escrita atômica e backups `.bak` em alterações destrutivas/patch
- `--dry-run` não muta disco nem executa comandos

## Memória
Persistida em `.agent/memory.json` no workspace (desativável com `--no-memory`).

## Testes

```bash
python -m pytest -q
```

Os testes unitários usam mocks e **não** dependem de Ollama.

## Limitações atuais
- Sem embeddings/RAG vetorial
- Patch unified-diff ainda é conservador (melhor usar hunks estruturados)
- Confirmação interativa rica para alto risco ainda é simplificada
- Qualidade depende fortemente do modelo Ollama escolhido

## Roadmap
- Diff/patch unificado mais completo
- Modo interativo REPL
- Políticas de aprovação por tool
- Indexação incremental e cache
- Métricas de custo/latência por etapa
