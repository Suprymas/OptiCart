import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from shop.models import Product

# Use Unsplash images - high quality and reliable
image_map = {
    'Pienas DVARO 2,5% 1 l': 'https://images.unsplash.com/photo-1550583573-3f5988fba109?w=300&h=300&fit=crop',
    'Pienas DVARO 3,5% 1 l': 'https://images.unsplash.com/photo-1550583573-3f5988fba109?w=300&h=300&fit=crop',
    'Kefyras VILKYŠKIŲ 2,5% 1 kg': 'https://images.unsplash.com/photo-1488477181946-85a2fdeee81f?w=300&h=300&fit=crop',
    'Grietinė DVARO 30% 380 g': 'https://images.unsplash.com/photo-1588083949404-c0b3e9a0ae3e?w=300&h=300&fit=crop',
    'Sviestas ROKIŠKIO NAMINIS 82% 180 g': 'https://images.unsplash.com/photo-1589985643862-16d3cc003342?w=300&h=300&fit=crop',
    'Sviestas ŽEMAITIJOS 82% 200 g': 'https://images.unsplash.com/photo-1589985643862-16d3cc003342?w=300&h=300&fit=crop',
    'Jogurtas GRAIKIŠKA AMFORA natūralus 3,9% 370 g': 'https://images.unsplash.com/photo-1488477181946-85a2fdeee81f?w=300&h=300&fit=crop',
    'Duona MOČIUTĖS juoda 450 g': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=300&h=300&fit=crop',
    'Skrudinimo duona TOSTE 500 g': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=300&h=300&fit=crop',
    'Cukrus PANEVĖŽIO PLIUS 1 kg': 'https://images.unsplash.com/photo-1600887373223-cc40f27daeaa?w=300&h=300&fit=crop',
    'Lietuviški trumpavaisiai agurkai 1 kg': 'https://images.unsplash.com/photo-1563337503-2d7d4fb4b4d1?w=300&h=300&fit=crop',
    'Bananai 1 kg': 'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=300&h=300&fit=crop',
}

updated = 0
for product_name, image_url in image_map.items():
    count = Product.objects.filter(name=product_name).update(image_url=image_url)
    if count > 0:
        print(f'✓ {product_name}: {count} products')
        updated += count

print(f'\nTotal updated: {updated} products')
