import json
import os
import requests
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from recommendations.models import Book
from store.google_books import fetch_image_by_reference_from_azacan

class Command(BaseCommand):
    help = 'Import cleaned Azacan book data from JSON'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the cleaned JSON file')
        parser.add_argument('--limit', type=int, default=None, help='Limit the number of books to import')
        parser.add_argument('--skip-images', action='store_true', help='Skip downloading images')
        parser.add_argument('--update', action='store_true', help='Update existing books if reference exists')

    def download_image(self, url, book_reference):
        # First try the scraper which we verified works
        try:
            content = fetch_image_by_reference_from_azacan(book_reference)
            if content:
                return ContentFile(content, name=f"{book_reference}.jpg")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Scraper failed for {book_reference}: {e}"))

        # Fallback to the provided URL if scraper fails
        if url:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    extension = url.split('.')[-1].split('?')[0]
                    if not extension or len(extension) > 4:
                        extension = "jpg"
                    filename = f"{book_reference}.{extension}"
                    return ContentFile(response.content, name=filename)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Direct download failed for {book_reference}: {e}"))
        
        return None

    def handle(self, *args, **options):
        json_file = options['json_file']
        limit = options['limit']
        skip_images = options['skip_images']
        update = options['update']

        if not os.path.exists(json_file):
            self.stdout.write(self.style.ERROR(f"File not found: {json_file}"))
            return

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if limit:
            data = data[:limit]

        count = 0
        updated = 0
        errors = 0

        for item in data:
            try:
                reference = item.get('reference')
                if not reference:
                    continue

                book, created = Book.objects.get_or_create(reference=reference, defaults={
                    'title': item.get('title'),
                    'author': item.get('author'),
                    'stock': item.get('stock', 0),
                    'price': Decimal(str(item.get('price', 0))),
                    'infantil': item.get('infantil'),
                    'category': item.get('category'),
                    'description': item.get('description'),
                    'iva': Decimal(str(item.get('iva', 0))),
                })

                if not created and update:
                    book.title = item.get('title')
                    book.author = item.get('author')
                    book.stock = item.get('stock', 0)
                    book.price = Decimal(str(item.get('price', 0)))
                    book.infantil = item.get('infantil')
                    book.category = item.get('category')
                    book.description = item.get('description')
                    book.iva = Decimal(str(item.get('iva', 0)))
                    book.save()
                    updated += 1
                elif not created:
                    # If we are not updating, skip but still maybe try to download image if missing
                    pass
                
                if count >= (limit or 999999):
                    break

                if not skip_images:
                    # If book has no image, try to download it
                    if not book.image:
                        image_file = self.download_image(item.get('image_url'), reference)
                        if image_file:
                            book.image.save(image_file.name, image_file, save=True)
                            self.stdout.write(f"Downloaded image for {reference}")

                count += 1
                if count % 10 == 0:
                    self.stdout.write(f"Processed {count} books...")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error importing book {item.get('reference')}: {e}"))
                errors += 1

        self.stdout.write(self.style.SUCCESS(f"Import complete: {count} processed, {updated} updated, {errors} errors."))
