import os
import re
import tkinter as tk
from tkinter import ttk


THEMES = ('Sistema', 'Papel', 'Grafite', 'Meia-noite')
ACCENTS = {
    'Azul':'#0059ff', 'Violeta':'#8253d6', 'Verde':'#218869',
    'Âmbar':'#b46c12', 'Rosa':'#c34d78', 'Ciano':'#168394',
}
DEFAULT_ACCENTS = {
    'Sistema':ACCENTS['Azul'], 'Papel':ACCENTS['Âmbar'],
    'Grafite':ACCENTS['Azul'], 'Meia-noite':ACCENTS['Ciano'],
}

PALETTES = {
    'Papel': ('#fffdf8','#f1ede5','#f3efe7','#e9e1d6','#26211d','#65594c'),
    'Grafite': ('#212226','#191a1d','#2c2e33','#383b41','#f1f1f2','#b2b3bc'),
    'Meia-noite': ('#172237','#101827','#202f49','#293c5b','#f0f5ff','#adbcd4'),
    'Sistema claro': ('#ffffff','#edf2f7','#eef3fa','#e2eaf5','#17202b','#505e6c'),
}


def valid_color(value):
    return isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value) is not None


def system_dark():
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
                return not bool(winreg.QueryValueEx(key, 'AppsUseLightTheme')[0])
        except OSError:
            pass
    return True


def mix(color, background, amount):
    rgb = [
        round(int(color[i:i+2],16)*amount + int(background[i:i+2],16)*(1-amount))
        for i in (1,3,5)
    ]
    return '#' + ''.join(f'{value:02x}' for value in rgb)


def luminance(color):
    channels = [int(color[i:i+2],16)/255 for i in (1,3,5)]
    return sum(
        weight * (part/12.92 if part <= .04045 else ((part+.055)/1.055)**2.4)
        for part,weight in zip(channels, (.2126,.7152,.0722))
    )


def palette(theme, accent):
    if theme == 'Sistema':
        theme = 'Grafite' if system_dark() else 'Sistema claro'
    paper, base, surface, hover, ink, muted = PALETTES.get(theme, PALETTES['Grafite'])
    dark = luminance(paper) < .18
    accent = accent if valid_color(accent) else ACCENTS['Azul']
    display = accent
    for _ in range(20):
        if (dark and luminance(display) >= .55) or (not dark and luminance(display) <= .10):
            break
        display = mix(display, '#ffffff' if dark else '#000000', .85)
    return {
        'paper':paper, 'base':base, 'surface':surface, 'hover':hover,
        'ink':ink, 'muted':muted, 'accent':display, 'on_accent':'#10131b' if dark else '#ffffff',
        'selected':mix(display,paper,.18), 'selected_hover':mix(display,paper,.28),
        'warn':'#ffd394' if dark else '#784500', 'warn_bg':'#352b20' if dark else '#fff1da',
    }


