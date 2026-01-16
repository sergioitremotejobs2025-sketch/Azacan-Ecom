from django.contrib import admin, messages
from django.core.files.base import ContentFile
import requests
from .models import Category, Customer, Product, Order, Profile
from .google_books import (
    fetch_dimensions_by_isbn, 
    fetch_image_by_isbn, 
    fetch_image_from_azacan, 
    fetch_all_details_from_azacan,
    fetch_all_details_by_reference_from_azacan,
    fetch_image_by_reference_from_azacan
)
from django.contrib.auth.models import User

# Register your models here.
admin.site.register(Category)
admin.site.register(Customer)
admin.site.register(Order)
admin.site.register(Profile)

#Mix Profile info and user info
class ProfileInline(admin.StackedInline):
    model = Profile

#Extends User model
class UserAdmin(admin.ModelAdmin):
    model = User
    field = ['username', 'email', 'first_name', 'last_name']
    inlines = [ProfileInline]
#Unregister the old way of User admin
admin.site.unregister(User)
#Register the new way of User admin
admin.site.register(User, UserAdmin)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "isbn", "reference", "publisher", "price", "is_sale")
    actions = [
        "fetch_dimensions_from_google_books", 
        "fetch_image_from_google_books", 
        "fetch_image_from_azacan_books", 
        "fetch_all_details_from_azacan_books",
        "fetch_by_reference_from_azacan_books",
        "fetch_image_by_reference_from_azacan_books"
    ]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'description', 'price', 'is_sale', 'sale_price', 'image')
        }),
        ('Book Details', {
            'fields': ('isbn', 'reference', 'publisher', 'year', 'edition_place', 'pages', 'measures', 'dimensions'),
        }),
    )

    @admin.action(description="Fetch dimensions from Google Books API")
    def fetch_dimensions_from_google_books(self, request, queryset):
        updated = 0
        skipped_no_isbn = 0
        skipped_no_dims = 0
        for product in queryset:
            if not product.isbn:
                skipped_no_isbn += 1
                continue
            dims = fetch_dimensions_by_isbn(product.isbn)
            if dims:
                product.dimensions = dims
                product.save(update_fields=["dimensions"])
                updated += 1
            else:
                skipped_no_dims += 1
        
        if updated > 0:
            self.message_user(request, f"Updated dimensions for {updated} product(s).", messages.SUCCESS)
        if skipped_no_isbn > 0:
            self.message_user(request, f"Skipped {skipped_no_isbn} product(s) without ISBN.", messages.WARNING)
        if skipped_no_dims > 0:
            self.message_user(request, f"Skipped {skipped_no_dims} product(s) - no dimensions found in Google Books.", messages.WARNING)

    @admin.action(description="Fetch image from Google Books API")
    def fetch_image_from_google_books(self, request, queryset):
        updated = 0
        skipped_no_isbn = 0
        skipped_no_image = 0
        for product in queryset:
            if not product.isbn:
                skipped_no_isbn += 1
                continue
            image_bytes = fetch_image_by_isbn(product.isbn)
            if image_bytes:
                # Save image with ISBN as filename
                filename = f"{product.isbn}.jpg"
                product.image.save(filename, ContentFile(image_bytes), save=True)
                updated += 1
            else:
                skipped_no_image += 1
        
        if updated > 0:
            self.message_user(request, f"Updated images for {updated} product(s).", messages.SUCCESS)
        if skipped_no_isbn > 0:
            self.message_user(request, f"Skipped {skipped_no_isbn} product(s) without ISBN.", messages.WARNING)
        if skipped_no_image > 0:
            self.message_user(request, f"Skipped {skipped_no_image} product(s) - no image found in Google Books.", messages.WARNING)
    @admin.action(description="Fetch image from Azacán Books")
    def fetch_image_from_azacan_books(self, request, queryset):
        updated = 0
        skipped_no_isbn = 0
        skipped_no_image = 0
        for product in queryset:
            if not product.isbn:
                skipped_no_isbn += 1
                continue
            image_bytes = fetch_image_from_azacan(product.isbn)
            if image_bytes:
                # Save image with ISBN as filename
                filename = f"{product.isbn}_azacan.jpg"
                product.image.save(filename, ContentFile(image_bytes), save=True)
                updated += 1
            else:
                skipped_no_image += 1
        
        if updated > 0:
            self.message_user(request, f"Updated images from Azacán for {updated} product(s).", messages.SUCCESS)
        if skipped_no_isbn > 0:
            self.message_user(request, f"Skipped {skipped_no_isbn} product(s) without ISBN.", messages.WARNING)
        if skipped_no_image > 0:
            self.message_user(request, f"Skipped {skipped_no_image} product(s) - no image found in Azacán Books.", messages.WARNING)

    @admin.action(description="Fetch all details from Azacán Books")
    def fetch_all_details_from_azacan_books(self, request, queryset):
        updated = 0
        skipped_no_isbn = 0
        skipped_no_details = 0
        for product in queryset:
            if not product.isbn:
                skipped_no_isbn += 1
                continue
            details = fetch_all_details_from_azacan(product.isbn)
            if details:
                if 'name' in details:
                    product.name = details['name']
                if 'description' in details:
                    product.description = details['description']
                if 'reference' in details:
                    product.reference = details['reference']
                # ISBN is already present if we are here, but update for consistency
                if 'isbn' in details:
                    product.isbn = details['isbn']
                if 'publisher' in details:
                    product.publisher = details['publisher']
                
                # Handle Image Download
                if 'image_url' in details:
                    try:
                        headers = {"User-Agent": "Mozilla/5.0"}
                        img_response = requests.get(details['image_url'], headers=headers, timeout=15)
                        img_response.raise_for_status()
                        filename = f"{product.isbn}_azacan.jpg" if product.isbn else f"{product.id}_azacan.jpg"
                        product.image.save(filename, ContentFile(img_response.content), save=False)
                    except Exception:
                        pass
                
                if 'year' in details:
                    product.year = details['year']
                if 'edition_place' in details:
                    product.edition_place = details['edition_place']
                if 'pages' in details:
                    product.pages = details['pages']
                if 'measures' in details:
                    product.measures = details['measures']
                
                product.save()
                updated += 1
            else:
                skipped_no_details += 1
        
        if updated > 0:
            self.message_user(request, f"Updated details from Azacán for {updated} product(s).", messages.SUCCESS)
        if skipped_no_isbn > 0:
            self.message_user(request, f"Skipped {skipped_no_isbn} product(s) without ISBN.", messages.WARNING)
        if skipped_no_details > 0:
            self.message_user(request, f"Skipped {skipped_no_details} product(s) - no details found in Azacán Books.", messages.WARNING)

    @admin.action(description="Fetch details from Azacán by Reference")
    def fetch_by_reference_from_azacan_books(self, request, queryset):
        updated = 0
        skipped_no_ref = 0
        skipped_no_details = 0
        for product in queryset:
            if not product.reference:
                skipped_no_ref += 1
                continue
            details = fetch_all_details_by_reference_from_azacan(product.reference)
            if details:
                if 'name' in details:
                    product.name = details['name']
                if 'description' in details:
                    product.description = details['description']
                if 'isbn' in details:
                    product.isbn = details['isbn']
                
                # Handle Image Download
                if 'image_url' in details:
                    try:
                        headers = {"User-Agent": "Mozilla/5.0"}
                        img_response = requests.get(details['image_url'], headers=headers, timeout=15)
                        img_response.raise_for_status()
                        filename = f"{product.reference}_azacan.jpg"
                        product.image.save(filename, ContentFile(img_response.content), save=False)
                    except Exception:
                        pass

                # Already have reference, but update if it changed or to be sure
                if 'reference' in details:
                    product.reference = details['reference']
                if 'publisher' in details:
                    product.publisher = details['publisher']
                if 'year' in details:
                    product.year = details['year']
                if 'edition_place' in details:
                    product.edition_place = details['edition_place']
                if 'pages' in details:
                    product.pages = details['pages']
                if 'measures' in details:
                    product.measures = details['measures']
                
                product.save()
                updated += 1
            else:
                skipped_no_details += 1
        
        if updated > 0:
            self.message_user(request, f"Updated details from Azacán for {updated} product(s).", messages.SUCCESS)
        if skipped_no_ref > 0:
            self.message_user(request, f"Skipped {skipped_no_ref} product(s) without Reference.", messages.WARNING)
        if skipped_no_details > 0:
            self.message_user(request, f"Skipped {skipped_no_details} product(s) - no details found in Azacán Books by Reference.", messages.WARNING)

    @admin.action(description="Fetch image from Azacán by Reference")
    def fetch_image_by_reference_from_azacan_books(self, request, queryset):
        updated = 0
        skipped_no_ref = 0
        skipped_no_image = 0
        for product in queryset:
            if not product.reference:
                skipped_no_ref += 1
                continue
            image_bytes = fetch_image_by_reference_from_azacan(product.reference)
            if image_bytes:
                # Save image with Reference as filename
                filename = f"{product.reference}_azacan.jpg"
                product.image.save(filename, ContentFile(image_bytes), save=True)
                updated += 1
            else:
                skipped_no_image += 1
        
        if updated > 0:
            self.message_user(request, f"Updated images from Azacán by Reference for {updated} product(s).", messages.SUCCESS)
        if skipped_no_ref > 0:
            self.message_user(request, f"Skipped {skipped_no_ref} product(s) without Reference.", messages.WARNING)
        if skipped_no_image > 0:
            self.message_user(request, f"Skipped {skipped_no_image} product(s) - no image found in Azacán Books by Reference.", messages.WARNING)

