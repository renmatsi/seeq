"""Provedores públicos e conexão Torznab local."""

import json
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

from core import Result, get, integer, magnet_for, magnet_hash, normalize_hash, publication_date, quality_from


def text(value):
    return value.strip() if isinstance(value, str) else ''


def https(value):
    return value if isinstance(value, str) and value.startswith('https://') else ''


def query_url(base, **params):
    return base + '?' + urlencode(params)


def json_object(url):
    data = json.loads(get(url))
    if not isinstance(data, dict):
        raise ValueError('Resposta inesperada da fonte')
    return data


class YTS:
    name = 'YTS'
    endpoint = 'https://yts.am/api/v2/list_movies.json'

    def search(self, query):
        data = json_object(query_url(self.endpoint, query_term=query, limit=50))
        if data.get('status') != 'ok' or not isinstance(data.get('data'), dict):
            raise ValueError('A API do YTS não retornou um catálogo')
        rows = []
        for movie in data['data'].get('movies') or []:
            title = text(movie.get('title_long') or movie.get('title'))
            for item in movie.get('torrents') or []:
                digest = normalize_hash(item.get('hash'))
                if not title or not digest:
                    continue
                quality = text(item.get('quality'))
                variant = ' '.join(filter(None, (quality, text(item.get('type')))))
                name = f'{title} [{variant}]' if variant else title
                rows.append(Result(
                    name, self.name, torrent=https(item.get('url')),
                    magnet=magnet_for(digest, name), infohash=digest,
                    category='Filmes', language=text(item.get('language')),
                    quality=quality, size=integer(item.get('size_bytes')),
                    seeders=integer(item.get('seeds')),
                    published=publication_date(item.get('date_uploaded_unix') or item.get('date_uploaded')),
                    release_year=integer(movie.get('year')),
                ))
        return rows


class EZTV:
    name = 'EZTV'
    endpoint = 'https://eztvx.to/api/get-torrents'

    def __init__(self):
        self.recent = []
        self.expires = 0

    def fetch(self, **params):
        data = json_object(query_url(self.endpoint, limit=100, page=1, **params))
        rows = data.get('torrents')
        if rows is None and integer(data.get('torrents_count')) == 0:
            return []
        if not isinstance(rows, list):
            raise ValueError('A API do EZTV não retornou uma lista de torrents')
        return rows

    def search(self, query):
        imdb = re.fullmatch(r'(?:tt)?([0-9]{7,10})', query, re.I)
        if imdb:
            items = self.fetch(imdb_id=imdb[1])
        else:
            if time.monotonic() >= self.expires:
                self.recent = self.fetch()
                self.expires = time.monotonic() + 300
            tokens = re.findall(r'\w+', query.casefold())
            if not tokens:
                return []
            items = [
                item for item in self.recent
                if all(word in (
                    text(item.get('title')) + ' ' + text(item.get('filename'))
                ).casefold() for word in tokens)
            ]
        rows = []
        for item in items:
            title = text(item.get('title') or item.get('filename'))
            magnet = text(item.get('magnet_url'))
            digest = magnet_hash(magnet) or normalize_hash(item.get('hash'))
            torrent = https(item.get('torrent_url'))
            if title and (digest or torrent):
                rows.append(Result(
                    title, self.name, torrent=torrent, infohash=digest,
                    magnet=magnet if magnet_hash(magnet) else magnet_for(digest, title),
                    category='Séries', quality=quality_from(title),
                    size=integer(item.get('size_bytes')), seeders=integer(item.get('seeds')),
                    published=publication_date(item.get('date_released_unix')),
                ))
        return rows


class SubsPlease:
    name = 'SubsPlease'

    def search(self, query):
        data = json.loads(get(query_url('https://subsplease.org/api/', f='search', s=query, tz='UTC')))
        if data == []:
            return []
        if not isinstance(data, dict):
            raise ValueError('Resposta inesperada do SubsPlease')
        rows = []
        for key, entry in data.items():
            if not isinstance(entry, dict):
                continue
            title = text(entry.get('show')) or key
            episode = str(entry.get('episode') or '').strip()
            for item in entry.get('downloads') or []:
                magnet = text(item.get('magnet'))
                digest = magnet_hash(magnet)
                if not digest:
                    continue
                resolution = str(item.get('res') or '').strip()
                quality = resolution + 'p' if resolution.isdecimal() else resolution
                name = ' - '.join(filter(None, (title, episode, quality)))
                size = parse_qs(magnet[8:]).get('xl', [None])[0]
                rows.append(Result(
                    name, self.name, magnet=magnet, infohash=digest,
                    category='Anime', quality=quality, size=integer(size),
                    published=publication_date(entry.get('release_date')),
                ))
                if len(rows) >= 150:
                    return rows
        return rows


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.links.append(href)


