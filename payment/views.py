from django.shortcuts import render, redirect
from django.contrib import messages
from cart.cart import Cart
from .forms import ShippingForm
from .models import ShippingAddress

def checkout(request):
    # Get the cart
    cart = Cart(request)
    cart_products = cart.get_prods()
    quantities = cart.get_quants()
    totals = cart.car_total()

    if request.user.is_authenticated:
        # Checkout as logged in user
        # Shipping User
        shipping_user = ShippingAddress.objects.filter(user__id=request.user.id).first()
        if shipping_user:
            shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        else:
            shipping_form = ShippingForm(request.POST or None)
        return render(request, "payment/checkout.html", {"cart": cart, "totals": totals, "form": shipping_form})
    else:
        # Checkout as guest
        shipping_form = ShippingForm(request.POST or None)
        return render(request, "payment/checkout.html", {"cart": cart, "totals": totals, "form": shipping_form})

def billing_info(request):
    if request.POST:
        # Get the cart
        cart = Cart(request)
        cart_products = cart.get_prods()
        quantities = cart.get_quants()
        totals = cart.car_total()

        # Create a session with Shipping Info
        my_shipping = request.POST
        request.session['my_shipping'] = my_shipping

        # Check to see if user is logged in
        if request.user.is_authenticated:
            # Get The Billing Form
            # billing_form = PaymentForm()
            return render(request, "payment/billing_info.html", {"cart": cart, "totals": totals, "shipping_info": request.POST})
        else:
            # Not logged in
            # Get The Billing Form
            # billing_form = PaymentForm()
            return render(request, "payment/billing_info.html", {"cart": cart, "totals": totals, "shipping_info": request.POST})

    else:
        messages.error(request, "Access Denied")
        return redirect('home')

def process_order(request):
    if request.POST:
        # Get the cart
        cart = Cart(request)
        cart_products = cart.get_prods()
        quantities = cart.get_quants()
        totals = cart.car_total()

        # Get Billing Info from the last page
        payment_form = request.POST
        # Get Shipping Info from session
        my_shipping = request.session.get('my_shipping')

        # Create Order
        # This is a simplified version, usually you'd create Order and OrderItem models here
        # and integrate with a payment gateway like Stripe or PayPal.
        
        # After successful "payment"
        for key in list(request.session.keys()):
            if key == "session_key":
                del request.session[key]
        
        # Also clear my_shipping session
        if 'my_shipping' in request.session:
            del request.session['my_shipping']

        messages.success(request, "Order Placed Successfully!")
        return redirect('payment_success')
    else:
        messages.error(request, "Access Denied")
        return redirect('home')

def payment_success(request):
    return render(request, 'payment/payment_success.html')
