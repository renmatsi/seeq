(function collectResults() {
  const site = location.hostname.replace(/^www\./, "");
  const ext = site === "ext.to";
  if (location.protocol !== "https:" || (!ext && site !== "1337x.to"))
    return { error: "Abra uma página do EXT.to ou do 1337x." };
  if (document.querySelector("#challenge-form, #challenge-stage, #cf-challenge-running") ||
      /just a moment|um momento|access denied/i.test(document.title)) {
    return { challenge: true, error: "A verificação do site ainda está aberta. Aguarde os resultados e tente de novo." };
  }

  const detailPath = ext ? /^\/[^/]+-\d+\/?$/ : /^\/torrent\/\d+\/[^/]+\/?$/;
  const sameSite = link => {
    try {
      const url = new URL(link.href);
      return url.origin === location.origin ? url : null;
    } catch {
      return null;
    }
  };
  const downloads = links => {
    const magnet = links.find(link => link.href.startsWith("magnet:?"))?.href || "";
    const torrent = links.find(link => sameSite(link)?.pathname.endsWith(".torrent"));
    return {
      magnet: magnet.slice(0, 4096),
      torrent: torrent ? new URL(torrent.href).pathname : ""
    };
  };
  if (detailPath.test(location.pathname)) {
    const title = document.querySelector("h1")?.innerText.trim().slice(0, 500);
    const links = [...document.querySelectorAll("a[href]")].filter(link => link.getClientRects().length);
    const files = downloads(links);
    if (!title || (!files.magnet && !files.torrent))
      return { error: "A página não mostra um link magnet ou .torrent que o app possa importar." };
    return { format: "torrentfindr-page-v1", site, items: [{ title, page: location.pathname, ...files }] };
  }
  const isSearch = ext
    ? location.pathname === "/browse/" && new URLSearchParams(location.search).has("q")
    : location.pathname.startsWith("/search/");
  if (!isSearch) return { error: "Abra uma página de resultados." };
  const items = [];
  const pages = new Set();
  for (const row of document.querySelectorAll("table tr")) {
    if (!row.getClientRects().length) continue;
    const links = [...row.querySelectorAll("td a[href]")];
    const detail = links.find(link => {
      const url = sameSite(link);
      return url && link.innerText.trim() && detailPath.test(url.pathname);
    });
    if (!detail) continue;
    const page = new URL(detail.href).pathname;
    if (pages.has(page)) continue;
    pages.add(page);

    const cells = [...row.querySelectorAll("td")];
    const seeds = ext
      ? cells.map(cell => cell.innerText.trim()).find(value => /^seeds?\s+[\d, ]+$/i.test(value))
      : row.querySelector("td.seeds")?.innerText;
    const size = ext
      ? cells.map(cell => cell.innerText.trim()).find(value => /^size\s+\d/i.test(value))
      : row.querySelector("td.size")?.innerText;
    const time = row.querySelector("time[datetime], td [data-timestamp]");
    items.push({
      title: detail.innerText.trim().slice(0, 500),
      page,
      seeders: (seeds || "").slice(0, 40),
      size: (size || "").slice(0, 40),
      published: (time?.getAttribute("datetime") || time?.getAttribute("data-timestamp") || "").slice(0, 64),
      ...downloads(links)
    });
    if (items.length === 50) break;
  }
  if (!items.length &&
      !/\b(?:no (?:torrents|results|matches)(?: found)?|0 torrents)\b/i.test(document.body.innerText))
    return { error: "Não encontrei linhas de resultados visíveis nesta aba." };
  return { format: "torrentfindr-page-v1", site, items };
})()
