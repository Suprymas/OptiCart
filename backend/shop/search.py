import re
import unicodedata

from .models import Product


CATEGORY_OPTIONS = [
    ('', 'Visos kategorijos'),
    ('pieno-produktai', 'Pieno produktai'),
    ('kepiniai', 'Kepiniai'),
    ('kiausiniai', 'Kiaušiniai'),
    ('mesa', 'Mėsa'),
    ('vaisiai-darzoves', 'Vaisiai ir daržovės'),
    ('gerimai', 'Gėrimai'),
]


CATEGORY_KEYWORDS = {
    'pieno-produktai': ['pien', 'jogurt', 'sviest', 'grietin', 'varsk', 'suri', 'syr', 'kefyr'],
    'kepiniai': ['duon', 'baton', 'riestain', 'baget', 'bandel', 'keks', 'pyrag'],
    'kiausiniai': ['kiausin', 'kiaušin', 'kiaus'],
    'mesa': ['mesa', 'mėsa', 'vist', 'jaut', 'kiaul', 'kalakut', 'desr', 'dešr', 'kump'],
    'vaisiai-darzoves': ['obuol', 'banan', 'apelsin', 'citrin', 'vynuog', 'kriaus', 'uog', 'vais', 'darz', 'darž', 'pomidor', 'agurk', 'mork'],
    'gerimai': ['gerim', 'gėrim', 'vand', 'sult', 'cola', 'fanta', 'sprite', 'kava', 'arbata', 'arb'],
}


FILTER_UI_SCHEMA = {
    'pieno-produktai': [
        {
            'name': 'dairy_type',
            'label': 'Tipas',
            'options': [
                {'value': 'pienas', 'label': 'Pienas'},
                {'value': 'kefyras', 'label': 'Kefyras'},
                {'value': 'grietine', 'label': 'Grietinė'},
                {'value': 'jogurtas', 'label': 'Jogurtas'},
                {'value': 'sviestas', 'label': 'Sviestas'},
            ],
        },
        {
            'name': 'milk_fat',
            'label': 'Riebumas',
            'depends_on': {'name': 'dairy_type', 'value': 'pienas'},
            'options': [
                {'value': '2.5', 'label': '2,5%'},
                {'value': '3.5', 'label': '3,5%'},
            ],
        },
        {
            'name': 'milk_volume',
            'label': 'Kiekis',
            'depends_on': {'name': 'dairy_type', 'value': 'pienas'},
            'options': [
                {'value': '1l', 'label': '1L'},
                {'value': '2l', 'label': '2L'},
            ],
        },
    ],
    'kepiniai': [],
    'kiausiniai': [
        {
            'name': 'egg_size',
            'label': 'Dydis',
            'options': [
                {'value': 's', 'label': 'S'},
                {'value': 'm', 'label': 'M'},
                {'value': 'l', 'label': 'L'},
            ],
        },
    ],
    'mesa': [
        {
            'name': 'meat_type',
            'label': 'Tipas',
            'options': [
                {'value': 'vistiena', 'label': 'Vištiena'},
                {'value': 'kiauliena', 'label': 'Kiauliena'},
                {'value': 'jautiena', 'label': 'Jautiena'},
            ],
        },
    ],
    'vaisiai-darzoves': [
        {
            'name': 'produce_type',
            'label': 'Tipas',
            'options': [
                {'value': 'vaisiai', 'label': 'Vaisiai'},
                {'value': 'darzoves', 'label': 'Daržovės'},
            ],
        },
    ],
    'gerimai': [
        {
            'name': 'drink_type',
            'label': 'Tipas',
            'options': [
                {'value': 'vanduo', 'label': 'Vanduo'},
                {'value': 'gaivieji', 'label': 'Gaivieji gėrimai'},
                {'value': 'sultys', 'label': 'Sultys'},
                {'value': 'alkoholis', 'label': 'Alkoholis'},
            ],
        },
    ],
}


