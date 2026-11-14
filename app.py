import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import threading, queue, json, os, webbrowser, importlib.util
import subprocess
from urllib.parse import urlsplit
from pathlib import Path
from collections import Counter
from dataclasses import asdict, replace
from core import Result, Archive, Debian, PirateBay, Nyaa, dedup, valid_magnet
from browser_import import read_browser_results
from extra_sources import ExtTo, EZTV, FitGirl, JackettSource, SearchRefused, SubsPlease, X1337, YTS
from desktop_style import ACCENTS, DEFAULT_ACCENTS, THEMES, apply_style, magnet_icon, valid_color
from search_filters import Filters, GIB, ORDERS, PERIODS, date_label, folded, interpret, publication, result_format, result_sources, result_values
from window_chrome import install as install_chrome

DATA=Path(os.getenv('APPDATA',str(Path.home())))/'torrentFindr'
DATA.mkdir(parents=True,exist_ok=True)
FILE=DATA/'dados.json'
try: data=json.loads(FILE.read_text(encoding='utf-8'))
except (OSError,ValueError): data={}
data.setdefault('history',[]); data.setdefault('favorites',[]); data.setdefault('enabled',{})
def save():
    draft = FILE.with_suffix('.tmp')
    draft.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    draft.replace(FILE)
ext_to = ExtTo()
x1337 = X1337()
jackett_indexers = {'RuTracker': 'rutracker', 'CGPeers': 'cgpeers'}
jackett_key = ''
builtins = [Archive(), Debian(), PirateBay(), Nyaa(), YTS(), EZTV(), SubsPlease(), FitGirl(), x1337, ext_to]
providers = builtins.copy()
# Plugins são código Python local, carregado somente após habilitação explícita.
plugin_dir=DATA/'providers'; plugin_dir.mkdir(exist_ok=True)
plugin_errors=[]
for path in plugin_dir.glob('*.py'):
    if not data['enabled'].get('plugin:'+path.name,False): continue
    try:
        spec=importlib.util.spec_from_file_location('tf_'+path.stem,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); providers.append(mod.Provider())
    except Exception as e: plugin_errors.append(path.name+': '+str(e))

root = tk.Tk()
root.title('torrentFindr')
root.geometry('1250x745')
root.minsize(940, 570)
appearance = data.get('appearance', {})
if not isinstance(appearance, dict):
    appearance = {}
theme = appearance.get('theme', 'Grafite')
if theme not in THEMES:
    theme = 'Grafite'
accent = appearance.get('accent', DEFAULT_ACCENTS[theme])
if not valid_color(accent):
    accent = DEFAULT_ACCENTS[theme]
colors = apply_style(root, theme, accent)
magnet_image = magnet_icon(root, colors['accent'])

chrome = ttk.Frame(root, style='Chrome.TFrame', padding=(14,5,8,5))
chrome.pack(fill='x')
brand = ttk.Label(chrome, text='torrentFindr', style='Brand.TLabel')
brand.pack(side='left', padx=(2,11))
caption = ttk.Label(chrome, text='Mesa de pesquisa', style='Chrome.TLabel')
caption.pack(side='left')
close_button = ttk.Button(chrome, text='×', width=3, style='Close.TButton', command=root.destroy)
close_button.pack(side='right')
maximize_button = ttk.Button(chrome, text='□', width=3, style='Caption.TButton',
                             command=lambda: root.state('normal' if root.state() == 'zoomed' else 'zoomed'))
maximize_button.pack(side='right')
minimize_button = ttk.Button(chrome, text='−', width=3, style='Caption.TButton', command=root.iconify)
minimize_button.pack(side='right')
appearance_button = ttk.Button(chrome, text='⚙', width=3, style='Caption.TButton', command=lambda: appearance_panel())
appearance_button.pack(side='right', padx=(0,4))
drag_area = ttk.Frame(chrome, style='Chrome.TFrame')
drag_area.pack(side='left', fill='both', expand=True)

navigation = ttk.Frame(root, style='Chrome.TFrame', padding=(14,1,14,9))
navigation.pack(fill='x')
nav_search = ttk.Button(navigation, text='Busca', style='NavActive.TButton', command=lambda: set_view('Busca'))
nav_search.pack(side='left', padx=(0,4))
nav_favorites = ttk.Button(navigation, text='Favoritos', style='Nav.TButton', command=lambda: favorites())
nav_favorites.pack(side='left', padx=4)
ttk.Button(navigation, text='Histórico', style='Nav.TButton', command=lambda: history()).pack(side='left', padx=4)
ttk.Button(navigation, text='Fontes', style='Nav.TButton', command=lambda: config()).pack(side='left', padx=4)

