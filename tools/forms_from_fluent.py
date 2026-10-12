#!/usr/bin/env python3
"""
Normalise a Fluent Forms export (JSON) into src/forms.json, keyed by the
original Fluent form id so `{{form:11}}` tokens in extracted content resolve.

    python tools/forms_from_fluent.py path/to/fluentform-export.json 11 12 13 14 15 16
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'src' / 'forms.json'


def text(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s or '')).strip()


def rules(settings):
    r = (settings or {}).get('validation_rules') or {}
    return bool((r.get('required') or {}).get('value'))


def normalise_field(f):
    el = f.get('element')
    a, s = f.get('attributes') or {}, f.get('settings') or {}
    base = {'name': a.get('name'), 'label': text(s.get('label')), 'required': rules(s),
            'placeholder': a.get('placeholder') or s.get('placeholder') or ''}
    if el == 'input_name':
        out = []
        for key, sub in (f.get('fields') or {}).items():
            if (sub.get('settings') or {}).get('visible', True):
                ss, sa = sub.get('settings') or {}, sub.get('attributes') or {}
                out.append({'type': 'text', 'name': f'{a.get("name","names")}_{key}', 'label': text(ss.get('label')),
                            'required': rules(ss), 'placeholder': sa.get('placeholder') or ''})
        return out
    if el == 'input_email':
        return [{**base, 'type': 'email'}]
    if el == 'input_text':
        return [{**base, 'type': 'text'}]
    if el == 'input_number':
        lab = base['label'].lower()
        kind = 'tel' if re.search(r'phone|whatsapp|tel[eé]fono|m[oó]vil', lab) else 'number'
        return [{**base, 'type': kind, 'min': s.get('validation_rules', {}).get('min', {}).get('value') or a.get('min'),
                 'max': s.get('validation_rules', {}).get('max', {}).get('value') or a.get('max')}]
    if el == 'input_hidden':
        return [{'type': 'hidden', 'name': a.get('name'), 'value': a.get('value') or ''}]
    if el == 'input_date':
        return [{**base, 'type': 'date'}]
    if el == 'textarea':
        return [{**base, 'type': 'textarea'}]
    if el == 'select':
        opts = [{'label': text(o.get('label')), 'value': o.get('value')} for o in s.get('advanced_options', [])]
        return [{**base, 'type': 'select', 'options': opts}]
    if el in ('input_checkbox', 'input_radio'):
        opts = [{'label': text(o.get('label')), 'value': o.get('value')} for o in s.get('advanced_options', [])]
        return [{**base, 'type': 'checkbox', 'options': opts}]
    if el == 'terms_and_condition':
        return [{**base, 'type': 'checkbox', 'options': [{'label': text(s.get('tnc_html')), 'value': 'yes'}]}]
    return [{'type': 'unsupported', 'element': el, 'name': a.get('name')}]


# Readable field names so notification emails make sense (Fluent's are numeric_field_1 etc.)
RENAME = {'names_first_name': 'first_name', 'names_last_name': 'last_name', 'numeric_field': 'phone',
          'numeric_field_1': 'guests', 'hidden': 'experience', 'datetime': 'preferred_date',
          'dropdown': 'heard_from', 'description': 'message', 'checkbox': 'health_confirmation'}

# Light copy fixes (typos / accents / the date format hint, now that the date picker is native)
COPY_FIXES = {'Air B&B Experiences': 'Airbnb Experiences', 'Numero de Personas': 'Número de personas',
              'Como nos conociste?': '¿Cómo nos conociste?', 'Preferred Date (dd/mm/yyyy)': 'Preferred date',
              'Fecha Preferida (dd/mm/yyyy)': 'Fecha preferida', '- Select -': 'Select', '- Selecciona -': 'Selecciona',
              'Correo': 'Correo electrónico', 'Correo Electrónico': 'Correo electrónico', 'de un amigo': 'Por un amigo'}


def fix(v):
    if isinstance(v, str):
        return COPY_FIXES.get(v, v)
    if isinstance(v, list):
        return [fix(x) for x in v]
    if isinstance(v, dict):
        return {k: (RENAME.get(x, x) if k == 'name' and isinstance(x, str) else fix(x)) for k, x in v.items()}
    return v


def main():
    src, ids = sys.argv[1], set(sys.argv[2:])
    data = json.load(open(src, encoding='utf-8'))
    forms = json.load(open(OUT)) if OUT.exists() else {}
    for f in data:
        if str(f['id']) not in ids:
            continue
        ff = json.loads(f['form_fields']) if isinstance(f['form_fields'], str) else f['form_fields']
        fields = []
        for fld in ff.get('fields', []):
            fields += normalise_field(fld)
        fields = fix(fields)
        meta = {m['meta_key']: m['value'] for m in f.get('metas', [])}
        fs = json.loads(meta.get('formSettings', '{}'))
        btn = (ff.get('submitButton') or {}).get('settings', {}).get('button_ui', {}).get('text') or 'Send'
        forms[str(f['id'])] = {'title': f['title'], 'button': btn,
                               'success': text(fs.get('confirmation', {}).get('messageToShow')),
                               'redirect': fs.get('confirmation', {}).get('customUrl') or '',
                               'fields': fields}
        print(f['id'], f['title'], '->', [x.get('name') or x.get('type') for x in fields])
    OUT.write_text(json.dumps(forms, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