FILTER_KEYWORDS = {
    'pieno-produktai': {
        'dairy_type': {
            'pienas': ['pien'],
            'kefyras': ['kefyr'],
            'grietine': ['grietin'],
            'jogurtas': ['jogurt'],
            'sviestas': ['sviest'],
        },
        'milk_fat': {
            '2.5': ['2,5', '2.5'],
            '3.5': ['3,5', '3.5'],
        },
        'milk_volume': {
            '1l': ['1l', '1 l', '1000ml', '1000 ml'],
            '2l': ['2l', '2 l', '2000ml', '2000 ml'],
        },
    },
    'kiausiniai': {
        'egg_size': {
            's': [' s ', '(s', ' s)', 'dydis s'],
            'm': [' m ', '(m', ' m)', 'dydis m'],
            'l': [' l ', '(l', ' l)', 'dydis l'],
        },
    },
    'mesa': {
        'meat_type': {
            'vistiena': ['vist'],
            'kiauliena': ['kiaul'],
            'jautiena': ['jaut'],
        },
    },
    'vaisiai-darzoves': {
        'produce_type': {
            'vaisiai': ['vais', 'obuol', 'banan', 'apelsin', 'uog'],
            'darzoves': ['darz', 'darž', 'pomidor', 'agurk', 'mork'],
        },
    },
    'gerimai': {
        'drink_type': {
            'vanduo': ['vand'],
            'gaivieji': ['cola', 'fanta', 'sprite', 'gaiv'],
            'sultys': ['sult'],
            'alkoholis': ['alus', 'vyn', 'degt', 'sidr', 'alkoh'],
        },
    },
}


def get_selected_filters(query_params):
    """Extract known extra filter values from request params."""
    selected = {}
    for fields in FILTER_UI_SCHEMA.values():
        for field in fields:
            name = field['name']
            value = process_category(query_params.get(name, ''))
            if value:
                selected[name] = value
    return selected


def process_search_query(raw_query):
    """
    KAN-39: Paruošia paieškos užklausą apdorojimui.
    Pašalina tarpus ir konvertuoja į mažąsias raides.
    """
    return raw_query.strip().lower()


def process_category(raw_category):
    """Normalize selected category from request params."""
    return (raw_category or '').strip().lower()