def apply_style(root, theme, accent):
    colors = palette(theme, accent)
    paper, base, surface, hover, ink = (colors[key] for key in ('paper','base','surface','hover','ink'))
    muted, emphasis = colors['muted'], colors['accent']
    style = ttk.Style(root)
    if style.theme_use() != 'clam':
        style.theme_use('clam')
    root.configure(background=paper)
    root.option_add('*TCombobox*Listbox.background', surface)
    root.option_add('*TCombobox*Listbox.foreground', ink)
    root.option_add('*TCombobox*Listbox.selectBackground', colors['selected'])
    root.option_add('*TCombobox*Listbox.selectForeground', ink)
    font = ('Segoe UI', 10)
    style.configure('.', background=paper, foreground=ink, font=font, borderwidth=0,
                    bordercolor=paper, lightcolor=paper, darkcolor=paper, focuscolor=emphasis)
    for name, background in (('TFrame',paper),('Chrome.TFrame',base),('Surface.TFrame',surface),('Warn.TFrame',colors['warn_bg'])):
        style.configure(name, background=background)
    for name, background, foreground, text_font in (
        ('TLabel',paper,ink,font), ('Muted.TLabel',paper,muted,('Segoe UI',9)),
        ('Heading.TLabel',paper,ink,('Segoe UI Semibold',21)),
        ('Chrome.TLabel',base,ink,('Segoe UI Semibold',11)),
        ('Brand.TLabel',base,emphasis,('Segoe UI Semibold',14)),
        ('Surface.TLabel',surface,ink,font), ('SurfaceMuted.TLabel',surface,muted,('Segoe UI',9)),
        ('Detail.TLabel',surface,ink,('Segoe UI Semibold',15)),
        ('Warn.TLabel',colors['warn_bg'],colors['warn'],font),
    ):
        style.configure(name,background=background,foreground=foreground,font=text_font)
    for name, background, foreground, active in (
        ('TButton',surface,ink,hover), ('Nav.TButton',base,ink,hover),
        ('NavActive.TButton',colors['selected'],emphasis,colors['selected_hover']),
        ('Accent.TButton',emphasis,colors['on_accent'],emphasis),
        ('Chip.TButton',colors['selected'],emphasis,colors['selected_hover']),
        ('Caption.TButton',base,muted,hover), ('Close.TButton',base,muted,'#a62b35'),
    ):
        style.configure(name, background=background, foreground=foreground, borderwidth=0,
                        lightcolor=background,darkcolor=background,bordercolor=background,
                        padding=(11,6), anchor='center')
        style.map(name, background=[('pressed',active),('active',active)],
                  foreground=[('disabled',muted),('active','#ffffff' if name=='Close.TButton' else foreground)],
                  lightcolor=[('active',active)],darkcolor=[('active',active)],bordercolor=[('active',active)])
    for name in ('Caption.TButton','Close.TButton'):
        style.configure(name, font=('Segoe UI Symbol',12), padding=(7,3))
    style.configure('TEntry', fieldbackground=surface, foreground=ink, insertcolor=ink, padding=(9,6),
                    bordercolor=surface, lightcolor=surface, darkcolor=surface)
    style.configure('TCombobox', fieldbackground=surface, foreground=ink, background=surface, arrowcolor=muted,
                    padding=(8,5), bordercolor=surface, lightcolor=surface, darkcolor=surface)
    for name in ('TCombobox','TEntry'):
        style.map(name, fieldbackground=[('readonly',surface),('disabled',paper)],
                  foreground=[('disabled',muted),('readonly',ink)], bordercolor=[('focus',emphasis)])
    style.configure('TCheckbutton', background=paper, foreground=ink, indicatorbackground=surface, indicatorcolor=emphasis)
    style.map('TCheckbutton', background=[('active',paper)], indicatorbackground=[('selected',emphasis)])
    style.configure('TLabelframe',background=paper,borderwidth=0)
    style.configure('TLabelframe.Label',background=paper,foreground=emphasis,font=('Segoe UI Semibold',10))
    style.configure('Treeview',background=paper,fieldbackground=paper,foreground=ink,
                    rowheight=35,relief='flat',font=font,borderwidth=0)
    style.map('Treeview',background=[('selected',colors['selected'])],foreground=[('selected',ink)])
    style.configure('Treeview.Heading',background=surface,foreground=muted,
                    font=('Segoe UI Semibold',9),padding=(8,7),relief='flat',borderwidth=0,
                    lightcolor=surface,darkcolor=surface,bordercolor=surface)
    style.map('Treeview.Heading', background=[('active',hover)], relief=[('active','flat')])
    style.configure('Vertical.TScrollbar',background=surface,troughcolor=paper,arrowcolor=muted,
                    bordercolor=paper,lightcolor=surface,darkcolor=surface)
    return colors


def magnet_icon(root, accent):
    image = tk.PhotoImage(master=root, width=19, height=19)
    for y in range(2, 17):
        for x in range(2, 17):
            dist = (x-9)**2 + (y-9)**2
            arc = y >= 9 and 16 <= dist <= 51
            leg = y < 9 and (2 <= x <= 5 or 13 <= x <= 16)
            if arc or leg:
                image.put(accent, (x,y))
    return image
