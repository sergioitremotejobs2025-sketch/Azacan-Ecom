import graphene
from graphene_django import DjangoObjectType
from .models import Book
# Import the custom converter to register it
from . import graphql_types  # This registers the converter

class BookType(DjangoObjectType):
    class Meta:
        model = Book
        fields = ("id", "title", "author", "published_date", "isbn", "embedding")
        
    def resolve_embedding(self, info):
        # Convert the vector to a list for GraphQL serialization
        if self.embedding is not None:
            return list(self.embedding)
        return None

class Query(graphene.ObjectType):
    all_books = graphene.List(BookType)
    book_by_id = graphene.Field(BookType, id=graphene.Int(required=True))

    def resolve_all_books(root, info):
        return Book.objects.all().order_by('-id')

    def resolve_book_by_id(root, info, id):
        try:
            return Book.objects.get(pk=id)
        except Book.DoesNotExist:
            return None

class CreateBook(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        author = graphene.String(required=True)
        published_date = graphene.Date(required=True)
        isbn = graphene.String(required=True)

    book = graphene.Field(BookType)
    success = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, title, author, published_date, isbn):
        book = Book(
            title=title,
            author=author,
            published_date=published_date,
            isbn=isbn
        )
        book.save()
        return CreateBook(book=book, success=True)

class Mutation(graphene.ObjectType):
    create_book = CreateBook.Field()

# Don't need schema definition here if you're using root schema
