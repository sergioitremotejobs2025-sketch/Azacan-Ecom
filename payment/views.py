from django.shortcuts import render, redirect
from django.contrib import messages
from cart.cart import Cart

from payment.forms import ShippingForm
from payment.models import ShippingAddress

from recommendations.rag import get_recommendations_by_book_title, get_recommendations

def checkout(request):
    cart = Cart(request)
    cart_products = cart.get_prods()
    quantities = cart.get_quants()
    totals = cart.car_total()
    
    recommendations = []
    try:
        if request.user.is_authenticated:
            recommendations = get_recommendations(request.user.id)
    except Exception as e:
        print(f"Error getting recommendations: {e}")

    form = None

    if request.user.is_authenticated: 
        try:
            # Use filter().first() to avoid MultipleObjectsReturned if data is dirty for some reason
            shipping_user = ShippingAddress.objects.filter(user=request.user).first()
            if shipping_user:
                form = ShippingForm(request.POST or None, instance=shipping_user)
            else:
                form = ShippingForm(request.POST or None)
        except Exception as e:
             print(f"Error fetching shipping address: {e}")
             form = ShippingForm(request.POST or None)
    else:
        # User not authenticated
        form = ShippingForm(request.POST or None)

    return render(request, 'payment/checkout.html', {
        'cart_products': cart_products, 
        'quantities': quantities, 
        'totals': totals, 
        'cart': cart, 
        'recommendations': recommendations, 
        'form': form 
    }) 

def billing_info(request):
    if request.POST:
        cart = Cart(request)
        cart_products = cart.get_prods()
        quantities = cart.get_quants()
        totals = cart.car_total()

        # Create session with shipping info
        my_shipping = request.POST
        request.session['my_shipping'] = my_shipping

        # Check if user is logged in
        if request.user.is_authenticated:
            return render(request, "payment/billing_info.html", {
                "cart_products":cart_products, 
                "quantities":quantities, 
                "totals":totals, 
                "shipping_info": request.POST
            })
        else:
             return render(request, "payment/billing_info.html", {
                "cart_products":cart_products, 
                "quantities":quantities, 
                "totals":totals, 
                "shipping_info": request.POST
            })

    else:
        messages.success(request, "Access Denied")
        return redirect('home')

def payment_success(request):
    return render(request, 'payment/payment_success.html')
