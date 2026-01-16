from .cart import Cart

# Create context processor so our Cart can work on all pages of the site
# This will make the cart available to all templates
# This is a function that returns a dictionary
def cart(request):
    # Return the cart object
    return {'cart': Cart(request)}