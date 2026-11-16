import json, urllib.request, urllib.parse, urllib.error, re, html, base64
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

@dataclass
class Result:
    title:str
    source:str
    torrent:str=''
    magnet:str=''
    infohash:str=''
    category:str=''
    language:str=''
    quality:str=''
    size:int|None=None
    seeders:int|None=None
    page:str=''
    published: str = ''
    release_year: int | None = None
    file_format: str = ''
    source_dates: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        # Fontes como o apibay entregam títulos com entidades HTML (&euml; etc.).
        self.title = html.unescape(self.title)


def publication_date(value):
    """Normaliza uma data informada pelo provedor. Vazio representa ausência."""
    if value in ('', None, 0, '0'):
        return ''
    try:
        if isinstance(value, (int, float)) or re.fullmatch(r'\d{9,13}', str(value)):
            timestamp = float(value)
            if timestamp > 100_000_000_000:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
        value = str(value).strip()
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date().isoformat()
        except ValueError:
            return parsedate_to_datetime(value).date().isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return ''

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'torrentFindr/0.1 (desktop prototype)'})
    with urllib.request.urlopen(req,timeout=15) as f:
        body = f.read(5_000_001)
        if len(body) > 5_000_000:
            raise ValueError('Resposta acima do limite de 5 MB')
        return body.decode('utf-8-sig', 'replace')

def source_error(error):
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(reason, socket.gaierror):
        return 'O DNS não conseguiu resolver o endereço da fonte.'
    return str(error)

def normalize_hash(h):
    if not isinstance(h, str): return ''
    h=h.strip().upper()
    if re.fullmatch('[0-9A-F]{40}',h): return h.lower()
    if re.fullmatch('[A-Z2-7]{32}',h):
        try: return base64.b32decode(h).hex()
        except ValueError: pass
    return ''

def magnet_hash(uri):
    if not isinstance(uri, str) or not uri.lower().startswith('magnet:?'):
        return ''
    params = urllib.parse.parse_qs(uri[8:])
    for value in params.get('xt', []):
        if value.lower().startswith('urn:btih:'):
            digest = normalize_hash(value[9:])
            if digest:
                return digest
    return ''


def valid_magnet(uri):
    if magnet_hash(uri):
        return True
    if not isinstance(uri,str) or not uri.lower().startswith('magnet:?'):
        return False
    return any(re.fullmatch(r'urn:btmh:1220[0-9a-f]{64}', value, re.I)
               for value in urllib.parse.parse_qs(uri[8:]).get('xt', []))

def dedup(rows):
    out=[]; seen={}
    for r in rows:
        if r.published and not r.source_dates and ', ' not in r.source:
            r.source_dates[r.source] = r.published
        h=normalize_hash(r.infohash) or magnet_hash(r.magnet)
        r.infohash=h
        if h and h in seen:
            old=seen[h]; old.source=', '.join(dict.fromkeys((old.source+', '+r.source).split(', ')))
            for source, day in r.source_dates.items():
                if day:
                    old.source_dates[source] = max(day,old.source_dates.get(source,''))
            old.published = max(old.published, r.published, *old.source_dates.values())
            for field in ('magnet','torrent','category','language','quality','size','seeders','page','release_year','file_format'):
                if getattr(old,field) in ('',None): setattr(old,field,getattr(r,field))
        else:
            out.append(r)
            if h: seen[h]=r
    return out

class Archive:
    name='Internet Archive'
    def search(self,q):
        query=urllib.parse.urlencode({'q':q,'fl[]':['identifier','title','mediatype','language'],'rows':50,'output':'json'},doseq=True)
        data=json.loads(get('https://archive.org/advancedsearch.php?'+query))
        rows=[]
        for d in data['response']['docs']:
            ident=d.get('identifier',''); title=d.get('title',ident)
            if not ident: continue
            lang=d.get('language',''); lang=', '.join(lang) if isinstance(lang,list) else str(lang)
            url='https://archive.org/download/'+urllib.parse.quote(ident,safe='')+'/'+urllib.parse.quote(ident+'_archive.torrent',safe='')
            rows.append(Result(str(title),self.name,torrent=url,category=str(d.get('mediatype','')),language=lang))
        return rows

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            h=dict(attrs).get('href','')
            if h.lower().endswith('.torrent'): self.links.append(h)

class Debian:
    name='Debian oficial'
    def search(self,q):
        base='https://cdimage.debian.org/debian-cd/current/amd64/bt-cd/'
        p=Links(); p.feed(get(base)); rows=[]
        for link in p.links:
            title=urllib.parse.unquote(link.rsplit('/',1)[-1])
            if q.casefold() in title.casefold(): rows.append(Result(title,self.name,torrent=urllib.parse.urljoin(base,link),category='software'))
        return rows

# Indexadores públicos: o conteúdo e os direitos variam por resultado.
def magnet_for(h,title):
    h=normalize_hash(h)
    return 'magnet:?'+urllib.parse.urlencode({'xt':'urn:btih:'+h,'dn':title}) if h else ''

def integer(v):
    try: return int(v)
    except (ValueError, TypeError): return None

def quality_from(title):
    m=re.search(r'(?i)\b(2160p|1080p|720p|480p|4k)\b',title)
    return m.group(1).lower() if m else ''

class PirateBay:
    name='The Pirate Bay'
    def search(self,q):
        data=json.loads(get('https://apibay.org/q.php?'+urllib.parse.urlencode({'q':q,'cat':'0'})))
        if not isinstance(data,list): raise ValueError('Resposta inesperada da fonte')
        rows=[]
        for x in data:
            if str(x.get('id'))=='0': continue
            title=html.unescape(x.get('name','')); h=normalize_hash(x.get('info_hash',''))
            if not title or not h: continue
            rows.append(Result(title,self.name,magnet=magnet_for(h,title),infohash=h,category=str(x.get('category','')),quality=quality_from(title),size=integer(x.get('size')),seeders=integer(x.get('seeders')),published=publication_date(x.get('added'))))
        return rows

class Nyaa:
    name='Nyaa'
    def search(self,q):
        import xml.etree.ElementTree as ET
        url='https://nyaa.si/?'+urllib.parse.urlencode({'page':'rss','q':q})
        root=ET.fromstring(get(url)); rows=[]
        ns='{https://nyaa.si/xmlns/nyaa}'
        for x in root.findall('./channel/item'):
            title=x.findtext('title',''); h=normalize_hash(x.findtext(ns+'infoHash',''))
            link=x.findtext('link',''); seed=integer(x.findtext(ns+'seeders',''))
            rows.append(Result(title,self.name,torrent=link if link.startswith('https://') else '',magnet=magnet_for(h,title),infohash=h,category=x.findtext(ns+'category',''),quality=quality_from(title),seeders=seed,published=publication_date(x.findtext('pubDate'))))
        return rows
