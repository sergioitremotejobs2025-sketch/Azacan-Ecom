from django.core.management.base import BaseCommand
from recommendations.models import Book
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate embeddings for books using SentenceTransformer'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of books to process in each batch (default: 100)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate embeddings even if they already exist'
        )
        parser.add_argument(
            '--book-ids',
            nargs='+',
            type=int,
            help='Specific book IDs to process (space-separated)'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        force = options['force']
        book_ids = options.get('book_ids')

        self.stdout.write(self.style.SUCCESS('Loading SentenceTransformer model...'))
        model = SentenceTransformer('all-MiniLM-L6-v2')
        self.stdout.write(self.style.SUCCESS('Model loaded successfully!'))

        # Get books to process
        if book_ids:
            books = Book.objects.filter(id__in=book_ids)
            self.stdout.write(f'Processing {len(book_ids)} specific books...')
        elif force:
            books = Book.objects.all()
            self.stdout.write(f'Regenerating embeddings for all {books.count()} books...')
        else:
            books = Book.objects.filter(embedding__isnull=True)
            self.stdout.write(f'Processing {books.count()} books without embeddings...')

        if not books.exists():
            self.stdout.write(self.style.WARNING('No books to process.'))
            return

        total_books = books.count()
        processed = 0
        errors = 0
        skipped = 0

        # Process in batches
        for i in range(0, total_books, batch_size):
            batch = list(books[i:i + batch_size])
            
            for book in batch:
                try:
                    # Skip if embedding exists and not forcing
                    if book.embedding is not None and not force:
                        skipped += 1
                        continue

                    # Combine title, author, description, and subjects for richer embeddings
                    text = f"Title: {book.title}. Author: {book.author}. infantil: {book.infantil}. Category: {book.category}. Description: {book.description}. Subjects: {book.subjects}."
                    
                    # Generate embedding
                    embedding = model.encode(text)
                    
                    # Save to database
                    book.embedding = embedding
                    book.save(update_fields=['embedding'])
                    
                    processed += 1
                    
                    # Progress update every 10 books
                    if processed % 10 == 0:
                        progress = (i + len(batch)) / total_books * 100
                        self.stdout.write(
                            f'Progress: {progress:.1f}% ({processed} processed, {errors} errors, {skipped} skipped)'
                        )
                
                except Exception as e:
                    errors += 1
                    logger.error(f'Error processing book {book.id} ({book.title}): {e}')
                    self.stdout.write(
                        self.style.ERROR(f'Error processing book {book.id}: {str(e)}')
                    )

        # Final summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('Embedding generation complete!'))
        self.stdout.write(self.style.SUCCESS(f'Total books processed: {processed}'))
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f'Books skipped (already had embeddings): {skipped}'))
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'Errors encountered: {errors}'))
        self.stdout.write(self.style.SUCCESS('='*50))