main = ttk.Frame(root, padding=(20,12,20,8))
main.pack(fill='both', expand=True)
view_title = tk.StringVar(value='Busca')
ttk.Label(main, textvariable=view_title, style='Heading.TLabel').pack(anchor='w', pady=(0,6))
top = ttk.Frame(main)
top.pack(fill='x')
query = tk.StringVar()
entry = ttk.Entry(top, textvariable=query)
entry.pack(side='left', fill='x', expand=True)
ttk.Button(top, text='Buscar', style='Accent.TButton', command=lambda: search()).pack(side='left', padx=(8,0))
smart = tk.BooleanVar(value=True)
smart_line = ttk.Frame(main)
smart_line.pack(fill='x', pady=(5,6))
ttk.Checkbutton(smart_line, text='Interpretar filtros na busca', variable=smart).pack(side='left')
ttk.Label(smart_line, text='Exemplo: linux iso últimos 7 dias até 3 GB', style='Muted.TLabel').pack(side='left', padx=12)

quick = ttk.Frame(main)
quick.pack(fill='x')
filter_button = ttk.Button(quick, text='Filtros ▾', command=lambda: toggle_filters())
filter_button.pack(side='left', padx=(0,5))
for label in ('Qualquer data', 'Hoje', 'Últimos 7 dias', 'Últimos 30 dias'):
    ttk.Button(quick, text=label, command=lambda label=label: quick_period(PERIODS[label])).pack(side='left', padx=(0,5))
sort = tk.StringVar(value=ORDERS[0])
sort_box = ttk.Combobox(quick, textvariable=sort, values=ORDERS, state='readonly', width=16)
sort_box.pack(side='right')
sort_box.bind('<<ComboboxSelected>>', lambda _: show())
ttk.Label(quick, text='Ordenar', style='Muted.TLabel').pack(side='right', padx=(0,8))

filter_panel = ttk.Frame(main, style='Surface.TFrame', padding=12)
ttk.Label(filter_panel, text='Refinar resultados', style='Detail.TLabel').grid(row=0, column=0, columnspan=4, sticky='w')
fields = {}
facets = {}
for index, (key, label, choices) in enumerate((
    ('period','Publicação do torrent', tuple(PERIODS)),
    ('from_date','De · DD/MM/AAAA',None), ('to_date','Até · DD/MM/AAAA',None),
    ('year','Ano do conteúdo',None), ('source','Fonte',()), ('category','Categoria',()),
    ('language','Idioma',()), ('quality','Qualidade',()), ('format','Formato',()), ('link','Tipo de link',()),
    ('min_seeds','Seeders mín.',None), ('min_gb','Tamanho mín. (GB)',None), ('max_gb','Tamanho máx. (GB)',None),
)):
    row, col = divmod(index,4)
    cell = ttk.Frame(filter_panel, style='Surface.TFrame')
    cell.grid(row=row+1, column=col, sticky='ew', padx=(0,8), pady=(6,0))
    ttk.Label(cell, text=label, style='SurfaceMuted.TLabel').pack(anchor='w')
    fields[key] = tk.StringVar(value='Qualquer data' if key=='period' else '')
    if choices is None:
        control = ttk.Entry(cell, textvariable=fields[key], width=10)
    else:
        control = ttk.Combobox(cell, textvariable=fields[key], values=choices, width=14)
        if key == 'period':
            control.configure(state='readonly')
        else:
            facets[key] = control
    control.pack(fill='x')
for col in range(4):
    filter_panel.columnconfigure(col, weight=1, uniform='filters')
include_undated = tk.BooleanVar()
ttk.Checkbutton(filter_panel, text='Incluir itens sem data no período', variable=include_undated).grid(row=5,column=0,columnspan=2,sticky='w',pady=(8,0))
ttk.Button(filter_panel,text='Limpar',command=lambda: clear_filters()).grid(row=5,column=2,sticky='e',pady=(8,0),padx=6)
ttk.Button(filter_panel,text='Aplicar filtros',style='Accent.TButton',command=lambda: apply_filters()).grid(row=5,column=3,sticky='ew',pady=(8,0))
chips = ttk.Frame(main)
chips.pack(fill='x', pady=(7,0))

