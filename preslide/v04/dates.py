"""Pre-registered V0.4 date/time rules for GeoSphere narrative date texts.

Two separate questions are answered for each record:
  * Is the event DAY known?  (tier A: one explicit narrative day, consistent with the
    structured day and the provider's structured interval, no uncertainty wording)
  * Is a LOWER BOUND on the event TIME known?  (daypart or clock time stated as event time)

t0 is always a conservative lower bound of the event time: features may only use data
strictly before t0. Without a usable time statement t0 is local midnight of the event day.
Upper-bound statements ("vor 18:26", "spaetestens") and observation/alarm times never move
t0 later. Ambiguous or contradictory statements are excluded or kept as their own tier.
"""
import re
from datetime import date, datetime, timedelta

import pandas as pd

TZ = 'Europe/Vienna'
RULES_VERSION = 'v04-dates-1'
MONTHS = {'jaenner': 1, 'januar': 1, 'februar': 2, 'maerz': 3, 'april': 4, 'mai': 5, 'juni': 6, 'juli': 7,
          'august': 8, 'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12}
MONTH_ABBR = r'\b(jan|feb|maer|mrz|apr|jun|jul|aug|sep|sept|okt|nov|dez)\b\.?'
# Lower bound (local clock) of each daypart; the earliest mentioned daypart is used.
DAYPART_START = [(r'\bfrueh\b|morgen', 0), (r'nachmittag', 12), (r'vormittag', 6), (r'(?<!nach)(?<!vor)mittag', 11), (r'abend', 17)]
UPPER_DAYPART = re.compile(r'(spaetestens|vor|bis)\s*(dem|der|am|zum)?\s*$')
# Wording that makes the DAY uncertain or points to another day.
DAY_UNCERTAIN = re.compile(r'\boder\b|\bod\.|\bod\b|\bev\.|eventuell|wahrsch|vermut|\bwohl\b|\?|aelter|entweder|'
                           r'unsicher|unklar|bereits|weitere|erste risse|progressiv|vortag|tag davor|folgetag|'
                           r'vorher|davor|anfang|\bende\b|\bseit\b|\btage\b|woche|#')
# Clock times attached to these words are observation/alarm/weather times, not event times.
OBSERVATION = re.compile(r'alarm|einsatz|einsaetz|\bposts?\b|bekanntgabe|veroeffentlich|artikel|bemerkt|gesehen|'
                         r'sperre|regen|unwetter|gewitter|aufnahme|online')
TWO_DAY = re.compile(r'\b\d{1,2}\s*\.?\s*/\s*\d{1,2}\s*\.|nacht\s+vo[nm]\b|\bauf\s+(den\s+)?\d|zwischen\s+\d{1,2}\.\s*(und|\w+\s+\d{4}\s*\()')
NUM_DATE = re.compile(r'(?<![\d:])(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{4}|\d{2})(?!\d)')
NAME_DATE = re.compile(r'(?<![\d:])(\d{1,2})\s*\.\s*(' + '|'.join(MONTHS) + r')\s*\.?\s*(\d{4})(?!\d)')
ISO_DATE = re.compile(r'(\d{4})-(\d{2})-(\d{2})')
PARTIAL_DATE = re.compile(r'(?<![\d:.])(\d{1,2})\.(\d{1,2})\.(?!\s*\d)')
CLOCK = re.compile(r'(?<![\d.])(\d{1,2}):(\d{2})|(?<![\d:.])(\d{1,2})\s*(?=(?:-\s*\d{1,2}\s*)?(?:uhr|h)\b)')
UPPER_QUALIFIER = re.compile(r'(vor|bis|spaetestens|-|und)\s*(ca\.?\s*)?$')


def normalize(text):
    text = (text or '').strip().lower()
    for a, b in (('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss'), ('�', '#'), ('\t', ' ')):
        text = text.replace(a, b)
    return re.sub(r'\s+', ' ', text)


def _valid(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def date_mentions(text):
    """All explicit calendar days in the text, with consumed character spans."""
    found, spans = [], []
    for pattern, kind in ((NUM_DATE, 'num'), (NAME_DATE, 'name'), (ISO_DATE, 'iso')):
        for m in pattern.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in spans):
                continue
            if kind == 'iso':
                d = _valid(int(m[1]), int(m[2]), int(m[3]))
            else:
                year = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
                month = int(m[2]) if kind == 'num' else MONTHS[m[2]]
                d = _valid(year, month, int(m[1]))
            spans.append((m.start(), m.end()))
            found.append(d)
    rest = ''.join(' ' if any(s <= i < e for s, e in spans) else c for i, c in enumerate(text))
    partial = [(int(m[1]), int(m[2])) for m in PARTIAL_DATE.finditer(rest)]
    return found, partial, rest


def clock_lower_bounds(rest):
    """Clock times usable as lower bounds of the event time (hours, minutes)."""
    out = []
    for m in CLOCK.finditer(rest):
        hour = int(m[1] if m[1] is not None else m[3])
        minute = int(m[2]) if m[2] is not None else 0
        if hour > 23 or minute > 59:
            continue
        if UPPER_QUALIFIER.search(rest[max(0, m.start() - 16):m.start()].rstrip()):
            continue
        out.append((hour, minute))
    return out


def structured_interval(attributes):
    s, e = attributes.get('Date_Anfan'), attributes.get('Date_End_a')
    if s is None or e is None:
        return None, None
    return (pd.Timestamp(s, unit='ms', tz='UTC').tz_convert(TZ), pd.Timestamp(e, unit='ms', tz='UTC').tz_convert(TZ))


def classify_date(attributes):
    """Return the date tier, the event day, the conservative t0 and the time quality."""
    out = {'rules_version': RULES_VERSION, 'date_tier': 'excluded', 'event_day': None, 't0_local': None,
           'time_quality': None, 'date_reason': None}
    raw_day = attributes.get('Ereignisdatum_validFrom')
    day = _valid(*map(int, raw_day.split('-'))) if isinstance(raw_day, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw_day) else None
    if day is None:
        out['date_reason'] = 'no_structured_day'
        return out
    explicit = [attributes.get(k) for k in ('EREIGNIS_J', 'EREIGNIS_M', 'EREIGNIS_T')]
    if any(a is not None and a != b for a, b in zip(explicit, [day.year, day.month, day.day])):
        out['date_reason'] = 'conflicting_structured_fields'
        return out
    start, end = structured_interval(attributes)
    midnight = pd.Timestamp(datetime(day.year, day.month, day.day), tz=TZ)
    text = normalize(attributes.get('processTimeOrPeriodInfo'))
    if text in ('<null>', 'null'):
        text = ''
    days, partial, rest = date_mentions(text)
    if DAY_UNCERTAIN.search(text):
        out['date_reason'] = 'uncertain_wording'
        return out
    if TWO_DAY.search(text):
        first = min([d for d in days if d], default=None)
        out.update(date_tier='B_two_day_window', date_reason='two_day_window_not_primary',
                   event_day=(first or day).isoformat())
        return out
    if start is None or start < midnight or end > midnight + timedelta(days=1):
        out['date_reason'] = 'structured_interval_not_within_day' if start is not None else 'no_structured_interval'
        return out
    if not days and not partial:
        if re.search(MONTH_ABBR, text) or any(m in text for m in MONTHS):
            out['date_reason'] = 'month_level_text'
            return out
        out.update(date_tier='C_structured_day_only', date_reason='day_not_stated_in_narrative', event_day=day.isoformat())
        return out
    if None in days or len(set(days)) != 1 or days[0] != day or any((dd, mm) != (day.day, day.month) for dd, mm in partial):
        out['date_reason'] = 'narrative_day_missing_multiple_or_conflicting'
        return out
    # Tier A: the day is known. Now a conservative lower bound on the time of day.
    bounds = [('day', midnight)]
    if 'nacht' not in text:
        for pattern, hour in DAYPART_START:
            for m in re.finditer(pattern, text):
                if UPPER_DAYPART.search(text[max(0, m.start() - 16):m.start()].rstrip()):
                    continue   # 'spaetestens Abend' is an upper bound, not a start
                bounds.append(('daypart', midnight + timedelta(hours=hour)))
        if not OBSERVATION.search(text):
            for hour, minute in clock_lower_bounds(rest):
                bounds.append(('clock', midnight + timedelta(hours=hour, minutes=minute) - timedelta(hours=1)))
    elif not OBSERVATION.search(text):
        # 'nachts' with explicit clock times on the stated day: only the clock bound can be used.
        clocks = clock_lower_bounds(rest)
        if clocks:
            bounds += [('clock', midnight + timedelta(hours=h, minutes=m) - timedelta(hours=1)) for h, m in clocks]
    informative = [b for b in bounds if b[0] != 'day']
    if informative:
        kind, t0 = min(informative, key=lambda b: b[1])
        t0 = min(t0, start.floor('h'))       # never later than the provider's structured start
        t0 = max(t0.floor('h'), midnight)
        kind = kind if t0 > midnight else 'day'
    else:
        kind, t0 = 'day', midnight
    out.update(date_tier='A_narrative_day', date_reason='narrative_single_day', event_day=day.isoformat(),
               t0_local=t0.isoformat(), time_quality=kind)
    return out
