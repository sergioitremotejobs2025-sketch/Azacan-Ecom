from django.shortcuts import render, redirect
from django.contrib import messages
from cart.cart import Cart

from payment.forms import ShippingForm
from payment.models import ShippingAddress, Order, OrderItem
# Added Order, OrderItem imports

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

def process_order(request):
    if request.POST:
        # Get the cart
        cart = Cart(request)
        cart_products = cart.get_prods()
        quantities = cart.get_quants()
        totals = cart.car_total()

        # Get Billing Info from the last page
        payment_form = request.POST

        # Get Shipping Session Data
        my_shipping = request.session.get('my_shipping')

        # Gather Order Info
        full_name = my_shipping['shipping_full_name']
        email = my_shipping['shipping_email']
        # Create Shipping Address from session info
        shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_pincode']}\n{my_shipping['shipping_country']}"
        amount_paid = totals

        # Create an Order
        if request.user.is_authenticated:
            user = request.user
            create_order = Order(user=user, full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
            create_order.save()

            # Add order items
            # Get the order ID
            order_id = create_order.pk
            
            # Get product Info
            for product in cart_products:
                # Get product ID
                product_id = product.id
                # Get product price
                if product.is_sale:
                    price = product.sale_price
                else:
                    price = product.price

                # Get quantity
                for key, value in quantities.items():
                    if int(key) == product.id:
                        # Create order item
                        create_order_item = OrderItem(order_id=order_id, product_id=product_id, user=user, quantity=value['quantity'], price=price)
                        create_order_item.save()

            # Delete our cart
            for key in list(request.session.keys()):
                if key == "session_key":
                    del request.session[key]
            
            # Delete Cart from Database (old_cart field)
            # current_user = Profile.objects.filter(user__id=request.user.id)
            # Delete old_cart field in DB not yet implemented in model properly but consistent with cart app logic
            
            messages.success(request, "Order Placed!")
            return redirect('payment_success')

        else:
            # Not logged in
            create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
            create_order.save()

            # Add order items
            # Get the order ID
            order_id = create_order.pk
            
            # Get product Info
            for product in cart_products:
                # Get product ID
                product_id = product.id
                # Get product price
                if product.is_sale:
                    price = product.sale_price
                else:
                    price = product.price

                # Get quantity
                for key, value in quantities.items():
                    if int(key) == product.id:
                        # Create order item
                        create_order_item = OrderItem(order_id=order_id, product_id=product_id, quantity=value['quantity'], price=price)
                        create_order_item.save()

            # Delete our cart
            for key in list(request.session.keys()):
                if key == "session_key":
                    del request.session[key]

            messages.success(request, "Order Placed!")
            return redirect('payment_success')

    else:
        messages.success(request, "Access Denied")
        return redirect('home')

def payment_success(request):
    return render(request, 'payment/payment_success.html')
