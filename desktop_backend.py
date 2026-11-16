"""Mecanismo local do seeq. Recebe comandos JSON e envia estados pela mesma sessão."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
import importlib.util
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
import webbrowser

from browser_import import read_browser_results
from catalog_sources import catalog_providers
from core import Archive, Debian, Nyaa, PirateBay, Result, dedup, source_error, valid_magnet
from extra_sources import ExtTo, EZTV, FitGirl, JackettSource, SubsPlease, X1337, YTS
from search_filters import Filters, GIB, ORDERS, date_label, folded, interpret, link_types, publication, result_format, result_sources, result_values


PROJECT = Path(sys.executable).resolve().parents[1] if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
DATA = Path(os.getenv('APPDATA') or Path.home()) / 'torrentFindr'
FILE = DATA / 'dados.json'
TRACKERS = {'RuTracker':'rutracker','CGPeers':'cgpeers'}
FACETS = ('source','category','language','quality','format','link')
THEMES = ('Sistema','Papel','Grafite','Meia-noite','AMOLED')
BACKDROP_BLENDS = ('auto','soft-light','screen','multiply')
LOCALES = ('pt-BR','en','es','ru','ja','zh-Hans')
APP_VERSION = '1.1.0'
DEVELOPER = 'Renan Matos'
SITE = 'https://renmatsi.github.io/'


def send(kind, **fields):
    print(json.dumps({'type':kind, **fields}, ensure_ascii=False), flush=True)


def embedded(url, automatic, canceled=None):
    browser = PROJECT / 'browser' / 'TorrentFindr.Browser.exe'
    if not browser.is_file():
        raise ValueError('Navegador integrado indisponível.')
    flags = ['--auto'] if automatic else []
    env = os.environ.copy()
    fixed = PROJECT / 'webview2-runtime'
    if fixed.is_dir():
        env['WEBVIEW2_BROWSER_EXECUTABLE_FOLDER'] = str(fixed)
    if canceled and canceled.is_set():
        return []
    deadline = time.monotonic()+155 if automatic else None
    with subprocess.Popen([str(browser),*flags,url,str(DATA/'webview2')], stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, encoding='utf-8', errors='replace', env=env,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)) as process:
        while True:
            if canceled and canceled.is_set():
                process.kill()
                process.communicate()
                return []
            if deadline and time.monotonic() >= deadline:
                process.kill()
                process.communicate()
                raise ValueError('A página não respondeu dentro do prazo.')
            try:
                output,_ = process.communicate(timeout=.4 if automatic else None)
                break
            except subprocess.TimeoutExpired:
                continue
        code = process.returncode
    if code:
        problems = {5:'A página não exibiu resultados no prazo.',6:'A fonte limitou as consultas.',
                    7:'A verificação da fonte ficou pendente.'}
        raise ValueError(problems.get(code,'O navegador integrado não iniciou.'))
    if not output:
        return []
    return read_browser_results(output)


def read_profile():
    DATA.mkdir(parents=True, exist_ok=True)
    try:
        obj = json.loads(FILE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        obj = {}
    return obj if isinstance(obj,dict) else {}


class Desk:
    def __init__(self):
        self.data = read_profile()
        for key, default in [('history',[]),('favorites',[]),('enabled',{}),('appearance',{})]:
            if not isinstance(self.data.get(key),type(default)):
                self.data[key] = default
        self.inbox = queue.Queue()
        self.rows = []
        self.favorites = []
        for item in self.data['favorites']:
            try:
                self.favorites.append(Result(**item))
            except (TypeError, ValueError):
                continue
        self.keys = {}
        self.filters = Filters()
        self.inferred = set()
        self.term = ''
        self.raw = ''
        self.order = ORDERS[0]
        self.view = 'Busca'
        self.status = 'Digite um termo e pressione Enter.'
        self.running = False
        self.browser_open = False
        self.failures = {}
        self.responded = set()
        self.query_sources = []
        self.ticket = None
        self.jackett_key = ''
        self.ext, self.x1337 = ExtTo(), X1337()
        self.builtins = [
            Archive(), Debian(), PirateBay(), Nyaa(), YTS(), EZTV(), SubsPlease(), FitGirl(), self.x1337, self.ext,
            *catalog_providers(),
        ]
        self.plugins = {}
        folder = DATA/'providers'
        folder.mkdir(exist_ok=True)
        self.plugin_files = sorted(folder.glob('*.py'))
        for file in self.plugin_files:
            key = 'plugin:'+file.name
            if self.data['enabled'].get(key):
                try:
                    spec = importlib.util.spec_from_file_location('tf_'+file.stem,file)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    self.plugins[key] = mod.Provider()
                except Exception:
                    self.failures[file.name] = 'Plugin não carregado.'

    def save(self):
        temporary = FILE.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(FILE)

    def sources(self):
        return (
            [{'key':item.name,'name':item.name,'enabled':bool(self.data['enabled'].get(item.name,True))}
             for item in self.builtins]
            + [{'key':'plugin:'+file.name,'name':file.name,'enabled':bool(self.data['enabled'].get('plugin:'+file.name)),'plugin':True}
               for file in self.plugin_files]
            + [{'key':name,'name':name,'enabled':bool(self.data['enabled'].get(name)),'tracker':True} for name in TRACKERS]
        )

    def serialize_row(self,row):
        key = str(id(row))
        self.keys[key] = row
        published = publication(row,self.filters.source)
        return dict(id=key,title=row.title,source=row.source,size=self.size(row.size),published=date_label(published),
                    year=row.release_year,seeders=row.seeders,category=row.category,language=row.language,
                    quality=row.quality,format=result_format(row),links=link_types(row),
                    magnet=valid_magnet(row.magnet),torrent=bool(row.torrent),page=bool(row.page),
                    favorite=any(self.favorite_key(item)==self.favorite_key(row) for item in self.favorites))

    @staticmethod
    def favorite_key(item):
        return item.infohash or item.page or (item.title,item.source)

    @staticmethod
    def size(value):
        if value is None:
            return '—'
        return (f'{value/GIB:.2f} GB' if value>=GIB else f'{value/1024**2:.0f} MB').replace('.',',')

    def ordered(self,rows):
        if self.order == 'Mais seeders':
            return sorted(rows,key=lambda item:item.seeders if item.seeders is not None else -1,reverse=True)
        if self.order == 'Menor tamanho':
            return sorted(rows,key=lambda item:item.size if item.size is not None else float('inf'))
        if self.order in ('Mais recentes','Mais antigos'):
            dated = [item for item in rows if publication(item,self.filters.source)]
            undated = [item for item in rows if not publication(item,self.filters.source)]
            return sorted(dated,key=lambda item:publication(item,self.filters.source),reverse=self.order=='Mais recentes')+undated
        term = folded(self.term)
        return sorted(rows,key=lambda item:(term in folded(item.title),sum(word in folded(item.title) for word in term.split()),
                      item.seeders if item.seeders is not None else -1),reverse=True) if term else rows

    def facets(self,rows):
        facets = {}
        for name in FACETS:
            counts = Counter()
            for row in rows:
                values = {value for value in result_values(row,name) if value}
                if name=='source':
                    counts.update(value for value in values if replace(self.filters,source=value).matches(row))
                elif self.filters.matches(row,omit=name):
                    counts.update(values)
            facets[name] = sorted(counts.items(),key=lambda pair:pair[0].casefold())
        return facets

    def snapshot(self):
        self.keys.clear()
        source = self.favorites if self.view=='Favoritos' else self.rows
        matches = self.ordered([item for item in source if self.filters.matches(item)])
        send('state', rows=[self.serialize_row(item) for item in matches], total=len(source), view=self.view,
             status=self.status, running=self.running, query=self.raw, browserOpen=self.browser_open, filters=asdict(self.filters),
             chips=self.filters.chips(), inferred=[key for key,_ in self.filters.chips() if key in self.inferred],
             order=self.order, sources=self.sources(), history=self.data['history'][-100:],
             responded=sorted(self.responded), failures=self.failures, querySources=self.query_sources,
             appearance=self.data['appearance'], locale=self.data.get('locale','pt-BR'), facets=self.facets(source),
             jackettPort=self.data.get('jackett_port',9117), jackettReady=bool(self.jackett_key),
             version=APP_VERSION, developer=DEVELOPER, site=SITE)

    def search(self,raw,smart):
        if self.browser_open:
            return
        raw = raw.strip()[:400]
        if not raw:
            raise ValueError('Digite um termo de busca.')
        names = [source['name'] for source in self.sources()]
        term, inferred = interpret(raw,names) if smart else (raw,{})
        if not term:
            raise ValueError('Inclua uma palavra-chave além dos filtros.')
        defaults = Filters()
        new = replace(self.filters,**{key:getattr(defaults,key) for key in self.inferred})
        if 'period' in inferred:
            inferred.update(from_date='',to_date='',unknown_dates=False)
        new = replace(new,**inferred)
        new.validate_size()
        enabled = self.data['enabled']
        active = [item for item in self.builtins if enabled.get(item.name,True)]
        active.extend(self.plugins.values())
        port = int(self.data.get('jackett_port',9117))
        if self.jackett_key:
            active.extend(JackettSource(name,TRACKERS[name],port,self.jackett_key)
                          for name in TRACKERS if enabled.get(name))
        if not active:
            raise ValueError('Ative uma fonte em Fontes para pesquisar.')
        if self.ticket:
            self.ticket.set()
        ticket = self.ticket = threading.Event()
        self.running, self.raw, self.term, self.view = True, raw, term, 'Busca'
        self.filters, self.inferred = new, set(inferred)
        self.rows = []
        self.failures = {name:'Informe a chave do Jackett em Fontes.' for name in TRACKERS
                         if enabled.get(name) and not self.jackett_key}
        self.responded.clear()
        self.query_sources = [item.name for item in active]
        self.data['history'] = ([q for q in self.data['history'] if q != raw]+[raw])[-100:]
        self.status = f'Buscando “{term}”…'
        self.save()
        self.snapshot()

        def run_browsers(integrated):
            for item in integrated:
                if ticket.is_set():
                    break
                try:
                    self.inbox.put(('batch',ticket,item.name,embedded(item.search_url(term),True,ticket),None))
                except Exception as error:
                    self.inbox.put(('batch',ticket,item.name,[],str(error)))

        def run():
            integrated = [item for item in (self.ext,self.x1337) if item in active]
            direct = [item for item in active if item not in integrated]
            with ThreadPoolExecutor(max_workers=min(6,len(direct))+bool(integrated)) as pool:
                if integrated:
                    pool.submit(run_browsers,integrated)
                futures = {pool.submit(item.search,term):item.name for item in direct}
                for future in as_completed(futures):
                    if ticket.is_set():
                        for pending in futures:
                            pending.cancel()
                        break
                    try:
                        self.inbox.put(('batch',ticket,futures[future],future.result(),None))
                    except Exception as error:
                        self.inbox.put(('batch',ticket,futures[future],[],source_error(error)))
            self.inbox.put(('done',ticket))
        threading.Thread(target=run,daemon=True).start()

    def manual_browser(self, url):
        if self.running or self.browser_open:
            raise ValueError('Aguarde a busca ou a janela integrada atual.')
        self.browser_open = True
        self.status = 'Abrindo a publicação…'
        self.snapshot()
        def run():
            try:
                self.inbox.put(('manual',embedded(url,False),None))
            except Exception as error:
                self.inbox.put(('manual',[],str(error)))
        threading.Thread(target=run,daemon=True).start()

    def open_result(self,row,kind):
        if kind not in ('magnet','torrent','page'):
            return
        link = getattr(row,kind)
        if kind=='magnet':
            if not valid_magnet(link):
                raise ValueError('Este resultado não tem um magnet válido.')
            try:
                os.startfile(link)
            except OSError:
                raise ValueError('Associe um cliente BitTorrent a links magnet no Windows.') from None
            return
        url = urlsplit(link)
        if url.scheme not in ('http','https') or not url.hostname:
            raise ValueError('A fonte não informou este link.')
        if kind=='page' and url.hostname in ('ext.to','1337x.to'):
            self.manual_browser(link)
        else:
            webbrowser.open(link)

    def handle(self, message):
        action = message.get('action')
        if action=='search':
            self.search(str(message.get('query','')),bool(message.get('smart')))
            return
        if action=='cancel':
            if self.running and self.ticket:
                self.ticket.set()
                self.running = False
                self.status = f'Busca cancelada · {len(self.rows)} resultado(s) preservados.'
                self.snapshot()
            return
        if action=='open':
            row = self.keys.get(str(message.get('id')))
            if row:
                self.open_result(row,message.get('kind'))
            return
        if action=='site':
            webbrowser.open(SITE)
            return
        if action=='manual':
            term = str(message.get('query','')).strip()[:400]
            if not term:
                raise ValueError('Digite um termo de busca.')
            source = next((item for item in (self.ext,self.x1337) if item.name==message.get('source')),None)
            if source:
                self.manual_browser(source.search_url(interpret(term)[0] or term))
            return
        if action=='view' and message.get('view') in ('Busca','Favoritos'):
            self.view = message['view']
        elif action=='sort' and message.get('order') in ORDERS:
            self.order = message['order']
        elif action=='history-remove':
            term = message.get('query')
            if isinstance(term,str) and term in self.data['history']:
                self.data['history'] = [item for item in self.data['history'] if item != term]
                self.save()
        elif action=='history-clear' and self.data['history']:
            self.data['history'] = []
            self.save()
        elif action=='locale' and message.get('locale') in LOCALES:
            self.data['locale'] = message['locale']
            self.save()
        elif action=='filters':
            defaults = asdict(Filters())
            values = message.get('values',{})
            raw = {key:str(values.get(key) or '') for key in defaults}
            raw['unknown_dates'] = bool(values.get('unknown_dates'))
            if raw['period'] not in ('','1','7','30','90','custom') and raw['period'] != self.filters.period:
                raw['period'] = ''
            self.filters = Filters.from_form(raw)
            self.inferred.clear()
        elif action in ('clear','remove','period'):
            key = message.get('key')
            if action=='clear':
                self.filters = Filters()
                self.inferred.clear()
            elif action=='period' or key=='period':
                period = message.get('period','')
                if period in ('','1','7','30','90'):
                    self.filters = replace(self.filters,period=period,from_date='',to_date='',unknown_dates=False)
                    self.inferred.difference_update(('period','from_date','to_date','unknown_dates'))
            elif isinstance(key,str) and key in asdict(Filters()):
                self.filters = replace(self.filters,**{key:getattr(Filters(),key)})
                self.inferred.discard(key)
        elif action=='favorite':
            row = self.keys.get(str(message.get('id')))
            if row:
                existing = next((item for item in self.favorites if self.favorite_key(item)==self.favorite_key(row)),None)
                if existing:
                    self.favorites.remove(existing)
                    self.status = 'Resultado removido dos favoritos.'
                else:
                    private = set(result_sources(row)).intersection(TRACKERS)
                    self.favorites.append(replace(row,magnet='',torrent='') if private else replace(row))
                    self.status = 'Resultado salvo nos favoritos.'
                self.data['favorites'] = [asdict(item) for item in self.favorites]
                self.save()
        elif action=='appearance':
            theme, accent = message.get('theme'), message.get('accent')
            if theme in THEMES and isinstance(accent,str) and len(accent)==7 and accent[0]=='#':
                int(accent[1:],16)
                appearance = self.data['appearance']
                appearance.update(theme=theme,accent=accent)
                if isinstance(message.get('backdrop'),bool):
                    appearance['backdrop'] = message['backdrop']
                if message.get('blend') in BACKDROP_BLENDS:
                    appearance['blend'] = message['blend']
                opacity = message.get('backdropOpacity')
                if type(opacity) is int and 5 <= opacity <= 30:
                    appearance['backdropOpacity'] = opacity
                self.save()
        elif action=='sources':
            values = message.get('enabled',{})
            port = int(message.get('port',9117))
            if not 1 <= port <= 65535:
                raise ValueError('Informe uma porta do Jackett entre 1 e 65535.')
            for source in self.sources():
                key = source['key']
                self.data['enabled'][key] = bool(values.get(key,source['enabled']))
                if source.get('plugin') and not self.data['enabled'][key]:
                    self.plugins.pop(key,None)
            key = str(message.get('apiKey','')).strip()[:1024]
            if key:
                self.jackett_key = key
            self.data['jackett_port'] = port
            self.save()
            self.status = 'Fontes salvas. Reinicie para carregar plugins recém-ativados.'
        self.snapshot()

    def loop(self):
        def read():
            for line in sys.stdin:
                try:
                    obj = json.loads(line)
                    if isinstance(obj,dict):
                        self.inbox.put(('command',obj))
                except ValueError:
                    continue
            self.inbox.put(('exit',))
        threading.Thread(target=read,daemon=True).start()
        while True:
            kind,*args = self.inbox.get()
            try:
                if kind=='exit':
                    return
                if kind=='command':
                    self.handle(args[0])
                elif kind=='batch':
                    ticket, name, results, error = args
                    if ticket is not self.ticket or ticket.is_set():
                        continue
                    if error:
                        self.failures[name] = error[:350]
                    else:
                        self.responded.add(name)
                        self.rows = dedup(self.rows+results)
                    self.snapshot()
                elif kind=='done':
                    if args[0] is not self.ticket or args[0].is_set():
                        continue
                    self.running = False
                    self.status = f'Busca concluída · {len(self.rows)} resultado(s).'
                    self.snapshot()
                elif kind=='manual':
                    self.browser_open = False
                    results,error = args
                    pages = {item.page:item for item in self.rows if item.page}
                    for result in results:
                        if old := pages.get(result.page):
                            for field in ('magnet','torrent','published','infohash'):
                                if getattr(result,field) and not getattr(old,field):
                                    setattr(old,field,getattr(result,field))
                        else:
                            self.rows.append(result)
                    self.rows = dedup(self.rows)
                    self.status = error or ('Resultado importado.' if results else 'Janela fechada.')
                    self.snapshot()
            except Exception as error:
                send('status',message=str(error)[:350])


if __name__ == '__main__':
    Desk().loop()