status = tk.StringVar(value='Digite um termo e pressione Enter.')
count_text = tk.StringVar(value='0 resultados')
summary = ttk.Frame(main)
summary.pack(fill='x', pady=(6,8))
ttk.Label(summary,textvariable=count_text).pack(side='left')
details_button = ttk.Button(summary,text='Recolher detalhes',command=lambda: toggle_details())
details_button.pack(side='right')

workspace = ttk.Frame(main)
workspace.pack(fill='both',expand=True)
workspace.columnconfigure(0,weight=1)
workspace.rowconfigure(0,weight=1)
listing = ttk.Frame(workspace)
listing.grid(row=0,column=0,sticky='nsew')
cols = ('title','source','size','published','seeders')
tree = ttk.Treeview(listing, columns=cols, show='tree headings', selectmode='browse')
tree.heading('#0',text='Magnet')
tree.column('#0',width=64,minwidth=58,stretch=False,anchor='center')
for col,label,width in zip(cols,('Título','Fontes','Tamanho','Publicação','Seeders'),(255,123,78,95,62)):
    tree.heading(col,text=label,command=lambda col=col: sort_heading(col))
    tree.column(col,width=width,minwidth=56,stretch=col=='title',anchor='w' if col in ('title','source') else 'center')
scroll = ttk.Scrollbar(listing, orient='vertical', command=tree.yview)
tree.configure(yscrollcommand=scroll.set)
scroll.pack(side='right',fill='y')
tree.pack(side='left',fill='both',expand=True)

details = ttk.Frame(workspace,style='Surface.TFrame',padding=14)
details.grid(row=0,column=1,sticky='nsew',padx=(14,0))
details.configure(width=270)
details.pack_propagate(False)
detail_title = tk.StringVar(value='Detalhes')
detail_meta = tk.StringVar(value='Selecione um resultado.')
ttk.Label(details,textvariable=detail_title,style='Detail.TLabel',wraplength=242).pack(anchor='w',pady=(0,8))
ttk.Label(details,textvariable=detail_meta,style='SurfaceMuted.TLabel',wraplength=242,justify='left').pack(anchor='w',pady=(0,12))
detail_actions = ttk.Frame(details,style='Surface.TFrame')
detail_actions.pack(fill='x')
detail_buttons = {}
for key,label,command in (
    ('magnet','Abrir magnet',lambda: open_link('magnet')), ('torrent','Abrir .torrent',lambda: open_link('torrent')),
    ('page','Abrir publicação',lambda: open_link('page')), ('favorite','Favoritar',lambda: favorite()),
):
    button = ttk.Button(detail_actions,text=label,command=command,style='Accent.TButton' if key=='magnet' else 'TButton')
    button.pack(fill='x',pady=(0,5))
    detail_buttons[key] = button

footer = ttk.Frame(root,style='Chrome.TFrame',padding=(16,6))
footer.pack(side='bottom',fill='x',before=main)
status_label = ttk.Label(footer,textvariable=status,style='Chrome.TLabel',wraplength=950)
status_label.pack(side='left',fill='x',expand=True)
manual = ttk.Frame(footer,style='Chrome.TFrame')
manual.pack(side='right')
for source in (ext_to,x1337):
    ttk.Button(manual,text=source.name,style='Nav.TButton',command=lambda p=source:open_source_search(p)).pack(side='left',padx=3)

rows = []
qqueue = queue.Queue()
searching = False
errors = []
refused = set()
browser_open = False
applied = Filters()
inferred_keys = set()
display_rows = []
active_view = 'Busca'
favorites_rows = []
details_visible = True
last_search_term = ''

