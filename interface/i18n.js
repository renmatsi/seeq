"use strict";

const locales = {
  "pt-BR":"Português (Brasil)", en:"English", es:"Español", ru:"Русский", ja:"日本語", "zh-Hans":"简体中文"
};
let locale = "pt-BR";
let translationIndex = -1;

// English, Spanish, Russian, Japanese and Simplified Chinese, in that order.
const translations = {
  "Navegação principal":["Main navigation","Navegación principal","Основная навигация","メインナビゲーション","主导航"],
  "Busca":["Search","Búsqueda","Поиск","検索","搜索"],
  "Favoritos":["Favorites","Favoritos","Избранное","お気に入り","收藏"],
  "Histórico":["History","Historial","История","履歴","历史记录"],
  "Fontes":["Sources","Fuentes","Источники","ソース","来源"],
  "Log de atividade":["Activity log","Registro de actividad","Журнал действий","アクティビティログ","活动日志"],
  "Configurações":["Settings","Configuración","Настройки","設定","设置"],
  "Minimizar":["Minimize","Minimizar","Свернуть","最小化","最小化"],
  "Fechar":["Close","Cerrar","Закрыть","閉じる","关闭"],
  "Fechar painel":["Close panel","Cerrar panel","Закрыть панель","パネルを閉じる","关闭面板"],
  "Buscar":["Search","Buscar","Искать","検索","搜索"],
  "Buscar torrents":["Search torrents","Buscar torrents","Поиск торрентов","トレントを検索","搜索种子"],
  "Título, palavra-chave ou infohash":["Title, keyword or infohash","Título, palabra clave o infohash","Название, ключевое слово или инфохеш","タイトル、キーワード、または infohash","标题、关键词或信息哈希"],
  "Cancelar busca":["Cancel search","Cancelar búsqueda","Отменить поиск","検索をキャンセル","取消搜索"],
  "Busca avançada":["Advanced search","Búsqueda avanzada","Расширенный поиск","詳細検索","高级搜索"],
  "Abrir busca avançada":["Open advanced search","Abrir búsqueda avanzada","Открыть расширенный поиск","詳細検索を開く","打开高级搜索"],
  "Recolher busca avançada":["Collapse advanced search","Cerrar búsqueda avanzada","Свернуть расширенный поиск","詳細検索を閉じる","收起高级搜索"],
  "Ordenar resultados":["Sort results","Ordenar resultados","Сортировать результаты","結果を並べ替える","排序结果"],
  "Ordenação":["Sort order","Orden","Сортировка","並べ替え順","排序方式"],
  "Relevância":["Relevance","Relevancia","Релевантность","関連度","相关度"],
  "Mais recentes":["Newest","Más recientes","Сначала новые","新しい順","最新优先"],
  "Mais antigos":["Oldest","Más antiguos","Сначала старые","古い順","最早优先"],
  "Mais seeders":["Most seeders","Más seeders","Больше сидов","シーダー数が多い順","做种者最多"],
  "Menor tamanho":["Smallest size","Menor tamaño","Наименьший размер","サイズが小さい順","体积最小"],
  "Qualquer data":["Any date","Cualquier fecha","Любая дата","すべての期間","不限日期"],
  "Hoje":["Today","Hoy","Сегодня","今日","今天"],
  "Últimos 7 dias":["Last 7 days","Últimos 7 días","За 7 дней","過去7日間","最近 7 天"],
  "Últimos 30 dias":["Last 30 days","Últimos 30 días","За 30 дней","過去30日間","最近 30 天"],
  "Últimos 90 dias":["Last 90 days","Últimos 90 días","За 90 дней","過去90日間","最近 90 天"],
  "Últimos {days} dias":["Last {days} days","Últimos {days} días","За {days} дн.","過去{days}日間","最近 {days} 天"],
  "Intervalo personalizado":["Custom range","Intervalo personalizado","Свой период","期間を指定","自定义范围"],
  "Interpretar filtros na busca":["Detect filters in the query","Detectar filtros en la búsqueda","Распознавать фильтры в запросе","検索語から絞り込み条件を検出","识别搜索词中的筛选条件"],
  "Usar busca de exemplo":["Use an example search","Usar búsqueda de ejemplo","Использовать пример запроса","検索例を使う","使用搜索示例"],
  "{count} filtro(s) interpretado(s)":["Filters detected: {count}","Filtros detectados: {count}","Распознано фильтров: {count}","検出した条件：{count} 件","已识别 {count} 个筛选条件"],
  "Publicação do torrent":["Torrent publication date","Publicación del torrent","Дата публикации торрента","トレントの公開日","种子发布日期"],
  "De":["From","Desde","С","開始日","开始日期"],
  "Até":["To","Hasta","По","終了日","结束日期"],
  "Desde {date}":["From {date}","Desde {date}","С {date}","{date} から","从 {date} 起"],
  "Até {date}":["Until {date}","Hasta {date}","До {date}","{date} まで","截至 {date}"],
  "Ano do conteúdo":["Content year","Año del contenido","Год выпуска","コンテンツの年","内容年份"],
  "Ano {year}":["Year {year}","Año {year}","Год: {year}","{year} 年","年份 {year}"],
  "Qualquer":["Any","Cualquiera","Любой","指定なし","不限"],
  "Fonte":["Source","Fuente","Источник","ソース","来源"],
  "Categoria":["Category","Categoría","Категория","カテゴリ","类别"],
  "Idioma":["Language","Idioma","Язык","言語","语言"],
  "Português":["Portuguese","Portugués","Португальский","ポルトガル語","葡萄牙语"],
  "Inglês":["English","Inglés","Английский","英語","英语"],
  "Espanhol":["Spanish","Español","Испанский","スペイン語","西班牙语"],
  "Russo":["Russian","Ruso","Русский","ロシア語","俄语"],
  "Japonês":["Japanese","Japonés","Японский","日本語","日语"],
  "Chinês":["Chinese","Chino","Китайский","中国語","中文"],
  "Qualidade":["Quality","Calidad","Качество","画質","质量"],
  "Formato":["Format","Formato","Формат","形式","格式"],
  "Tipo de link":["Link type","Tipo de enlace","Тип ссылки","リンクの種類","链接类型"],
  "Seeders mín.":["Min. seeders","Mín. seeders","Мин. сидов","シーダー数の下限","最少做种者"],
  "Tamanho mín. (GB)":["Min. size (GB)","Tamaño mín. (GB)","Мин. размер (ГБ)","最小サイズ（GB）","最小体积（GB）"],
  "Tamanho máx. (GB)":["Max. size (GB)","Tamaño máx. (GB)","Макс. размер (ГБ)","最大サイズ（GB）","最大体积（GB）"],
  "Sem mínimo":["No minimum","Sin mínimo","Без минимума","下限なし","无下限"],
  "Sem máximo":["No maximum","Sin máximo","Без максимума","上限なし","无上限"],
  "Incluir itens sem data no período":["Include items with no date","Incluir elementos sin fecha","Включать записи без даты","日付不明の項目も含める","包含日期未知的项目"],
  "Inclui sem data":["Includes undated items","Incluye sin fecha","Включая записи без даты","日付不明も含む","包含日期未知项"],
  "Limpar filtros":["Clear filters","Borrar filtros","Сбросить фильтры","条件をクリア","清除筛选条件"],
  "Aplicar filtros":["Apply filters","Aplicar filtros","Применить фильтры","条件を適用","应用筛选条件"],
  "Filtros aplicados":["Applied filters","Filtros aplicados","Применённые фильтры","適用中の条件","已应用的筛选条件"],
  "Remover {item}":["Remove {item}","Quitar {item}","Удалить: {item}","{item} を削除","移除 {item}"],
  "Recolher detalhes":["Collapse details","Ocultar detalles","Скрыть подробности","詳細を閉じる","收起详情"],
  "Mostrar detalhes":["Show details","Mostrar detalles","Показать подробности","詳細を表示","显示详情"],
  "Resultados":["Results","Resultados","Результаты","検索結果","结果"],
  "Detalhes do resultado":["Result details","Detalles del resultado","Подробности результата","検索結果の詳細","结果详情"],
  "{count} resultado":["{count} result","{count} resultado","Результаты: {count}","{count} 件の結果","{count} 条结果"],
  "{count} resultados":["{count} results","{count} resultados","Результаты: {count}","{count} 件の結果","{count} 条结果"],
  "Os resultados salvos aparecem aqui.":["Saved results appear here.","Los resultados guardados aparecen aquí.","Здесь будут сохранённые результаты.","保存した結果がここに表示されます。","已保存的结果会显示在这里。"],
  "Aguardando as primeiras fontes…":["Waiting for the first sources…","Esperando las primeras fuentes…","Ожидание ответов источников…","ソースからの応答を待っています…","正在等待来源响应…"],
  "Nenhum resultado com os critérios atuais.":["No results match the current filters.","No hay resultados con los filtros actuales.","Нет результатов с текущими фильтрами.","現在の条件に一致する結果がありません。","没有符合当前条件的结果。"],
  "Data não informada":["Date unavailable","Fecha no indicada","Дата не указана","日付不明","日期未知"],
  "Sem dados":["No data","Sin datos","Нет данных","データなし","无数据"],
  "{count} seeds":["{count} seeds","{count} seeds","Сиды: {count}","シーダー {count}","{count} 个做种者"],
  "Seeders não informados":["Seeder count unavailable","Cantidad de seeders no indicada","Число сидов не указано","シーダー数不明","做种者数量未知"],
  "{count} seeders informados":["{count} reported seeders","{count} seeders informados","Указано сидов: {count}","報告されたシーダー数：{count}","报告了 {count} 个做种者"],
  "Encontrado em":["Found on","Encontrado en","Найдено в","掲載元","来源"],
  "Publicação":["Published","Publicación","Публикация","公開日","发布日期"],
  "Abrir magnet no cliente BitTorrent":["Open magnet in BitTorrent client","Abrir magnet en el cliente BitTorrent","Открыть magnet в клиенте BitTorrent","BitTorrent クライアントでマグネットリンクを開く","在 BitTorrent 客户端中打开磁力链接"],
  "Nenhum link disponível":["No link available","Ningún enlace disponible","Нет доступных ссылок","利用できるリンクはありません","暂无可用链接"],
  "Abrir .torrent":["Open .torrent","Abrir .torrent","Открыть .torrent",".torrent を開く","打开 .torrent"],
  "Abrir magnet":["Open magnet","Abrir magnet","Открыть magnet","マグネットリンクを開く","打开磁力链接"],
  "Abrir publicação":["Open listing","Abrir publicación","Открыть публикацию","掲載ページを開く","打开详情页"],
  "Favorito":["Favorite","Favorito","Избранное","お気に入り","收藏"],
  "Remover dos favoritos":["Remove from favorites","Quitar de favoritos","Удалить из избранного","お気に入りから削除","取消收藏"],
  "Adicionar aos favoritos":["Add to favorites","Añadir a favoritos","Добавить в избранное","お気に入りに追加","添加到收藏"],
  "Abrir fonte":["Open source","Abrir fuente","Открыть источник","ソースを開く","打开来源"],
  "Nenhuma atividade nesta sessão.":["No activity in this session.","No hay actividad en esta sesión.","В этом сеансе нет действий.","このセッションには記録がありません。","本次会话暂无活动。"],
  "Nenhuma busca salva.":["No saved searches.","No hay búsquedas guardadas.","Нет сохранённых запросов.","保存した検索はありません。","没有已保存的搜索。"],
  "Limpar histórico":["Clear history","Borrar historial","Очистить историю","履歴を消去","清除历史记录"],
  "Limpar todo o histórico?":["Clear all search history?","¿Borrar todo el historial?","Очистить всю историю поиска?","検索履歴をすべて消去しますか？","清除所有搜索历史记录？"],
  "Cancelar":["Cancel","Cancelar","Отмена","キャンセル","取消"],
  "Limpar tudo":["Clear all","Borrar todo","Очистить всё","すべて消去","全部清除"],
  "Remover do histórico":["Remove from history","Quitar del historial","Удалить из истории","履歴から削除","从历史记录中移除"],
  "Remover {item} do histórico":["Remove {item} from history","Quitar {item} del historial","Удалить из истории: {item}","履歴から {item} を削除","从历史记录中移除 {item}"],
  "Idioma da interface":["Interface language","Idioma de la interfaz","Язык интерфейса","表示言語","界面语言"],
  "Esquema de cores":["Color scheme","Esquema de colores","Цветовая схема","配色","配色方案"],
  "Sistema":["System","Sistema","Системная","システム","跟随系统"],
  "Papel":["Paper","Papel","Светлая","ペーパー","纸白"],
  "Grafite":["Graphite","Grafito","Графит","グラファイト","石墨灰"],
  "Meia-noite":["Midnight","Medianoche","Полночь","ミッドナイト","午夜"],
  "Cor de destaque":["Accent color","Color de acento","Цвет акцента","アクセントカラー","强调色"],
  "Azul":["Blue","Azul","Синий","青","蓝色"],
  "Violeta":["Violet","Violeta","Фиолетовый","紫","紫色"],
  "Verde":["Green","Verde","Зелёный","緑","绿色"],
  "Âmbar":["Amber","Ámbar","Янтарный","琥珀色","琥珀色"],
  "Rosa":["Pink","Rosa","Розовый","ピンク","粉色"],
  "Ciano":["Cyan","Cian","Бирюзовый","シアン","青色"],
  "Cor personalizada":["Custom color","Color personalizado","Свой цвет","カスタムカラー","自定义颜色"],
  "Fundo ilustrado":["Illustrated background","Fondo ilustrado","Фоновая иллюстрация","イラスト背景","插画背景"],
  "Modo de mistura":["Blend mode","Modo de fusión","Режим наложения","描画モード","混合模式"],
  "Automático":["Automatic","Automático","Автоматический","自動","自动"],
  "Luz suave":["Soft light","Luz suave","Мягкий свет","ソフトライト","柔光"],
  "Tela":["Screen","Trama","Экран","スクリーン","滤色"],
  "Multiplicar":["Multiply","Multiplicar","Умножение","乗算","正片叠底"],
  "Intensidade":["Intensity","Intensidad","Интенсивность","強度","强度"],
  "acesso por convite":["invite-only access","acceso por invitación","доступ по приглашению","招待制","仅限邀请"],
  "Porta Jackett":["Jackett port","Puerto de Jackett","Порт Jackett","Jackett のポート","Jackett 端口"],
  "Chave do Jackett":["Jackett key","Clave de Jackett","Ключ Jackett","Jackett のキー","Jackett 密钥"],
  "Chave ativa nesta sessão":["Key active for this session","Clave activa en esta sesión","Ключ активен в этом сеансе","このセッションでキーが有効","密钥在本次会话中有效"],
  "Somente nesta sessão":["This session only","Solo en esta sesión","Только в этом сеансе","このセッションのみ","仅限本次会话"],
  "Use o Jackett local para RuTracker e CGPeers. Ative somente fontes e plugins autorizados.":["Use local Jackett for RuTracker and CGPeers. Enable only authorized sources and plugins.","Usa Jackett local para RuTracker y CGPeers. Activa solo fuentes y complementos autorizados.","Используйте локальный Jackett для RuTracker и CGPeers. Включайте только разрешённые источники и плагины.","RuTracker と CGPeers にはローカルの Jackett を使います。許可されたソースとプラグインのみ有効にしてください。","RuTracker 和 CGPeers 需要本地 Jackett。请仅启用已获授权的来源和插件。"],
  "Salvar fontes":["Save sources","Guardar fuentes","Сохранить источники","ソースを保存","保存来源"],
  "Buscando “{term}”…":["Searching for “{term}”…","Buscando «{term}»…","Поиск «{term}»…","「{term}」を検索中…","正在搜索“{term}”…"],
  "Busca concluída · {count} resultado(s).":["Search complete · {count} result(s).","Búsqueda completada · {count} resultado(s).","Поиск завершён · результатов: {count}.","検索完了 · {count} 件。","搜索完成 · {count} 条结果。"],
  "Busca cancelada · {count} resultado(s) preservados.":["Search canceled · {count} result(s) kept.","Búsqueda cancelada · {count} resultado(s) conservados.","Поиск отменён · сохранено результатов: {count}.","検索をキャンセル · {count} 件を保持。","搜索已取消 · 保留了 {count} 条结果。"],
  "Abrindo a publicação…":["Opening the listing…","Abriendo la publicación…","Открытие публикации…","掲載ページを開いています…","正在打开详情页…"],
  "Resultado removido dos favoritos.":["Removed from favorites.","Quitado de favoritos.","Удалено из избранного.","お気に入りから削除しました。","已取消收藏。"],
  "Resultado salvo nos favoritos.":["Saved to favorites.","Guardado en favoritos.","Добавлено в избранное.","お気に入りに追加しました。","已添加到收藏。"],
  "Fontes salvas. Reinicie para carregar plugins recém-ativados.":["Sources saved. Restart to load newly enabled plugins.","Fuentes guardadas. Reinicia para cargar los complementos recién activados.","Источники сохранены. Перезапустите приложение, чтобы загрузить новые плагины.","ソースを保存しました。新しく有効にしたプラグインを読み込むには再起動してください。","来源已保存。重启后加载新启用的插件。"],
  "Resultado importado.":["Result imported.","Resultado importado.","Результат импортирован.","結果を取り込みました。","结果已导入。"],
  "Janela fechada.":["Window closed.","Ventana cerrada.","Окно закрыто.","ウィンドウを閉じました。","窗口已关闭。"],
  "Digite um termo de busca.":["Enter a search term.","Escribe un término de búsqueda.","Введите поисковый запрос.","検索語を入力してください。","请输入搜索词。"],
  "Inclua uma palavra-chave além dos filtros.":["Include a keyword alongside the filters.","Incluye una palabra clave además de los filtros.","Добавьте ключевое слово к фильтрам.","絞り込み条件に加えてキーワードを入力してください。","请在筛选条件之外输入关键词。"],
  "Ative uma fonte em Fontes para pesquisar.":["Enable a source to start searching.","Activa una fuente para buscar.","Включите источник, чтобы начать поиск.","検索するにはソースを有効にしてください。","请启用至少一个来源后再搜索。"],
  "Plugin não carregado.":["Plugin could not load.","No se pudo cargar el complemento.","Не удалось загрузить плагин.","プラグインを読み込めませんでした。","无法加载插件。"],
  "Informe a chave do Jackett em Fontes.":["Enter the Jackett key in Sources.","Introduce la clave de Jackett en Fuentes.","Введите ключ Jackett в разделе «Источники».","ソースで Jackett のキーを入力してください。","请在来源中输入 Jackett 密钥。"],
  "Navegador integrado indisponível.":["Built-in browser unavailable.","Navegador integrado no disponible.","Встроенный браузер недоступен.","内蔵ブラウザーを利用できません。","内置浏览器不可用。"],
  "O DNS não conseguiu resolver o endereço da fonte.":["DNS could not resolve the source address.","El DNS no pudo resolver la dirección de la fuente.","DNS не смог разрешить адрес источника.","DNS でソースのアドレスを解決できませんでした。","DNS 无法解析来源地址。"],
  "A página não respondeu dentro do prazo.":["The page timed out.","La página tardó demasiado en responder.","Страница не ответила вовремя.","ページの応答がタイムアウトしました。","页面响应超时。"],
  "A página não exibiu resultados no prazo.":["The page did not return results in time.","La página no mostró resultados a tiempo.","Страница не показала результаты вовремя.","ページに結果が表示されるまでに時間がかかりすぎました。","页面未在规定时间内返回结果。"],
  "A fonte limitou as consultas.":["The source limited requests.","La fuente limitó las consultas.","Источник ограничил запросы.","ソースがリクエストを制限しました。","来源限制了查询频率。"],
  "A verificação da fonte ficou pendente.":["Source verification is pending.","La verificación de la fuente está pendiente.","Проверка источника ещё не завершена.","ソースの確認が完了していません。","来源验证尚未完成。"],
  "O navegador integrado não iniciou.":["The built-in browser could not start.","El navegador integrado no se inició.","Встроенный браузер не запустился.","内蔵ブラウザーを起動できませんでした。","无法启动内置浏览器。"],
  "Aguarde a busca ou a janela integrada atual.":["Wait for the current search or built-in window.","Espera la búsqueda o la ventana integrada actual.","Дождитесь окончания поиска или закройте встроенное окно.","現在の検索または内蔵ウィンドウの処理を待ってください。","请等待当前搜索或内置窗口完成。"],
  "Este resultado não tem um magnet válido.":["This result has no valid magnet link.","Este resultado no tiene un enlace magnet válido.","В этом результате нет действительной magnet-ссылки.","この結果には有効なマグネットリンクがありません。","此结果没有有效的磁力链接。"],
  "Associe um cliente BitTorrent a links magnet no Windows.":["Associate magnet links with a BitTorrent client in Windows.","Asocia los enlaces magnet con un cliente BitTorrent en Windows.","Свяжите magnet-ссылки с клиентом BitTorrent в Windows.","Windows でマグネットリンクを BitTorrent クライアントに関連付けてください。","请在 Windows 中将磁力链接关联到 BitTorrent 客户端。"],
  "A fonte não informou este link.":["The source did not provide this link.","La fuente no proporcionó este enlace.","Источник не предоставил эту ссылку.","ソースからこのリンクが提供されていません。","来源未提供此链接。"],
  "Informe uma porta do Jackett entre 1 e 65535.":["Enter a Jackett port between 1 and 65535.","Introduce un puerto de Jackett entre 1 y 65535.","Укажите порт Jackett от 1 до 65535.","Jackett のポートは 1～65535 で入力してください。","请输入 1 到 65535 之间的 Jackett 端口。"],
  "Confira os campos numéricos de ano, tamanho e seeders.":["Check the numeric fields for year, size and seeders.","Revisa los campos numéricos de año, tamaño y seeders.","Проверьте числовые поля года, размера и числа сидов.","年、サイズ、シーダー数の数値を確認してください。","请检查年份、体积和做种者数量。"],
  "Use números positivos ou zero.":["Use non-negative numbers.","Usa números positivos o cero.","Используйте неотрицательные числа.","0 以上の数値を入力してください。","请输入非负数。"],
  "Informe um ano de conteúdo válido.":["Enter a valid content year.","Introduce un año de contenido válido.","Введите действительный год выпуска.","有効な年を入力してください。","请输入有效的内容年份。"],
  "Informe um intervalo de publicação válido.":["Enter a valid publication range.","Introduce un intervalo de publicación válido.","Укажите допустимый период публикации.","有効な公開期間を入力してください。","请输入有效的发布日期范围。"],
  "O tamanho mínimo precisa ser menor ou igual ao máximo.":["The minimum size must be less than or equal to the maximum.","El tamaño mínimo debe ser menor o igual al máximo.","Минимальный размер не может превышать максимальный.","最小サイズは最大サイズ以下にしてください。","最小体积不得超过最大体积。"],
  "O mecanismo de busca foi encerrado. Reabra o aplicativo.":["The search engine stopped. Reopen the app.","El motor de búsqueda se detuvo. Vuelve a abrir la aplicación.","Поисковый модуль остановлен. Откройте приложение заново.","検索エンジンが停止しました。アプリを開き直してください。","搜索引擎已停止。请重新打开应用。"],
  "Sobre":["About","Acerca de","О приложении","このアプリについて","关于"],
  "Versão {version}":["Version {version}","Versión {version}","Версия {version}","バージョン {version}","版本 {version}"],
  "Desenvolvido por":["Developed by","Desarrollado por","Разработчик","開発者","开发者"],
  "Abrir site do desenvolvedor":["Open developer website","Abrir sitio del desarrollador","Открыть сайт разработчика","開発者のサイトを開く","打开开发者网站"]
};

