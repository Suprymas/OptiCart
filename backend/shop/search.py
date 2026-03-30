from django.db.models import Q

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
    'kepiniai': [
        {
            'name': 'bakery_type',
            'label': 'Tipas',
            'options': [
                {'value': 'duona', 'label': 'Duona'},
                {'value': 'batonas', 'label': 'Batonas'},
            ],
        },
    ],
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
    'kepiniai': {
        'bakery_type': {
            'duona': ['duon'],
            'batonas': ['baton'],
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


def _filter_by_keywords(queryset, keywords):
    query = Q()
    for keyword in keywords:
        query |= Q(name__icontains=keyword)
    return queryset.filter(query)


def process_search_query(raw_query):
    """
    KAN-39: Paruošia paieškos užklausą apdorojimui.
    Pašalina tarpus ir konvertuoja į mažąsias raides.
    """
    return raw_query.strip().lower()


def process_category(raw_category):
    """Normalize selected category from request params."""
    return (raw_category or '').strip().lower()


def search_products(raw_query, raw_category='', selected_filters=None):
    """
    KAN-37: Vykdo paiešką ir grąžina rezultatus.
    Jei užklausa tuščia – grąžina tuščią QuerySet.
    """
    query = process_search_query(raw_query)
    category = process_category(raw_category)
    selected_filters = selected_filters or {}

    if not query:
        return Product.objects.none()

    base_qs = Product.objects.filter(name__icontains=query)
    if not category or category not in CATEGORY_KEYWORDS:
        return base_qs

    base_qs = _filter_by_keywords(base_qs, CATEGORY_KEYWORDS[category])

    category_filter_map = FILTER_KEYWORDS.get(category, {})
    for field_name, value_map in category_filter_map.items():
        selected_value = process_category(selected_filters.get(field_name, ''))
        if not selected_value:
            continue
        if selected_value not in value_map:
            continue
        base_qs = _filter_by_keywords(base_qs, value_map[selected_value])

    return base_qs


def has_search_results(results):
    """
    KAN-37: Patikrina ar paieška grąžino bent vieną rezultatą.
    """
    return results.exists()
