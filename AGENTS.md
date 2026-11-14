# seeq — contexto do projeto

App Windows de **busca de metadados e links de torrents** (não é cliente BitTorrent). Inspirado no conceito do Torlink (MIT, © 2026 bairon.dev), implementado de forma independente. Nome original: **torrentFindr**; renomeado para **seeq** em 11/11/2026.

**Migrado do Codex para o Hermes em 14/11/2026.** Origem (backup, não usar para desenvolvimento): `C:/Users/Renan/Documents/Codex/2026-11-10/referenced-chatgpt-conversation-this-is-an/outputs`. Sessão Codex: `01a1c3c1-aa90-7b13-bea4-3b3a82f2e4a5` (`~/.codex/sessions/2026/11/10/rollout-2026-11-10T01-40-12-*.jsonl`).

## Arquitetura

| Caminho | Papel |
|---|---|
| `core.py` | `Result`, dedup por infohash (hex/Base32), fontes base: Internet Archive, Debian, The Pirate Bay (apibay), Nyaa (RSS) |
| `extra_sources.py` | YTS, EZTV, SubsPlease, FitGirl, EXT.to, 1337x, JackettSource (RuTracker/CGPeers) |
| `catalog_sources.py` | 5 fontes oficiais adicionadas em 13/11: FOSS Torrents, Academic Torrents, Blender Video (PeerTube), Ubuntu, Fedora |
| `search_filters.py` | Filtros inteligentes em linguagem natural (`linux iso últimos 7 dias até 3 GB`), facetas, datas |
| `desktop_backend.py` | Motor local: comandos JSON ↔ estados via stdio para o shell WebView2. Perfil em `%APPDATA%\torrentFindr\dados.json` |
| `seeq_mcp.py` | Servidor MCP stdio (read-only): `list_sources`, `search`. Fontes públicas diretas; não cobre Jackett nem fluxo interativo EXT.to/1337x |
| `browser_import.py` | Importa resultados do navegador integrado |
| `desktop/` | Shell .NET 10 WinForms + WebView2 (`TorrentFindr.Desktop.csproj`, `Program.cs`, `StartupPrompt.cs` = loading de prompt de códigos, `PortablePayload.cs`, `pack_payload.py`, ícone) |
| `embedded-browser/` | Navegador WebView2 dedicado a EXT.to/1337x (`TorrentFindr.Browser.csproj`) → publica em `browser/` |
| `interface/` | UI: `index.html`, `style.css`, `desk.js`, `i18n.js`, assets de marca e backdrop |
| `desktop-app/` | Shell publicado (versão em pasta, **binário regenerável**, fora do git) |
| `browser/` | Navegador integrado publicado (**binário regenerável**, fora do git; exigido pelo `pack_payload.py`) |
| `dist/` | `seeq-Standalone-x64.exe` (~512 MB, build de 13/11/2026; fora do git) |
| `providers/` | Plugins de fonte do usuário (carregados de `%APPDATA%\torrentFindr\providers`) |
| `app.py`, `window_chrome.py`, `desktop_style.py` | Protótipo Tkinter legado — a UI atual é WebView2 |
| `integrations/` | Configs MCP prontas: `hermes.yaml`, `strata.json`, `LEIA-ME.md` |

## Executar

- **Standalone:** `dist/seeq-Standalone-x64.exe` (duplo clique). Embute Python 3.13 + .NET + WebView2 Fixed Version; primeira abertura extrai em `%LOCALAPPDATA%\seeq\standalone\<hash>`.
- **Versão em pasta:** `Iniciar.bat` → `start_desktop.py` → `desktop-app/seeq.exe` (recebe o caminho do Python como argumento). Requer Python 3.10+ e WebView2 Runtime.
- **Dados do usuário:** `%APPDATA%\torrentFindr\dados.json` (config, histórico, favoritos), perfil WebView2 em `%APPDATA%\torrentFindr\webview2`. Não mover/renomear — compatibilidade com instalações existentes.

## Build (SDK .NET 10 + Python 3.10+)

Da raiz do projeto, em PowerShell:

