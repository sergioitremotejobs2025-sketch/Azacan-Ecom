from django.shortcuts import render, get_object_or_404
from .cart import Cart
from store.models import Product
from django.http import JsonResponse 
from django.contrib import messages

# Create your views here.
def cart_summary(request):
    #Get cart instance
    cart = Cart(request)
    #Get products in cart
    cart_products = cart.get_prods()
    quantities = cart.get_quants()
    #Get total price
    totals = cart.car_total()
    return render(request, 'cart_summary.html',{'cart_products': cart_products  , 'quantities': quantities, 'totals': totals, 'cart': cart})
def cart_add(request):
    cart = Cart(request)
    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        product_qty = int(request.POST.get('product_qty'))
        product = get_object_or_404(Product, id=product_id)
        cart.add(product=product, quantity=product_qty)
        cart_quantity = cart.__len__()
        response = JsonResponse({'Product Name: ': product_id,'qty': product_qty})
        messages.success(request, 'Product added to cart')
        return response
    
def cart_delete(request):
    cart = Cart(request)
    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        # product_qty = int(request.POST.get('product_qty')) # Not needed for delete
        product = get_object_or_404(Product, id=product_id)
        cart.remove(product=product)
        response = JsonResponse({'product': product_id})
        messages.success(request, 'Product removed from cart')  
        return response
def cart_update(request):
    cart = Cart(request)
    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        product_qty = int(request.POST.get('product_qty'))
        
        cart.update(product=product_id, quantity=product_qty)
        
        response = JsonResponse({'qty': product_qty})
        messages.success(request, 'Product updated in cart')
        return response
        #return redirect('cart_summary')