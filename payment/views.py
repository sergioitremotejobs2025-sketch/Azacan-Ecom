from django.shortcuts import render
from cart.cart import Cart

from payment.forms import ShippingForm
from payment.models import ShippingAddress

from recommendations.rag import get_recommendations_by_book_title, get_recommendations
# Create your views here.
def checkout(request):
    cart = Cart(request)
    cart_products = cart.get_prods()
    quantities = cart.get_quants()
    totals = cart.car_total()
    
    
    #recommendations = get_recommendations_by_book_title("Estudio del Quijote")
    recommendations = get_recommendations(request.user.id)
    if request.user.is_authenticated: 
         
        form = ShippingForm(request.POST or None,instance=ShippingAddress.objects.get(user=request.user))
        return render(request, 'payment/checkout.html',{'cart_products': cart_products  , 'quantities': quantities, 'totals': totals, 'cart': cart, 'recommendations': recommendations, 'form': form}) 
    else:
        form = ShippingForm(request.POST or None)
        return render(request, 'payment/checkout.html',{'cart_products': cart_products  , 'quantities': quantities, 'totals': totals, 'cart': cart }) 



def payment_success(request):
    return render(request, 'payment/payment_success.html')

