"""Filtros locais e leitura de critérios escritos no campo de busca."""

from dataclasses import dataclass
from datetime import date, timedelta
import math
import re
import unicodedata


PERIODS = {
    'Qualquer data': '', 'Hoje': '1', 'Últimos 7 dias': '7',
    'Últimos 30 dias': '30', 'Últimos 90 dias': '90', 'Intervalo': 'custom',
}
ORDERS = ('Relevância', 'Mais recentes', 'Mais antigos', 'Mais seeders', 'Menor tamanho')
GIB = 1024**3


def folded(value):
    return ''.join(
        char for char in unicodedata.normalize('NFKD', str(value).casefold())
        if not unicodedata.combining(char)
    )


def result_format(row):
    if row.file_format:
        return row.file_format.upper()
    match = re.search(r'(?i)\b(iso|pdf|epub|mkv|mp4|avi|flac|mp3|zip|7z|rar)\b', row.title)
    return match[0].upper() if match else ''


def normalized_quality(value):
    value = value.strip().lower()
    return '2160p' if value in ('4k', 'uhd') else value


def languages(value):
    aliases = {
        'en':'Inglês', 'eng':'Inglês', 'english':'Inglês', 'ingles':'Inglês',
        'pt':'Português', 'por':'Português', 'pt-br':'Português', 'portuguese':'Português', 'portugues':'Português',
        'es':'Espanhol', 'spa':'Espanhol', 'spanish':'Espanhol', 'espanhol':'Espanhol',
        'ja':'Japonês', 'jpn':'Japonês', 'japanese':'Japonês', 'japones':'Japonês',
        'ru':'Russo', 'rus':'Russo', 'russian':'Russo',
    }
    return tuple(
        aliases.get(folded(part), part.strip())
        for part in re.split(r'[,;/]', value) if part.strip()
    )


def result_sources(row):
    return tuple(source.strip() for source in row.source.split(',') if source.strip())


def publication(row, source=''):
    if source and row.source_dates:
        return row.source_dates.get(source, '')
    if source and source not in result_sources(row):
        return ''
    if row.published:
        return row.published
    return max(row.source_dates.values(), default='')


def date_label(value):
    if not value:
        return '—'
    try:
        return date.fromisoformat(value).strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return '—'


def link_types(row):
    return tuple(label for label, key in (('Magnet','magnet'), ('.torrent','torrent'), ('Publicação','page')) if getattr(row,key))


def result_values(row, key):
    if key == 'source':
        return result_sources(row)
    if key == 'language':
        return languages(row.language)
    if key == 'format':
        return (result_format(row),)
    if key == 'quality':
        return (normalized_quality(row.quality),)
    if key == 'link':
        return link_types(row)
    return (getattr(row, key),)


def iso_input(raw):
    if not raw:
        return ''
    if '/' in raw:
        day, month, year = map(int, raw.split('/'))
        return date(year, month, day).isoformat()
    return date.fromisoformat(raw).isoformat()


