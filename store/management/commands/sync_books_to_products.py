from django.core.management.base import BaseCommand
from recommendations.models import Book
from store.models import Product, Category
from django.db import transaction

class Command(BaseCommand):
    help = 'Sync all books from Recommendations to Store Products'

    def handle(self, *args, **options):
        # 1. Ensure "Libros" category exists
        category, created = Category.objects.get_or_create(
            name='Libros',
            defaults={'description': 'Catálogo completo de libros importados.'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created "Libros" category.'))

        books = Book.objects.all()
        total = books.count()
        self.stdout.write(f'Found {total} books to sync.')

        created_count = 0
        updated_count = 0
        errors = 0

        for book in books:
            try:
                # Use reference as the unique identifier if available, otherwise title
                lookup_field = {'reference': book.reference} if book.reference else {'name': book.title}
                
                with transaction.atomic():
                    product, created = Product.objects.update_or_create(
                        **lookup_field,
                        defaults={
                            'name': book.title,
                            'price': book.price or 0,
                            'category': category,
                            'description': book.description,
                            'publisher': book.author,
                            'image': book.image, # Django handles pointing to the same file
                            'reference': book.reference,
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                if (created_count + updated_count) % 100 == 0:
                    self.stdout.write(f'Synced {created_count + updated_count}/{total}...')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error syncing book {book.title}: {e}'))
                errors += 1

        self.stdout.write(self.style.SUCCESS(
            f'Sync complete! Created: {created_count}, Updated: {updated_count}, Errors: {errors}'
        ))
