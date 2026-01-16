from django.contrib import admin
from .models import Book, Purchase

# Register your models here.
#admin.site.register(Book)
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author')
    #list_filter = ('is_sale', 'category')
    #search_fields = ('title', 'author', 'description')
    #ordering = ('-price',)

#admin.site.register(Purchase)

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'purchase_date')
    #list_filter = ('user', 'book', 'purchase_date')
    #search_fields = ('user__username', 'book__title')
    #date_hierarchy = 'purchase_date'
    #ordering = ('-purchase_date',)
