# seeq — Mesa de pesquisa

Aplicativo Windows de busca de torrents, inspirado no conceito do Torlink e implementado de forma independente. Não é cliente BitTorrent: para baixar conteúdo, instale um cliente compatível e use os links disponíveis. Disponibilidade e direitos de cada item devem ser verificados pelo usuário; a inclusão no Internet Archive não garante autorização para qualquer uso.

## Abrir no Windows

No Windows x64, abra `seeq-Standalone-x64.exe` com duplo clique. Ele inclui Python, .NET e WebView2. Na primeira abertura, o app extrai os componentes em `%LOCALAPPDATA%\seeq\standalone`. O prompt na janela acompanha a inicialização até carregar a interface e o perfil. A busca exige acesso à internet.

Digite, por exemplo, `debian` e pressione Enter ou clique na lupa. Clique no ímã de uma linha para abrir o magnet no cliente BitTorrent padrão. Selecione uma linha para ver os detalhes e passe o mouse sobre os ícones para identificar cada ação.

Na versão em pasta, abra `Iniciar.bat` com Python 3.10 ou superior e o Microsoft Edge WebView2 Runtime instalados.

A engrenagem na barra de título abre **Configurações**. Escolha o idioma da interface, o tema e a cor de destaque. Ative **Fundo ilustrado** para escolher o modo de mistura e a intensidade. O fundo diminui de intensidade ao exibir resultados. O seeq usa `%APPDATA%\torrentFindr\dados.json` para aproveitar as configurações, o histórico e os favoritos existentes.

Em **Histórico**, clique em um termo para pesquisar de novo. Use a lixeira ao lado de um termo para removê-lo ou **Limpar histórico** para esvaziar a lista após confirmar.

Arraste a área livre da barra de título para mover a janela. Durante uma busca, o botão quadrado de **Cancelar busca** preserva os resultados já recebidos. Para substituí-la, digite outro termo e clique na lupa. O ícone de documento à direita da navegação abre o **Log de atividade** da sessão.

## Filtros e datas

- Experimente `linux iso últimos 7 dias até 3 GB` com **Interpretar filtros na busca** ativado na busca avançada. As fontes recebem o termo `linux` e os critérios reconhecidos aparecem como etiquetas removíveis acima da lista.
- Clique no **+** ao lado dos atalhos de data para abrir a busca avançada. Combine publicação, ano do conteúdo, fonte, categoria, idioma, qualidade, formato, tipo de link, tamanho e seeders. As opções das listas mostram a contagem de correspondências nos resultados disponíveis, considerando os demais filtros.
- **Publicação** usa a data informada pela fonte. Quando um torrent aparece em várias fontes, o app conserva a data de cada uma, quando conhecida. Selecione uma fonte para usar a data dela. **Ano do conteúdo** é um campo separado. Resultados sem data aparecem com um traço. Use **Incluir itens sem data no período** para mantê-los em uma busca por data.
- A deduplicação usa infohash v1 hexadecimal ou Base32 quando disponível. O formato pode ser inferido do título. Outros metadados variam por fonte.

## Fontes e limites
- Internet Archive: busca via Advanced Search, até 50 itens. URLs `.torrent` são derivadas do identificador e podem não existir; direitos variam por item. Idioma e categoria usam os metadados originais.
- Debian oficial: lista torrents da versão atual para amd64/bt-cd e filtra pelo nome. A listagem pode mudar ou ficar indisponível.
- Tempo limite de 15 segundos por solicitação. Falhas ou bloqueios não impedem outras fontes. Não há contorno de CAPTCHA ou autenticação, nem tentativas automáticas para evitar excesso de requisições.
- The Pirate Bay usa a API pública apibay. Nyaa usa a primeira página do RSS. Categorias e outros metadados variam por fonte.
- YTS busca por título ou código IMDb e lista as qualidades fornecidas na resposta.
- EZTV filtra os 100 torrents recentes ao buscar por texto. Digite o código IMDb da série, como `tt1234567`, para consultar até 100 resultados desse título na API.
- SubsPlease busca pelo catálogo público e lista as resoluções disponíveis. FitGirl consulta o primeiro feed RSS da busca. Resultados sem dados de seeders exibem um traço.
- EXT.to consulta a primeira página da busca pública. Quando a lista disponibiliza apenas a página da publicação, selecione o resultado e clique em **Abrir página**.
- 1337x consulta a primeira página da busca pública. Use **Abrir publicação** para abrir a página de detalhes.
- BitTorrented aparece em **Fontes** com o status de acesso por convite.