def download_links(links, base):
    magnet = ''
    torrent = ''
    for href in links:
        if not magnet and magnet_hash(href):
            magnet = href
        elif not torrent and re.search(r'\.torrent(?:[?#]|$)', href, re.I):
            torrent = https(urljoin(base, href))
    return magnet, torrent


def rss_channel(body):
    root = ET.fromstring(body)
    if root.tag == 'error':
        raise ValueError(f'Torznab retornou um erro (código {integer(root.get("code")) or "desconhecido"})')
    channel = root.find('channel')
    if root.tag != 'rss' or channel is None:
        raise ValueError('A fonte não retornou um feed RSS válido')
    return channel


class FitGirl:
    name = 'FitGirl'
    base = 'https://fitgirl-repacks.site/'

    def search(self, query):
        channel = rss_channel(get(query_url(self.base, s=query, feed='rss2')))
        rows = []
        for item in channel.findall('item')[:50]:
            title = unescape(item.findtext('title', '')).strip()
            page = https(item.findtext('link', ''))
            parser = Anchors()
            for part in item:
                if part.tag in ('description', '{http://purl.org/rss/1.0/modules/content/}encoded'):
                    parser.feed(part.text or '')
            magnet, torrent = download_links(parser.links, self.base)
            if title and (magnet or torrent or page):
                rows.append(Result(
                    title, self.name, torrent=torrent, magnet=magnet,
                    infohash=magnet_hash(magnet), category='Jogos', page=page,
                    published=publication_date(item.findtext('pubDate')),
                ))
        return rows


class SearchTable(HTMLParser):
    """Lê texto e links dentro de cada célula da tabela pública."""

    def __init__(self, body):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.anchor = None
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tr':
            self.row = []
        elif tag == 'td' and self.row is not None:
            self.cell = {'classes': (attrs.get('class') or '').split(), 'words': [], 'links': []}
            self.row.append(self.cell)
        elif tag == 'a' and self.cell is not None:
            self.anchor = [attrs.get('href') or '', []]
            self.cell['links'].append(self.anchor)

    def handle_endtag(self, tag):
        if tag == 'a':
            self.anchor = None
        elif tag == 'td':
            self.anchor = self.cell = None
        elif tag == 'tr' and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None and data.strip():
            self.cell['words'].append(data.strip())
        if self.anchor is not None and data.strip():
            self.anchor[1].append(data.strip())


def size_bytes(value):
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*([KMGT]i?B|B)\b', value, re.I)
    if match:
        exponent = 'BKMGT'.index(match[2][0].upper())
        return int(float(match[1].replace(',', '.')) * 1024**exponent)
    return None


class SearchRefused(ValueError):
    pass


class PublicTableSource:
    def search(self, query):
        try:
            body = get(self.search_url(query))
        except HTTPError as error:
            if error.code == 403:
                raise SearchRefused('A fonte recusou a consulta automática (HTTP 403).') from error
            raise
        return self.parse_search_page(body)

    def parse_search_page(self, body):
        if re.search(r'<title>\s*(?:Just a moment|Access denied|Attention Required)', body, re.I):
            raise SearchRefused('A página contém um desafio de acesso, em vez dos resultados.')
        table = SearchTable(body)
        rows = []
        for cells in table.rows:
            links = [link for cell in cells for link in cell['links']]
            title_links = [
                (href, ' '.join(words)) for href, words in links
                if words and self.detail_path.fullmatch(urlsplit(href).path)
                and urlsplit(urljoin(self.base, href)).netloc == urlsplit(self.base).netloc
            ]
            if not title_links:
                continue
            href, title = title_links[0]
            magnet, torrent = download_links((link[0] for link in links), self.base)
            seeders, size = self.stats(cells)
            rows.append(Result(
                title, self.name, torrent=torrent, magnet=magnet, infohash=magnet_hash(magnet),
                quality=quality_from(title), size=size, seeders=seeders,
                page=urljoin(self.base, href),
            ))
            if len(rows) >= 50:
                break
        if not rows and not re.search(r'\b(?:no (?:torrents|results|matches)|0 torrents)\b', body, re.I):
            raise ValueError('A página não apresentou uma tabela de resultados reconhecível')
        return rows