def show():
    global display_rows
    previous = selected(quiet=True)
    y = tree.yview()[0]
    available = rows if active_view == 'Busca' else favorites_rows
    display_rows = [result for result in available if applied.matches(result)]
    order = sort.get()
    if order == 'Mais seeders':
        display_rows.sort(key=lambda item: item.seeders if item.seeders is not None else -1, reverse=True)
    elif order == 'Menor tamanho':
        display_rows.sort(key=lambda item: item.size if item.size is not None else float('inf'))
    elif order in ('Mais recentes','Mais antigos'):
        dated = [item for item in display_rows if publication(item,applied.source)]
        undated = [item for item in display_rows if not publication(item,applied.source)]
        dated.sort(key=lambda item: publication(item,applied.source), reverse=order=='Mais recentes')
        display_rows = dated + undated
    elif active_view=='Busca' and last_search_term:
        query_text = folded(last_search_term)
        tokens = query_text.split()
        def relevance(item):
            title = folded(item.title)
            hits = sum(token in title for token in tokens)
            return title == query_text, query_text in title, hits, item.seeders if item.seeders is not None else -1
        display_rows.sort(key=relevance,reverse=True)
    tree.delete(*tree.get_children())
    selected_id = None
    for index, result in enumerate(display_rows):
        iid = str(index)
        tree.insert('', 'end', iid=iid, image=magnet_image if valid_magnet(result.magnet) else '',
                    values=(result.title,result.source,size_label(result.size),date_label(publication(result,applied.source)),
                            result.seeders if result.seeders is not None else '—'))
        if result is previous:
            selected_id = iid
    if selected_id is not None:
        tree.selection_set(selected_id)
        tree.focus(selected_id)
        tree.yview_moveto(y)
    elif display_rows:
        tree.selection_set('0')
        tree.focus('0')
    count = len(display_rows)
    count_text.set(f'{count} resultado' if count==1 else f'{count} resultados')
    refresh_details()
    refresh_facets()


def size_label(size):
    if size is None:
        return '—'
    return (f'{size/GIB:.2f} GB' if size>=GIB else f'{size/1024**2:.0f} MB').replace('.',',')


def selected(*, quiet=False):
    s=tree.selection()
    if not s:
        if not quiet:
            messagebox.showinfo('Seleção','Selecione um resultado.',parent=root)
        return None
    return display_rows[int(s[0])]


def refresh_details():
    result = selected(quiet=True)
    detail_title.set(result.title if result else 'Detalhes')
    if result:
        meta = [
            f'Fontes: {result.source}',
            f'Publicação: {date_label(publication(result,applied.source))}',
            f'Ano do conteúdo: {result.release_year or "—"}',
            f'Tamanho: {size_label(result.size)}',
            f'Seeders: {result.seeders if result.seeders is not None else "—"}',
        ]
        extra = ' · '.join(filter(None,(result.category,result.language,result.quality,result_format(result))))
        if extra:
            meta.append(extra)
        detail_meta.set('\n\n'.join(meta))
    else:
        detail_meta.set('Selecione um resultado.')
    for key,button in detail_buttons.items():
        available = result and (key=='favorite' or (valid_magnet(result.magnet) if key=='magnet' else getattr(result,key)))
        button.state(['!disabled'] if available else ['disabled'])


def magnet_click(event):
    iid = tree.identify_row(event.y)
    if iid and tree.identify_column(event.x)=='#0':
        result = display_rows[int(iid)]
        if valid_magnet(result.magnet):
            open_link('magnet', result)
            return 'break'


def sort_heading(key):
    choices = {'published':'Mais antigos' if sort.get()=='Mais recentes' else 'Mais recentes',
               'size':'Menor tamanho','seeders':'Mais seeders','title':'Relevância','source':'Relevância'}
    sort.set(choices.get(key,'Relevância'))
    show()


def toggle_details():
    global details_visible
    details_visible = not details_visible
    if details_visible:
        details.grid()
    else:
        details.grid_remove()
    details_button.configure(text='Recolher detalhes' if details_visible else 'Mostrar detalhes')


def toggle_filters():
    if filter_panel.winfo_manager():
        filter_panel.pack_forget()
    else:
        filter_panel.pack(fill='x', pady=(8,0), before=chips)
        refresh_facets()


def refresh_facets():
    if not filter_panel.winfo_manager():
        return
    available = rows if active_view=='Busca' else favorites_rows
    for key, control in facets.items():
        counts = Counter()
        for result in available:
            if key == 'source':
                for source in result_sources(result):
                    if replace(applied,source=source).matches(result):
                        counts[source] += 1
            elif applied.matches(result,omit=key):
                counts.update(value for value in set(result_values(result,key)) if value)
        control.configure(values=('',*(f'{value}  ({counts[value]})' for value in sorted(counts,key=str.casefold))))


def sync_filter_form():
    period = next((label for label,code in PERIODS.items() if code==applied.period), f'Últimos {applied.period} dias')
    for key, variable in fields.items():
        value = period if key=='period' else getattr(applied,key)
        if key in ('from_date','to_date') and value:
            value = date_label(value)
        variable.set('' if value is None else value)
    include_undated.set(applied.unknown_dates)