```powershell
# 1. Navegador integrado (gera browser/TorrentFindr.Browser.exe)
dotnet publish embedded-browser/TorrentFindr.Browser.csproj -c Release -r win-x64 --self-contained -o browser -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:EnableCompressionInSingleFile=true

# 2. Payload (Python embeddable + WebView2 Fixed Version + app)
python desktop/pack_payload.py C:/pacotes/python-x64.zip C:/pacotes/WebView2-extraido build/payload.zip

# 3. Executável standalone
$payload = (Resolve-Path build/payload.zip).Path
dotnet publish desktop/TorrentFindr.Desktop.csproj -c Release -r win-x64 --self-contained -o build/standalone -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:DebugType=None "-p:PortablePayload=$payload"
# → build/standalone/seeq.exe ; distribuir como seeq-Standalone-x64.exe

# Shell da versão em pasta (sem payload):
dotnet publish desktop/TorrentFindr.Desktop.csproj -c Release -r win-x64 --self-contained -o desktop-app
```

**Insumos do payload:** ZIP embeddable x64 oficial do Python + CAB Fixed Version x64 do WebView2 (extrair com `expand.exe -F:*`; o diretório precisa conter `msedgewebview2.exe`). Os originais não foram migrados, mas o runtime extraído do build atual está em `%LOCALAPPDATA%\seeq\standalone\2fb69a59cb9e462faa78304c30f77985\` (`engine/` = Python, `webview2-runtime/` = WebView2) e pode ser reempacotado se necessário. O `work/seeq-sources-build/payload.zip` da origem também contém o payload completo do build de 13/11.

## MCP (Hermes / Strata)

- Registrado no Hermes como `mcp_servers.seeq`: `C:/Users/Renan/AppData/Local/Programs/Python/Python313/python.exe -B C:/Users/Renan/seeq/seeq_mcp.py`. Ferramentas: `mcp_seeq_list_sources`, `mcp_seeq_search`. Testar: `hermes mcp test seeq`.
- Strata: mesclar `integrations/strata.json` (atualizar o caminho do script para o novo local).
- Consulta de teste: `debian` apenas em `Debian oficial`, `limit: 3`.

## Estado na migração (13/11/2026)

- 5 fontes novas integradas e testadas ao vivo: busca `linux` retornou 128 resultados; MCP encontrou `Sintel` no Blender Video.
- Executável standalone reconstruído com mensagem de erro de DNS mais clara.
- **Problemas conhecidos:**
  - **EZTV (`eztvx.to`) e FitGirl (`fitgirl-repacks.site`):** os DNS IPv6 configurados no Wi-Fi respondem NXDOMAIN; Google DNS (8.8.8.8) resolve normalmente. Falha é da rede, não do app. Próximo passo: revisar DNS IPv6 do Wi-Fi (AdGuard é suspeito, não confirmado) ou adicionar fallback DoH no app.
  - **Academic Torrents:** catálogo busca e retorna magnets, mas a página de detalhes devolve 403.
  - **EXT.to / 1337x:** HTTP 403 em consulta direta → resolvido pelo navegador integrado (interação do usuário quando há desafio).
  - **RuTracker / CGPeers:** dependem de Jackett local configurado pelo usuário (porta 9117 + chave API em memória por sessão).

## Convenções de UI (preferências do usuário — não regredir)

- Botões minimalistas com ícone (sem palavras); sem bordas finas; janela sem maximizar; barra de título arrastável.
- Tema AMOLED + cor de destaque vívida; título na cor de destaque; ícone interno grande.
- Fade em todas as transições; fundo ilustrado com modo de mistura + intensidade (reduz ao exibir resultados); loading = prompt de códigos.
- Barra de busca com 25% de opacidade em repouso; busca avançada atrás do **+**; filtros inteligentes como etiquetas removíveis, visíveis só após buscar.
- Ícone de ímã por linha; engrenagem discreta junto de fechar/minimizar; log de atividade atrás do ícone de documento.
- Idiomas: pt-BR, en, es, ru, ja, zh. Histórico com remoção por item e limpar tudo (com confirmação).

## Verificação rápida

```bash
python -m compileall -q .          # sintaxe
hermes mcp test seeq               # conexão MCP
# busca real: debian / Debian oficial / limit 3
```

Ao alterar fontes: testar cada integração **ao vivo** (simulações não provam acesso — lição da sessão Codex). Timeout de 15 s por requisição; falha de uma fonte não bloqueia as outras. Sem contorno de CAPTCHA.