@dataclass(frozen=True)
class Filters:
    period: str = ''
    from_date: str = ''
    to_date: str = ''
    source: str = ''
    year: int | None = None
    category: str = ''
    language: str = ''
    quality: str = ''
    format: str = ''
    min_seeds: int | None = None
    min_gb: float | None = None
    max_gb: float | None = None
    link: str = ''
    unknown_dates: bool = False

    @classmethod
    def from_form(cls, values):
        fields = dict(values)
        for key in ('year', 'min_seeds', 'min_gb', 'max_gb'):
            raw = fields[key].strip().replace(',', '.')
            try:
                fields[key] = (int(raw) if key in ('year', 'min_seeds') else float(raw)) if raw else None
            except ValueError:
                raise ValueError('Confira os campos numéricos de ano, tamanho e seeders.') from None
            number = fields[key]
            if number is not None and (not math.isfinite(number) or number < 0):
                raise ValueError('Use números positivos ou zero.')
        if fields['year'] is not None and not 1900 <= fields['year'] <= date.today().year + 1:
            raise ValueError('Informe um ano de conteúdo válido.')
        if fields['period'] == 'custom':
            try:
                start, end = (iso_input(fields[key].strip()) for key in ('from_date', 'to_date'))
            except ValueError:
                raise ValueError('Use DD/MM/AAAA nos campos de data.') from None
            if not (start or end) or (start and end and start > end):
                raise ValueError('Informe um intervalo de publicação válido.')
            fields['from_date'], fields['to_date'] = start, end
        else:
            fields['from_date'] = fields['to_date'] = ''
        result = cls(**fields)
        result.validate_size()
        return result

    def validate_size(self):
        if self.min_gb is not None and self.max_gb is not None and self.min_gb > self.max_gb:
            raise ValueError('O tamanho mínimo precisa ser menor ou igual ao máximo.')

    def matches(self, row, *, omit='', today=None):
        for key in ('source', 'category', 'language', 'quality', 'format', 'link'):
            expected = getattr(self, key)
            if key != omit and expected:
                expected = normalized_quality(expected) if key == 'quality' else expected
                if not any(folded(expected) == folded(value) for value in result_values(row, key)):
                    return False
        if self.year is not None and row.release_year != self.year:
            return False
        if self.min_seeds is not None and (row.seeders is None or row.seeders < self.min_seeds):
            return False
        if self.min_gb is not None and (row.size is None or row.size < self.min_gb * GIB):
            return False
        if self.max_gb is not None and (row.size is None or row.size > self.max_gb * GIB):
            return False
        if not self.period:
            return True
        start, end = self.from_date, self.to_date
        if self.period.isdigit():
            today = today or date.today()
            start, end = (today - timedelta(days=int(self.period)-1)).isoformat(), today.isoformat()
        published = publication(row, '' if omit == 'source' else self.source)
        return (not start or published >= start) and (not end or published <= end) if published else self.unknown_dates

    def chips(self):
        values = {
            'source':self.source, 'category':self.category, 'language':self.language,
            'quality':self.quality, 'format':self.format, 'link':self.link,
            'year':f'Ano {self.year}' if self.year else '',
            'min_seeds':f'≥ {self.min_seeds} seeders' if self.min_seeds is not None else '',
            'min_gb':f'≥ {self.min_gb:g} GB' if self.min_gb is not None else '',
            'max_gb':f'≤ {self.max_gb:g} GB' if self.max_gb is not None else '',
            'unknown_dates':'Inclui sem data' if self.period and self.unknown_dates else '',
        }
        if self.period == 'custom':
            if self.from_date and self.to_date:
                label = f'{date_label(self.from_date)} a {date_label(self.to_date)}'
            else:
                label = f'Desde {date_label(self.from_date)}' if self.from_date else f'Até {date_label(self.to_date)}'
        else:
            label = next((name for name, code in PERIODS.items() if code == self.period and code), '')
            if not label and self.period.isdigit():
                label = f'Últimos {self.period} dias'
        return [(key, value) for key, value in {'period':label, **values}.items() if value]


def interpret(query, source_names=()):
    """Extrai só padrões explícitos. O restante continua sendo o termo da fonte."""
    parsed = {}
    remainder = query

    def take(pattern, key, convert):
        nonlocal remainder
        def replace(match):
            value = convert(*match.groups())
            if value is None:
                return match[0]
            parsed[key] = value
            return ' '
        remainder = re.sub(pattern, replace, remainder, count=1, flags=re.I)

    take(r'(?:\bnos?\s+)?[úu]ltim[oa]s?\s+(\d{1,4})\s+dias?\b', 'period', lambda n: str(int(n)) if int(n) else None)
    take(r'\b(?:publicad[oa]s?\s+)?(hoje)\b', 'period', lambda _: '1')
    take(r'\b(?:at[eé]|no m[aá]ximo|menor que)\s*(\d+(?:[.,]\d+)?)\s*(gb|mb)\b', 'max_gb',
         lambda size,unit: float(size.replace(',','.')) / (1024 if unit.lower() == 'mb' else 1))
    take(r'\b(?:a partir de|no m[ií]nimo|maior que)\s*(\d+(?:[.,]\d+)?)\s*(gb|mb)\b', 'min_gb',
         lambda size,unit: float(size.replace(',','.')) / (1024 if unit.lower() == 'mb' else 1))
    take(r'\b(?:com\s+)?(?:(?:pelo menos|m[ií]nimo de|no m[ií]nimo)\s+)?(\d+)\s+seeders?\b', 'min_seeds', int)
    take(r'(?<![\w.])(480p|720p|1080p|2160p|4k)(?!\w)', 'quality', normalized_quality)
    take(r'(?<![\w.])(iso|pdf|epub|mkv|mp4|avi|flac|mp3)(?!\w)', 'format', str.upper)
    take(r'\bem\s+(portugu[eê]s|ingl[eê]s|espanhol|japon[eê]s|russo)\b', 'language', lambda raw: languages(raw)[0])
    take(r'\bano\s+(19\d{2}|20\d{2})\b', 'year', int)
    if source_names:
        names = sorted(source_names, key=len, reverse=True)
        take(r'\b(?:no|na|via)\s+(' + '|'.join(map(re.escape, names)) + r')(?![\w.])',
             'source', lambda value: next((name for name in names if name.casefold() == value.casefold()), None))
    return ' '.join(remainder.split()).strip(' ,;'), parsed