def render_chips():
    for widget in chips.winfo_children():
        widget.destroy()
    entries = applied.chips()
    filter_button.configure(text=f'Filtros · {len(entries)}' if entries else 'Filtros ▾')
    for index,(key,label) in enumerate(entries):
        ttk.Button(chips,text=label+'  ×',style='Chip.TButton',command=lambda key=key:clear_filter(key)).grid(
            row=index//5,column=index%5,sticky='w',padx=(0,6),pady=(0,4))


def set_filters(value):
    global applied
    applied = value
    sync_filter_form()
    render_chips()
    show()


def quick_period(period):
    inferred_keys.difference_update(('period','from_date','to_date','unknown_dates'))
    set_filters(replace(applied,period=period,from_date='',to_date='',unknown_dates=False))


def clear_filter(key):
    if key == 'period':
        quick_period('')
        return
    inferred_keys.discard(key)
    set_filters(replace(applied,**{key:getattr(Filters(),key)}))


def clear_filters():
    inferred_keys.clear()
    set_filters(Filters())


def apply_filters():
    values = {key:variable.get().strip() for key,variable in fields.items()}
    for key in facets:
        values[key] = values[key].rsplit('  (',1)[0]
    label = values['period']
    values['period'] = PERIODS.get(label, applied.period if label==f'Últimos {applied.period} dias' else '')
    values['unknown_dates'] = include_undated.get()
    try:
        selected_filters = Filters.from_form(values)
    except ValueError as error:
        status.set(str(error))
        return
    inferred_keys.clear()
    set_filters(selected_filters)
    filter_panel.pack_forget()
    status.set('Filtros aplicados aos resultados.')


def set_view(view):
    global active_view
    active_view = view
    view_title.set(view)
    nav_search.configure(style='NavActive.TButton' if view=='Busca' else 'Nav.TButton')
    nav_favorites.configure(style='NavActive.TButton' if view=='Favoritos' else 'Nav.TButton')
    show()

def open_link(kind, result=None):
    r = result or selected()
    if not r: return
    link=getattr(r,kind)
    if not link: messagebox.showinfo('Indisponível','Esta fonte não forneceu esse tipo de link.'); return
    if kind=='magnet' and not valid_magnet(link): messagebox.showerror('Link inválido','Magnet inválido.',parent=root); return
    if kind in ('torrent', 'page') and not link.lower().startswith(('https://','http://')):
        messagebox.showerror('Link inválido', 'Endereço inválido.')
        return
    if kind == 'page':
        host = urlsplit(link).hostname
        for source in (ext_to, x1337):
            if host == urlsplit(source.base).hostname:
                open_embedded(link, source.name)
                return
    try:
        if kind == 'magnet' and os.name == 'nt':
            os.startfile(link)
        elif not webbrowser.open(link):
            messagebox.showerror('Falha ao abrir', 'Nenhum navegador foi encontrado.')
    except OSError:
        messagebox.showerror('Falha ao abrir', 'Confira se há um cliente BitTorrent associado a magnets.')

def open_source_search(source):
    term = query.get().strip()
    if not term:
        messagebox.showinfo('Busca no app', 'Digite o termo da busca.')
        return
    if smart.get():
        term = interpret(term, source_names())[0] or term
    open_embedded(source.search_url(term), source.name)

def embedded_search(url, *, automatic=False):
    executable = Path(__file__).resolve().parent / 'browser' / 'TorrentFindr.Browser.exe'
    if not executable.is_file():
        raise ValueError('O navegador integrado não está na pasta browser do torrentFindr.')
    options = ['--auto'] if automatic else []
    try:
        process = subprocess.run(
            [str(executable), *options, url, str(DATA / 'webview2')],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            encoding='utf-8', errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=155 if automatic else None,
        )
    except subprocess.TimeoutExpired:
        raise ValueError('O navegador não respondeu dentro do prazo.') from None
    failures = {
        5: 'A página não exibiu resultados que o app pudesse ler no prazo.',
        6: 'O site limitou as consultas. Tente novamente mais tarde.',
        7: 'A verificação do site ficou pendente. Você pode reabrir a busca integrada.',
    }
    if process.returncode:
        raise ValueError(failures.get(process.returncode, 'O navegador integrado não iniciou. Confira o WebView2 Runtime.'))
    if process.stdout:
        return read_browser_results(process.stdout)
    if automatic:
        raise ValueError('A janela da fonte foi fechada antes de concluir a consulta.')
    return []


def open_embedded(url, name):
    global browser_open
    if searching or browser_open:
        messagebox.showinfo('Busca no app', 'Aguarde a busca atual ou feche a janela de navegação.')
        return
    browser_open = True
    status.set(f'{name}: abrindo no navegador do torrentFindr…')

    def run():
        try:
            qqueue.put(('browser', name, embedded_search(url)))
        except (OSError, ValueError) as error:
            qqueue.put(('browser_error', name, str(error)))

    threading.Thread(target=run, daemon=True).start()


def append_imported(imported):
    global rows
    pages = {row.page: row for row in rows if row.page}
    new_rows = []
    updated = 0
    for row in imported:
        old = pages.get(row.page)
        if old is None:
            pages[row.page] = row
            new_rows.append(row)
        else:
            changed = False
            for field in ('magnet', 'torrent', 'infohash', 'published'):
                if not getattr(old, field) and getattr(row, field):
                    setattr(old, field, getattr(row, field))
                    changed = True
            updated += int(changed)
    total_before = len(rows)
    rows = dedup(rows + new_rows)
    show()
    added = len(rows) - total_before
    status.set(f'{imported[0].source}: {added} novos resultados, {updated} atualizados. Para itens sem link direto, use Abrir página.')

def favorite():
    r=selected()
    if r:
        item = asdict(r)
        if any(name in jackett_indexers for name in r.source.split(', ')):
            # URLs de download podem conter a chave do Jackett ou do tracker.
            item['torrent'] = ''
            item['magnet'] = ''
        key = item['infohash'] or item['page'] or (item['title'],item['source'])
        if any((other.get('infohash') or other.get('page') or (other.get('title'),other.get('source'))) == key
               for other in data['favorites']):
            status.set('Este resultado já está nos favoritos.')
            return
        data['favorites'].append(item)
        save()
        status.set('Resultado salvo nos favoritos.')
def favorites():
    global favorites_rows
    favorites_rows = [Result(**item) for item in data['favorites']]
    set_view('Favoritos')
    status.set('Favoritos salvos localmente.')
def history():
    w=tk.Toplevel(root)
    w.transient(root)
    w.title('Histórico')
    box=tk.Listbox(w,width=64,height=14,borderwidth=0,highlightthickness=0,font=('Segoe UI',10),
                   background=colors['paper'],foreground=colors['ink'],selectbackground=colors['selected'],
                   selectforeground=colors['ink'])
    box.pack(fill='both',expand=True,padx=10,pady=10)
    for h in reversed(data['history']): box.insert('end',h)
    def use(event):
        if box.curselection(): query.set(box.get(box.curselection()[0])); w.destroy(); search()
    box.bind('<Double-1>',use)
    box.bind('<Return>',use)


def appearance_panel():
    w = tk.Toplevel(root)
    w.title('Aparência')
    w.transient(root)
    w.resizable(False,False)
    panel = ttk.Frame(w,padding=16)
    panel.pack(fill='both',expand=True)
    ttk.Label(panel,text='Aparência',style='Heading.TLabel').pack(anchor='w',pady=(0,12))
    ttk.Label(panel,text='Esquema de cores').pack(anchor='w')
    schemes = ttk.Frame(panel)
    schemes.pack(fill='x',pady=(5,12))
    ttk.Label(panel,text='Cor de destaque').pack(anchor='w')
    accents = ttk.Frame(panel)
    accents.pack(fill='x',pady=(5,8))
    current = tk.StringVar()
    ttk.Label(panel,textvariable=current,style='Muted.TLabel').pack(anchor='w',pady=(0,10))
    scheme_buttons = {}
    accent_buttons = {}

    def paint():
        w.configure(background=colors['paper'])
        for name, button in scheme_buttons.items():
            button.configure(style='Chip.TButton' if name==theme else 'TButton')
        for value, button in accent_buttons.items():
            button.configure(style='Chip.TButton' if value==accent else 'TButton')
        current.set(f'{theme} · {accent.upper()}')

    def change(new_theme, new_accent):
        global theme, accent, colors, magnet_image
        theme, accent = new_theme, new_accent.lower()
        data['appearance'] = {'theme':theme,'accent':accent}
        colors = apply_style(root,theme,accent)
        magnet_image = magnet_icon(root,colors['accent'])
        save()
        paint()
        show()

    def choose_color():
        value = colorchooser.askcolor(color=accent,parent=w,title='Cor de destaque')[1]
        if valid_color(value):
            change(theme,value)

    for name in THEMES:
        button = ttk.Button(schemes,text=name,command=lambda name=name:change(name,DEFAULT_ACCENTS[name]))
        button.pack(side='left',padx=(0,6))
        scheme_buttons[name] = button
    for name,value in ACCENTS.items():
        button = ttk.Button(accents,text=name,command=lambda value=value:change(theme,value))
        button.pack(side='left',padx=(0,6))
        accent_buttons[value] = button
    actions = ttk.Frame(panel)
    actions.pack(fill='x')
    ttk.Button(actions,text='Cor personalizada',command=choose_color).pack(side='left')
    ttk.Button(actions,text='Fechar',command=w.destroy).pack(side='right')
    paint()
    w.bind('<Escape>',lambda _:w.destroy())

def config():
    global jackett_key
    w=tk.Toplevel(root); w.title('Fontes'); w.transient(root)
    w.configure(background=colors['paper'])
    ttk.Label(w,text='Ative apenas fontes e plugins em que confia.',padding=10).pack()
    vars={}
    names=[(p.name,p.name) for p in builtins]
    names += [(x.name,'plugin:'+x.name) for x in plugin_dir.glob('*.py')]
    for label,key in names:
        v=tk.BooleanVar(value=data['enabled'].get(key,not key.startswith('plugin:'))); vars[key]=v; ttk.Checkbutton(w,text=label,variable=v).pack(anchor='w',padx=12)
    ttk.Label(w, text='BitTorrented · acesso por convite').pack(anchor='w', padx=12, pady=4)
    tracker = ttk.LabelFrame(w, text='Trackers via Jackett local', padding=8)
    tracker.pack(fill='x', padx=12, pady=6)
    ttk.Label(tracker, text='Configure os indexadores autorizados no Jackett.').grid(row=0, columnspan=2, sticky='w')
    ttk.Label(tracker, text='Porta local').grid(row=1, column=0, sticky='w')
    port = tk.StringVar(value=str(data.get('jackett_port', 9117)))
    ttk.Entry(tracker, textvariable=port, width=8).grid(row=1, column=1, sticky='w')
    ttk.Label(tracker, text='Chave da API (só nesta sessão)').grid(row=2, column=0, sticky='w')
    api_key = tk.StringVar(value=jackett_key)
    ttk.Entry(tracker, textvariable=api_key, show='*', width=28).grid(row=2, column=1)
    tracker_flags = {}
    for row, name in enumerate(jackett_indexers, start=3):
        flag = tk.BooleanVar(value=data['enabled'].get(name, False))
        tracker_flags[name] = flag
        ttk.Checkbutton(tracker, text=f'Consultar {name}', variable=flag).grid(row=row, columnspan=2, sticky='w')
    def apply():
        global jackett_key
        try:
            number = int(port.get())
            if not 1 <= number <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror('Porta inválida', 'Digite uma porta entre 1 e 65535.', parent=w)
            return
        key = api_key.get().strip()
        if any(flag.get() for flag in tracker_flags.values()) and not key:
            messagebox.showerror('Chave ausente', 'Cole a chave da API mostrada no Jackett.', parent=w)
            return
        for k,v in vars.items(): data['enabled'][k]=v.get()
        data['jackett_port'] = number
        jackett_key = key
        data['enabled'].update({name: flag.get() for name, flag in tracker_flags.items()})
        save(); w.destroy()
        status.set('Fontes salvas. Alterações nos plugins entram em vigor ao reiniciar.')
    ttk.Button(w,text='Salvar',command=apply).pack(pady=10)

def source_names():
    return [source.name for source in providers] + list(jackett_indexers)


def search():
    global searching, inferred_keys, last_search_term
    raw = query.get().strip()
    if searching or browser_open or not raw:
        return
    term, understood = interpret(raw,source_names()) if smart.get() else (raw,{})
    if not term:
        status.set('Inclua um título ou uma palavra-chave além dos filtros.')
        return
    defaults = Filters()
    next_filters = replace(applied,**{key:getattr(defaults,key) for key in inferred_keys})
    if 'period' in understood:
        understood.update(from_date='',to_date='',unknown_dates=False)
    next_filters = replace(next_filters,**understood)
    try:
        next_filters.validate_size()
    except ValueError as error:
        status.set(str(error))
        return
    active=[p for p in providers if data['enabled'].get(p.name,True)]
    trackers = [name for name in jackett_indexers if data['enabled'].get(name, False)]
    tracker_missing_key = trackers and not jackett_key
    if jackett_key:
        port = data.get('jackett_port', 9117)
        active.extend(JackettSource(name, jackett_indexers[name], port, jackett_key) for name in trackers)
    if not active and tracker_missing_key:
        status.set('Informe a chave do Jackett em Fontes para consultar ' + ', '.join(trackers) + '.')
        return
    if not active: status.set('Nenhuma fonte ativa.'); return
    integrated = [source for source in (ext_to, x1337) if source in active]
    direct = [source for source in active if source not in integrated]
    searching = True
    last_search_term = term
    inferred_keys = set(understood)
    rows.clear()
    errors.clear()
    refused.clear()
    set_view('Busca')
    set_filters(next_filters)
    status.set(f'Buscando “{term}” em {len(active)} fonte(s)…')
    data['history'] = (data['history']+[raw])[-100:]
    save()
    if tracker_missing_key:
        errors.append(', '.join(trackers) + ': informe a chave do Jackett em Fontes.')
    def run_integrated():
        # Uma janela de verificação por vez, com o mesmo perfil do navegador integrado.
        for source in integrated:
            try:
                results = embedded_search(source.search_url(term), automatic=True)
                qqueue.put(('result', source.name, results))
            except (OSError, ValueError) as error:
                qqueue.put(('error', source.name, str(error)))

    def run():
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(6, len(direct)) + bool(integrated)) as pool:
            if integrated:
                pool.submit(run_integrated)
            futures={pool.submit(p.search,term):p.name for p in direct}
            for f in as_completed(futures):
                try: qqueue.put(('result',futures[f],f.result()))
                except SearchRefused: qqueue.put(('refused', futures[f], None))
                except Exception as e: qqueue.put(('error',futures[f],str(e)))
        qqueue.put(('done','',''))
    threading.Thread(target=run,daemon=True).start()

