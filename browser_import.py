import json
import re

from core import Result, integer, magnet_hash, publication_date, quality_from, valid_magnet
from extra_sources import ExtTo, X1337, size_bytes, text


def read_browser_results(payload):
    if len(payload) > 500_000:
        raise ValueError('O conteúdo copiado é grande demais.')
    try:
        data = json.loads(payload)
    except (ValueError, RecursionError):
        raise ValueError('O navegador do app não retornou resultados válidos.') from None
    if not isinstance(data, dict) or data.get('format') != 'torrentfindr-page-v1':
        raise ValueError('O navegador do app não retornou resultados válidos.')
    site = data.get('site')
    if site == 'ext.to':
        source = ExtTo()
    elif site == '1337x.to':
        source = X1337()
    else:
        raise ValueError('Esta fonte não é aceita pelo navegador do app.')
    items = data.get('items')
    if not isinstance(items, list) or len(items) > 50:
        raise ValueError('O navegador precisa retornar até 50 resultados.')
    if not items:
        return []

    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = text(item.get('title'))[:500]
        path = text(item.get('page'))
        if not title or len(path) > 2048 or not source.detail_path.fullmatch(path) or re.search(r'[\s\\?#\x00-\x1f\x7f]', path):
            continue
        magnet = text(item.get('magnet'))
        digest = magnet_hash(magnet) if len(magnet) <= 4096 else ''
        torrent = text(item.get('torrent'))
        if not re.fullmatch(r'/(?!/)[\w/.-]{1,1000}\.torrent', torrent, re.I):
            torrent = ''
        seeds = re.fullmatch(r'(?:seeds?\s+)?([\d, ]{1,20})', text(item.get('seeders')), re.I)
        rows.append(Result(
            title=title, source=source.name, page=source.base.rstrip('/') + path,
            magnet=magnet if len(magnet)<=4096 and valid_magnet(magnet) else '', infohash=digest,
            torrent=source.base.rstrip('/') + torrent if torrent else '',
            quality=quality_from(title), size=size_bytes(text(item.get('size'))[:40]),
            seeders=integer(seeds[1].replace(',', '').replace(' ', '')) if seeds else None,
            published=publication_date(text(item.get('published'))[:64]),
        ))
    if not rows:
        raise ValueError('Nenhum resultado copiado tem um endereço de publicação válido.')
    return rows