class ExtTo(PublicTableSource):
    name = 'EXT.to'
    base = 'https://ext.to/'
    detail_path = re.compile(r'/[^/]+-\d+/?')

    def search_url(self, query):
        return query_url(self.base + 'browse/', q=query)

    def stats(self, cells):
        seeders = size = None
        for cell in cells[1:]:
            value = ' '.join(cell['words'])
            seeds = re.fullmatch(r'(?:seeds|seeders)\s+(\d[\d, ]*)', value, re.I)
            if seeds:
                seeders = integer(seeds[1].replace(',', '').replace(' ', ''))
            if size is None:
                size = size_bytes(value)
        return seeders, size


class X1337(PublicTableSource):
    name = '1337x'
    base = 'https://1337x.to/'
    detail_path = re.compile(r'/torrent/\d+/[^/]+/?')

    def search_url(self, query):
        return self.base + 'search/' + quote(query, safe='') + '/1/'

    def search(self, query):
        rows = super().search(query)
        details = [row for row in rows if not (row.magnet or row.torrent)][:3]
        if details:
            with ThreadPoolExecutor(max_workers=len(details)) as pool:
                list(pool.map(self.add_download_links, details))
        return rows

    def add_download_links(self, row):
        try:
            body = get(row.page)
        except (URLError, OSError, ValueError):
            return  # A página da publicação continua disponível na lista.
        parser = Anchors()
        parser.feed(body)
        row.magnet, row.torrent = download_links(parser.links, self.base)
        row.infohash = magnet_hash(row.magnet)

    def stats(self, cells):
        seeders = size = None
        for cell in cells:
            value = ' '.join(cell['words'])
            if 'seeds' in cell['classes']:
                seeders = integer(value.replace(',', ''))
            elif 'size' in cell['classes']:
                size = size_bytes(value)
        return seeders, size


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class JackettSource:
    def __init__(self, name, indexer, port, key):
        self.name = name
        self.indexer = indexer
        self.port = port
        self.key = key

    def search(self, query):
        base = f'http://127.0.0.1:{self.port}'
        url = query_url(
            base + f'/api/v2.0/indexers/{self.indexer}/results/torznab/api',
            apikey=self.key, t='search', q=query, limit=100,
        )
        opener = build_opener(ProxyHandler({}), NoRedirect())
        try:
            with opener.open(url, timeout=15) as response:
                body = response.read(5_000_001)
        except HTTPError as err:
            raise ValueError(f'Jackett respondeu com HTTP {err.code}') from None
        except (URLError, OSError):
            raise ValueError('Jackett local indisponível. Confira a porta e se ele está aberto.') from None
        if len(body) > 5_000_000:
            raise ValueError('Resposta do Jackett acima do limite de 5 MB')
        try:
            channel = rss_channel(body)
        except ET.ParseError:
            raise ValueError('O Jackett não retornou um feed XML válido') from None
        rows = []
        for item in channel.findall('item')[:100]:
            title = item.findtext('title', '').strip()
            attrs = {
                attr.get('name'): attr.get('value', '')
                for attr in item if attr.tag.endswith('}attr')
            }
            enclosure = item.find('enclosure')
            enclosure_url = enclosure.get('url', '') if enclosure is not None else ''
            link = item.findtext('link', '')
            magnet = next((uri for uri in (attrs.get('magneturl'), link, enclosure_url) if magnet_hash(uri)), '')
            digest = magnet_hash(magnet) or normalize_hash(attrs.get('infohash'))
            # O Jackett faz o download usando a sessão já configurada no indexador.
            torrent = next((
                uri for uri in (enclosure_url, link)
                if uri.startswith(base + '/')
            ), '')
            if title and (magnet or torrent):
                rows.append(Result(
                    title, self.name, torrent=torrent, magnet=magnet, infohash=digest,
                    category=item.findtext('category', '') or attrs.get('category', ''),
                    language=attrs.get('language', ''), quality=quality_from(title),
                    size=integer(item.findtext('size') or attrs.get('size')),
                    seeders=integer(attrs.get('seeders')), page=https(item.findtext('comments', '')),
                    published=publication_date(item.findtext('pubDate')),
                ))
        return rows