def _normalize_text(value):
    text = process_search_query(value)
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(char for char in text if not unicodedata.combining(char))
    text = text.replace(',', '.')
    text = re.sub(r'[^a-z0-9.% ]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _product_text(product):
    return _normalize_text(f"{getattr(product, 'name', '')} {getattr(product, 'description', '')}")


def _keyword_match(text, keywords):
    return any(_normalize_text(keyword) in text for keyword in keywords)


def _infer_category(text):
    for category, keywords in CATEGORY_KEYWORDS.items():
        if _keyword_match(text, keywords):
            return category
    return None


def _parse_amount(text):
    match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\b', text)
    if not match:
        return None

    amount = match.group(1).rstrip('0').rstrip('.') if '.' in match.group(1) else match.group(1)
    unit = match.group(2)
    return f'{amount}{unit}'


def _extract_product_signature(product):
    text = _product_text(product)
    signature = {
        'text': text,
        'category': _infer_category(text),
        'dairy_type': None,
        'milk_fat': None,
        'milk_volume': None,
        'egg_size': None,
        'meat_type': None,
        'produce_type': None,
        'drink_type': None,
    }

    if signature['category'] == 'pieno-produktai':
        type_match = re.search(r'\btipas\s+(pienas|kefyras|grietine|jogurtas|sviestas)\b', text)
        if type_match:
            signature['dairy_type'] = type_match.group(1)
        elif 'sviestas' in text or 'sviest' in text:
            signature['dairy_type'] = 'sviestas'
        elif 'kefyras' in text or 'kefyr' in text:
            signature['dairy_type'] = 'kefyras'
        elif 'grietine' in text or 'grietin' in text:
            signature['dairy_type'] = 'grietine'
        elif 'jogurtas' in text or 'jogurt' in text:
            signature['dairy_type'] = 'jogurtas'
        elif 'pienas' in text:
            signature['dairy_type'] = 'pienas'

        fat_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
        if fat_match:
            signature['milk_fat'] = fat_match.group(1)

        amount = _parse_amount(text)
        if amount and amount.endswith('l'):
            signature['milk_volume'] = amount

    elif signature['category'] == 'kiausiniai':
        for egg_size in ('s', 'm', 'l'):
            if f'dydis {egg_size}' in text or f'({egg_size})' in text or f' {egg_size} ' in text:
                signature['egg_size'] = egg_size
                break

    elif signature['category'] == 'mesa':
        if 'vist' in text:
            signature['meat_type'] = 'vistiena'
        elif 'kiaul' in text:
            signature['meat_type'] = 'kiauliena'
        elif 'jaut' in text:
            signature['meat_type'] = 'jautiena'

    elif signature['category'] == 'vaisiai-darzoves':
        if (
            'grupe darzoves' in text
            or 'tipas darzoves' in text
            or 'grupe darzove' in text
            or 'tipas darzove' in text
        ):
            signature['produce_type'] = 'darzoves'
        elif 'grupe vaisiai' in text or 'tipas vaisiai' in text:
            signature['produce_type'] = 'vaisiai'
        elif any(keyword in text for keyword in ('agurk', 'mork', 'pomidor')):
            signature['produce_type'] = 'darzoves'
        elif any(keyword in text for keyword in ('banan', 'obuol', 'apelsin', 'citrin', 'vynuog', 'kriaus', 'uog')):
            signature['produce_type'] = 'vaisiai'

    elif signature['category'] == 'gerimai':
        if 'vand' in text:
            signature['drink_type'] = 'vanduo'
        elif any(keyword in text for keyword in ('cola', 'fanta', 'sprite', 'gaiv')):
            signature['drink_type'] = 'gaivieji'
        elif 'sult' in text:
            signature['drink_type'] = 'sultys'
        elif any(keyword in text for keyword in ('alus', 'vyn', 'degt', 'sidr', 'alkoh')):
            signature['drink_type'] = 'alkoholis'

    return signature


def _matches_query(product, query):
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return False

    text = _product_text(product)
    return all(token in text for token in normalized_query.split())


def _matches_category(signature, category):
    if not category:
        return True
    return signature['category'] == category


def _matches_selected_filters(signature, category, selected_filters):
    if not category:
        return True

    category_filter_map = FILTER_KEYWORDS.get(category, {})
    for field_name, value_map in category_filter_map.items():
        selected_value = process_category(selected_filters.get(field_name, ''))
        if not selected_value:
            continue
        if selected_value not in value_map:
            continue

        if signature.get(field_name) != selected_value:
            return False

    return True


def _infer_category_from_filters(selected_filters):
    if not selected_filters:
        return ''

    for category, fields in FILTER_UI_SCHEMA.items():
        field_names = {field['name'] for field in fields}
        if any(process_category(selected_filters.get(field_name, '')) for field_name in field_names):
            return category

    return ''


def _iter_matching_products(query, category, selected_filters):
    direct_matches = list(Product.objects.filter(name__icontains=query))
    candidates = direct_matches or list(Product.objects.all())

    matched = []
    for product in candidates:
        if query and not _matches_query(product, query):
            continue

        signature = _extract_product_signature(product)
        if not _matches_category(signature, category):
            continue

        if not _matches_selected_filters(signature, category, selected_filters):
            continue

        matched.append(product)

    return matched


def search_products(raw_query, raw_category='', selected_filters=None):
    """
    KAN-37: Vykdo paiešką ir grąžina rezultatus.
    Jei užklausa tuščia – grąžina tuščią QuerySet.
    """
    query = process_search_query(raw_query)
    category = process_category(raw_category)
    selected_filters = selected_filters or {}
    effective_category = category or _infer_category_from_filters(selected_filters)

    if not query and not effective_category and not selected_filters:
        return Product.objects.none()

    if query:
        base_qs = Product.objects.filter(name__icontains=query)
        if not effective_category or effective_category not in CATEGORY_KEYWORDS:
            if not selected_filters:
                if hasattr(base_qs, 'exists'):
                    if base_qs.exists():
                        return base_qs
                elif base_qs:
                    return base_qs

        matched_products = _iter_matching_products(query, effective_category, selected_filters)
    else:
        matched_products = _iter_matching_products('', effective_category, selected_filters)

    if not matched_products:
        return Product.objects.none()

    return Product.objects.filter(pk__in=[product.pk for product in matched_products]).order_by('name', 'store', 'id')


def has_search_results(results):
    """
    KAN-37: Patikrina ar paieška grąžino bent vieną rezultatą.
    """
    if hasattr(results, 'exists'):
        return results.exists()
    return bool(results)