def poll():
    global searching,rows,browser_open
    try:
        while True:
            typ,name,value=qqueue.get_nowait()
            if typ == 'browser':
                browser_open = False
                if value:
                    append_imported(value)
                else:
                    status.set(f'{name}: janela fechada.')
            elif typ == 'browser_error':
                browser_open = False
                status.set(f'{name}: {value}')
            elif typ=='result': rows=dedup(rows+value); show(); status.set(f'{name}: concluído. {len(rows)} resultado(s).')
            elif typ=='refused':
                refused.add(name)
            elif typ=='error': errors.append(f'{name}: {value}'); status.set('Falhas: ' + ' | '.join(errors))
            else:
                searching = False
                summary = f'Busca encerrada · {len(rows)} resultado(s) recebidos.'
                if refused:
                    summary += f' Consulta recusada por {", ".join(sorted(refused))}.'
                if errors:
                    summary += ' Falhas: ' + ' | '.join(errors)
                status.set(summary)
    except queue.Empty: pass
    root.after(150,poll)
tree.bind('<<TreeviewSelect>>',lambda _:refresh_details())
tree.bind('<Button-1>',magnet_click)
tree.bind('<Alt-Return>',lambda _:open_link('magnet'))
entry.bind('<Return>',lambda _:search())
root.bind('<Control-k>',lambda _:entry.focus_set())
def resize_status(event):
    if event.widget is root:
        status_label.configure(wraplength=max(420,event.width-245))
root.bind('<Configure>',resize_status)
try:
    native_caption = install_chrome(root,(chrome,brand,caption,drag_area))
except (OSError, AttributeError):
    native_caption = False
if not native_caption:
    for button in (close_button,maximize_button,minimize_button):
        button.pack_forget()
else:
    for widget in (chrome,brand,caption,drag_area):
        widget.bind('<Double-Button-1>',lambda _:maximize_button.invoke())
refresh_details()
entry.focus_set()
root.after(100,poll)
if plugin_errors: messagebox.showwarning('Plugins','\n'.join(plugin_errors))
root.mainloop()
