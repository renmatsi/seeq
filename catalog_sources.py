"""Catálogos públicos compartilhados pela interface do seeq e pelo MCP."""

import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from time import monotonic
from urllib.parse import unquote, urljoin, urlsplit

from core import Links, Result, get, integer, magnet_for, normalize_hash, publication_date, valid_magnet
from extra_sources import SearchTable, json_object, query_url, rss_channel, size_bytes, text
from search_filters import folded


def search_text(value):
    return frozenset(re.findall(r'[^\W_]+', folded(value)))


def torrent_link(value, base, *hosts):
    url = urljoin(base, value)
    parsed = urlsplit(url)
    if parsed.scheme == 'https' and parsed.netloc in hosts and parsed.path.lower().endswith('.torrent'):
        return url
    return ''


class PublicCatalog:
    refresh_seconds = 3600

    def __init__(self):
        self.lock = threading.Lock()
        self.expires = 0
        self.index = ()

    def search(self, query):
        terms = search_text(query)
        if not terms:
            return []
        with self.lock:
            if monotonic() >= self.expires:
                self.index = [
                    (row, search_text(row.title), search_text(f'{row.title} {context}'))
                    for row, context in self.read_catalog()
                ]
                if not self.index:
                    raise ValueError('O catálogo não retornou torrents válidos.')
                self.expires = monotonic() + self.refresh_seconds
            index = self.index

        matches = [
            (terms <= title, row)
            for row, title, context in index
            if terms <= context
        ]
        matches.sort(key=lambda match: (match[0], match[1].published), reverse=True)
        # A busca unificada altera resultados ao mesclar infohashes de várias fontes.
        return [replace(row, source_dates={}) for _, row in matches[:50]]


class FossTorrents(PublicCatalog):
    name = 'FOSS Torrents'
    endpoint = 'https://fosstorrents.com/feed/torrents.xml'

    def read_catalog(self):
        for item in rss_channel(get(self.endpoint)).findall('item'):
            title = item.findtext('title', '').strip()
            torrent = torrent_link(item.findtext('link', ''), self.endpoint, 'fosstorrents.com')
            if title and torrent:
                filename = unquote(urlsplit(torrent).path.rsplit('/', 1)[-1]).removesuffix('.torrent')
                yield Result(
                    title, self.name, torrent=torrent, page='https://fosstorrents.com/',
                    published=publication_date(item.findtext('pubDate')),
                ), f"{filename} {item.findtext('description', '')}"


class AcademicTorrents(PublicCatalog):
    name = 'Academic Torrents'
    endpoint = 'https://academictorrents.com/database.xml'
    refresh_seconds = 86400

    def read_catalog(self):
        for item in rss_channel(get(self.endpoint)).findall('item'):
            title = item.findtext('title', '').strip()
            infohash = normalize_hash(item.findtext('infohash', ''))
            if title and infohash:
                yield Result(
                    title, self.name, magnet=magnet_for(infohash, title), infohash=infohash,
                    page=f'https://academictorrents.com/details/{infohash}',
                    category=item.findtext('category', '').strip(),
                    size=integer(item.findtext('size')),
                    published=publication_date(item.findtext('pubDate')),
                ), item.findtext('description', '')


class Ubuntu(PublicCatalog):
    name = 'Ubuntu oficial'
    endpoint = 'https://ubuntu.com/download/alternative-downloads'

    def read_catalog(self):
        page = Links()
        page.feed(get(self.endpoint))
        for href in dict.fromkeys(page.links):
            torrent = torrent_link(href, self.endpoint, 'releases.ubuntu.com', 'cdimage.ubuntu.com')
            if torrent:
                filename = unquote(urlsplit(torrent).path.rsplit('/', 1)[-1]).removesuffix('.torrent')
                yield Result(
                    filename.removesuffix('.iso'), self.name, torrent=torrent, category='software',
                    page=self.endpoint, file_format='ISO',
                ), 'Linux'


class Fedora(PublicCatalog):
    name = 'Fedora oficial'
    endpoint = 'https://torrent.fedoraproject.org/index.html'

    def read_catalog(self):
        for cells in SearchTable(get(self.endpoint)).rows:
            if len(cells) < 5 or not cells[0]['links']:
                continue
            href, _ = cells[0]['links'][0]
            torrent = torrent_link(href, self.endpoint, 'torrent.fedoraproject.org')
            title = ' '.join(cells[1]['words'])
            if title and torrent:
                yield Result(
                    title, self.name, torrent=torrent, category='software', page=self.endpoint,
                    file_format='ISO', size=size_bytes(' '.join(cells[2]['words'])),
                    published=publication_date(' '.join(cells[4]['words'])),
                ), 'Linux'


class BlenderVideo:
    name = 'Blender Video'
    base = 'https://video.blender.org'

    def search(self, query):
        data = json_object(query_url(
            self.base + '/api/v1/search/videos', search=query, count=6, isLocal='true',
        )).get('data')
        if not isinstance(data, list):
            raise ValueError('Resposta inesperada da fonte')
        ids = [
            video['uuid'] for video in data[:6]
            if video.get('isLocal') and re.fullmatch(r'[\da-f-]{36}', text(video.get('uuid')), re.ASCII)
        ]
        rows, errors = {}, []
        with ThreadPoolExecutor(max_workers=3) as pool:
            requests = {pool.submit(self.video_results, video_id): video_id for video_id in ids}
            for request in as_completed(requests):
                try:
                    rows[requests[request]] = request.result()
                except (OSError, ValueError) as error:
                    errors.append(error)
        results = [row for video_id in ids for row in rows.get(video_id, ())]
        if errors and not results:
            raise errors[0]
        return results

    def video_results(self, video_id):
        video = json_object(f'{self.base}/api/v1/videos/{video_id}')
        title = text(video.get('name'))
        if not title or not video.get('isLocal') or video.get('downloadEnabled') is not True:
            return []
        files = video.get('files') or [
            file for playlist in video.get('streamingPlaylists', []) for file in playlist.get('files', [])
        ]
        rows = []
        for file in files:
            if file.get('hasVideo') is False or file.get('hasAudio') is False:
                continue
            torrent = torrent_link(
                file.get('torrentDownloadUrl') or file.get('torrentUrl') or '', self.base, 'video.blender.org',
            )
            magnet = text(file.get('magnetUri'))
            if not valid_magnet(magnet):
                magnet = ''
            if torrent or magnet:
                rows.append(Result(
                    title, self.name, torrent=torrent, magnet=magnet,
                    page=f'{self.base}/w/{video_id}', category='Vídeos',
                    quality=text((file.get('resolution') or {}).get('label')),
                    language=text((video.get('language') or {}).get('id')),
                    size=integer(file.get('size')), file_format='MP4',
                    published=publication_date(video.get('publishedAt')),
                ))
        return rows


def catalog_providers():
    return [FossTorrents(), AcademicTorrents(), BlenderVideo(), Ubuntu(), Fedora()]