function tr(key, values = {}) {
  key = String(key ?? "");
  const template = Object.hasOwn(translations,key) ? translations[key][translationIndex] || key : key;
  return template.replace(/\{(\w+)\}/g, (part,name)=>Object.hasOwn(values,name) ? values[name] : part);
}

// Capture the original static text before the search interface adds any user data.
const staticLabels = [];
const staticText = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
for (let node = staticText.nextNode(); node; node = staticText.nextNode()) {
  const key = node.textContent.trim();
  if (Object.hasOwn(translations,key)) staticLabels.push({node,key});
}
for (const node of document.querySelectorAll("[aria-label],[title],[placeholder]")) {
  for (const attribute of ["aria-label","title","placeholder"]) {
    const key = node.getAttribute(attribute);
    if (Object.hasOwn(translations,key)) staticLabels.push({node,attribute,key});
  }
}

function setLocale(value) {
  locale = Object.hasOwn(locales,value) ? value : "pt-BR";
  translationIndex = Object.keys(locales).indexOf(locale) - 1;
  document.documentElement.lang = locale;
  for (const {node,attribute,key} of staticLabels) {
    if (attribute) node.setAttribute(attribute,tr(key));
    else node.textContent = tr(key);
  }
}

function translateStatus(message) {
  const search = /^Buscando “(.*)”…$/.exec(message);
  if (search) return tr("Buscando “{term}”…",{term:search[1]});
  const complete = /^Busca concluída · (\d+) resultado\(s\)\.$/.exec(message);
  if (complete) return tr("Busca concluída · {count} resultado(s).",{count:complete[1]});
  const cancelled = /^Busca cancelada · (\d+) resultado\(s\) preservados\.$/.exec(message);
  if (cancelled) return tr("Busca cancelada · {count} resultado(s) preservados.",{count:cancelled[1]});
  return tr(message);
}