## EXT.to e 1337x na busca normal

O navegador integrado usa [WebView2](https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution). A edição standalone leva o runtime de versão fixa e o executável do navegador dentro do próprio pacote.

Com as fontes habilitadas em **Fontes**, digite o termo e clique em **Buscar**. O navegador integrado consulta EXT.to e 1337x em segundo plano, um por vez, enquanto as demais fontes pesquisam em paralelo. Quando a tabela carregar, até 50 itens por fonte entram na lista automaticamente.

Se o site pedir verificação, o app mostra a janela da fonte para você interagir. Você pode fechá-la para continuar com os outros resultados. A janela das fontes usa o perfil em `%APPDATA%\torrentFindr\webview2`. A importação depende de o site liberar e exibir os resultados.

Quando o aplicativo mostrar um aviso para EXT.to ou 1337x, **Abrir fonte** abre a janela integrada diretamente. Se um resultado só tiver o endereço da publicação, **Abrir publicação** pode trazer links diretos que estejam visíveis na página de detalhes.

Para recompilar o navegador a partir da pasta do projeto, com o SDK .NET 10, execute:

```powershell
dotnet publish embedded-browser/TorrentFindr.Browser.csproj -c Release -r win-x64 --self-contained -o browser -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:EnableCompressionInSingleFile=true
```

## Configurar RuTracker e CGPeers
1. Em uma instância local do [Jackett](https://github.com/Jackett/Jackett), adicione **RuTracker.org** ou **CGPeers**. Configure sua conta autorizada no RuTracker ou sua sessão autorizada no CGPeers. Use o botão de teste do próprio Jackett para confirmar o acesso.
2. No seeq, abra **Fontes**, informe a porta local do Jackett (padrão `9117`) e cole a chave da API exibida no painel dele.
3. Marque **Consultar RuTracker**, **Consultar CGPeers** ou ambos e clique em **Salvar**. A próxima busca consulta os indexadores selecionados.

A chave fica em memória durante a sessão. Informe-a novamente ao reabrir o seeq. As credenciais dos trackers ficam no Jackett. Para manter os endereços de download fora do arquivo de favoritos, o app salva apenas os metadados e a página do resultado desses trackers. Para baixar um favorito novamente, faça uma nova busca.

## Adicionar um provedor
Coloque um arquivo `.py` de fonte confiável em `%APPDATA%\torrentFindr\providers`, ative-o em Fontes e reinicie. Plugins executam código com os mesmos privilégios do usuário: revise-os antes de ativar. Exemplo:

```python
from core import Result
class Provider:
    name = 'Minha fonte'
    def search(self, query):
        return [Result(title='Exemplo', source=self.name,
                       magnet='magnet:?xt=urn:btih:' + 'a'*40,
                       infohash='a'*40, category='software',
                       language='pt', quality='', size=1024, seeders=3)]
```

Use somente serviços e credenciais para os quais você tenha autorização. Não exponha chaves no código compartilhado.

## Recompilar a versão standalone

O código da janela principal está em `desktop` e a interface em `interface`. Para o build, use o SDK .NET 10 e Python 3.10 ou superior. Baixe o ZIP embutível x64 do [Python](https://www.python.org/downloads/windows/) e o CAB **Fixed Version** x64 do [WebView2](https://developer.microsoft.com/microsoft-edge/webview2/). Confira as assinaturas dos componentes e extraia o CAB com `expand.exe -F:*`.

Da pasta do projeto, ajuste os dois caminhos de entrada no primeiro comando:

```powershell
python desktop/pack_payload.py C:/pacotes/python-x64.zip C:/pacotes/WebView2-extraido build/payload.zip
$payload = (Resolve-Path build/payload.zip).Path
dotnet publish desktop/TorrentFindr.Desktop.csproj -c Release -r win-x64 --self-contained -o build/standalone -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:DebugType=None "-p:PortablePayload=$payload"
```

O executável em `build/standalone/seeq.exe` pode ser distribuído sozinho. Gere um novo build para atualizar os runtimes incluídos.

## Referências
O Torlink usa a licença MIT, copyright 2026 bairon.dev. O projeto do seeq foi implementado de forma independente. [Repositório do Torlink](https://github.com/baairon/torlink)

Em 10/11/2026, consultas reais retornaram resultados com links em YTS, EZTV, SubsPlease e FitGirl. EXT.to e 1337x responderam HTTP 403 ao aplicativo. O fluxo de RuTracker e CGPeers foi verificado na janela com respostas simuladas de um servidor local. A consulta real desses trackers depende da sua configuração no Jackett.
