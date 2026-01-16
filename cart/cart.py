
from decimal import Decimal
from store.models import Product,Profile

class Cart(): 
    def __init__(self, request): 
        self.session = request.session 
        #Get request
        self.request = request
        cart = self.session.get("session_key")
        #if the user is new, no session key! create one
        if 'session_key' not in request.session:
            cart = self.session["session_key"] = {}
        #Make sure cart is available on all pages of the site
        self.cart = cart
        
        # Temporary fix for legacy cart data that stored quantity as int directly
        # checks if key is int and converts to dictionary if so
        changed = False
        for key, value in self.cart.items():
            if isinstance(value, int):
                self.cart[key] = {'quantity': value}
                changed = True
        if changed:
            self.save()
    def db_add(self, product, quantity): 
        product_id = str(product )
        product_qty = str(quantity)
        if product_id in self.cart:
            #self.cart[product_id]['quantity'] += int(product_qty)
            pass
        else:
            self.cart[product_id] = {'quantity': int(product_qty)} 
        self.save() 
    
    
    def add(self, product, quantity): 
        product_id = str(product.id)
        product_qty = str(quantity)
        if product_id in self.cart:
            pass
        else:
            self.cart[product_id] = {'quantity': int(product_qty)} 
        self.save() 
        #Deal with logged in users
        if self.request.user.is_authenticated:
            #Get the current user profile
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            #Convert
            cart_user = str(self.cart)
            cart_user = cart_user.replace("\'", "\"")
            #Save our carty to the profile model
            current_user.update(old_cart=str(cart_user))
            
           
    def save(self): 
        self.session["session_key"] = self.cart
        self.session.modified = True
    def remove(self, product): 
        product_id = str(product.id)
        if product_id in self.cart: 
            del self.cart[product_id]
            self.save()
    def __iter__(self): 
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        for key in cart:
            cart[key] = cart[key].copy()

        for product in products: 
            cart[str(product.id)]['product'] = product
            
        for item in cart.values(): 
            # Ensure price is handled correctly from the product object if available
            if 'product' in item:
                item['price'] = item['product'].sale_price if item['product'].is_sale else item['product'].price
            else:
                item['price'] = Decimal(item.get('price', 0))
                
            item['total_price'] = item['price'] * item['quantity']
            yield item
    def __len__(self): 
        #return sum(item['quantity'] for item in self.cart.values())
        return len(self.cart)
    def get_prods(self):
        #Get ids of products in cart
        product_ids = self.cart.keys()
        #Use ids to look up products in db
        products = Product.objects.filter(id__in=product_ids)
        #Return those looked up products
        return products
    def get_quants(self):
        quantities = self.cart
        return quantities
    def update(self, product, quantity):
        # Handle both Product object and product_id (int/str)
        if hasattr(product, 'id'):
            product_id = str(product.id)
        else:
            product_id = str(product)
            
        product_qty = int(quantity)
        
        # Update the quantity in the cart
        if product_id in self.cart:
            self.cart[product_id]['quantity'] = product_qty
            
        self.save()
        return self.cart
    def car_total(self):
        # Get products IDs from cart keys
        product_ids = self.cart.keys()
        # Use ids to look up products in db
        products = Product.objects.filter(id__in=product_ids)
        
        total = Decimal('0')
        for product in products:
            # Session keys are always strings
            product_id_str = str(product.id)
            if product_id_str in self.cart:
                quantity = self.cart[product_id_str]['quantity']
                # Use sale_price if applicable
                price = product.sale_price if product.is_sale else product.price
                total += price * quantity
        return total

    def clear(self): 
        del self.session["session_key"]
        self.session.modified = True  