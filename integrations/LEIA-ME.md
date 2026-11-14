# seeq para Hermes e Strata

As duas configurações apontam para o mesmo servidor local do seeq. Ele usa o Python já instalado neste Windows e pode ser chamado com a janela do seeq fechada.

- `list_sources` mostra as fontes públicas disponíveis e quais estão habilitadas no perfil do seeq.
- `search` recebe o termo em `query`. Use `sources` para escolher fontes e `limit` para limitar a lista. Os resultados trazem links e metadados, além de falhas por fonte. A busca consulta os endereços públicos das fontes selecionadas.

O servidor funciona por entrada e saída padrão e consulta o perfil em modo de leitura. A integração cobre fontes públicas de consulta direta. RuTracker, CGPeers e importações que dependem de interação na janela integrada continuam disponíveis na interface do seeq conforme a configuração das fontes.

## Hermes

Adicione a entrada `seeq` de `hermes.yaml` à seção `mcp_servers` do arquivo de configuração do perfil Hermes. Se a seção já existir, insira apenas a entrada dentro dela. Em seguida, use `/reload-mcp` na sessão. [Documentação do Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)

## Strata Desktop

Abra **Configurações → Ferramentas → Adicionar ferramenta** e escolha **Conectar um servidor de ferramentas (MCP)**. Use `seeq` como nome e `Busca metadados e links de torrents em fontes públicas` como descrição. Copie o caminho em `command` de `strata.json` para o campo do programa. No campo de argumentos, coloque `-B` na primeira linha e o caminho do script na segunda, sem aspas. A alteração vale a partir da próxima mensagem. [Configuração de ferramentas do Strata](https://github.com/Niko1221/Strata/blob/main/apps/host/src/components/SettingsTools.tsx)

Para o modo servidor do Strata, mescle a entrada de `strata.json` em `mcp_servers` na configuração de execução. [Cliente MCP do Strata](https://github.com/Niko1221/Strata/blob/main/serve/mcp.py)

## Consulta de teste

Peça ao assistente para buscar `debian` no seeq usando apenas `Debian oficial` e mostrar até três resultados.
