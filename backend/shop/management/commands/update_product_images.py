from django.core.management.base import BaseCommand
from shop.models import Product


class Command(BaseCommand):
    help = 'Update product images from a list of URLs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Path to a file with product image mappings (name|url format)',
        )

    def handle(self, *args, **options):
        """
        Update product images. Can be used in two ways:
        
        1. From file: python manage.py update_product_images --file images.txt
           File format (one per line):
           Pienas DVARO 2,5% 1 l|https://example.com/image.jpg
           
        2. Manually in the shell:
           python manage.py shell
           >>> from shop.models import Product
           >>> Product.objects.filter(name='Pienas DVARO 2,5% 1 l').update(
           ...     image_url='https://example.com/image.jpg'
           ... )
        """
        
        if options.get('file'):
            try:
                with open(options['file'], 'r', encoding='utf-8') as f:
                    updated = 0
                    for line in f:
                        line = line.strip()
                        if not line or '|' not in line:
                            continue
                        
                        name, url = line.split('|', 1)
                        name = name.strip()
                        url = url.strip()
                        
                        count = Product.objects.filter(name=name).update(image_url=url)
                        if count > 0:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✓ Updated "{name}": {count} products'
                                )
                            )
                            updated += count
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'⚠ Product not found: "{name}"')
                            )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'\nTotal updated: {updated} products')
                    )
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f'File not found: {options["file"]}'))
        else:
            self.stdout.write(
                self.style.WARNING(
                    'No file provided. Use --file to specify image mappings file.\n'
                    'File format: product_name|image_url (one per line)'
                )
            )
