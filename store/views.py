from django.shortcuts import render,redirect
from .models import Product, Category, Profile
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm

from payment.forms import ShippingForm
from payment.models import ShippingAddress

from django import forms
from django.db.models import Q
from cart.cart import Cart
import json

def search(request):
    # Determine if they filled out the form
    if request.method == 'POST':
        query = request.POST.get('search')
        products = Product.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
        if not products:
            messages.error(request, 'No se encontraron productos con el nombre "{}"'.format(query)) 
            return redirect('search')
        else:
            return render(request, 'search.html', {'products': products})
    else:
        return render(request, 'search.html')

def update_info(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to update your profile.')
        return redirect('login')
    else:
        current_user = Profile.objects.get(user_id=request.user.id)
        #Get Current User's Shipping Address
        try:
            shipping_user = ShippingAddress.objects.get(user_id=request.user.id)
        except ShippingAddress.DoesNotExist:
            shipping_user = None

        form = UserInfoForm(instance=current_user)
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        if request.method == 'POST':
            form = UserInfoForm(request.POST, instance=current_user)
            if form.is_valid() and shipping_form.is_valid():
                form.save()
                shipping_address = shipping_form.save(commit=False)
                shipping_address.user = request.user
                shipping_address.save()
                messages.success(request, 'Profile updated successfully.')
            return redirect('update_info')
        else:
            messages.error(request, 'Error updating profile.')
    return render(request, 'update_info.html', {'form': form, 'shipping_form': shipping_form})

def update_password(request):
    if request.user.is_authenticated:
        current_user = request.user
        #Did they fill out the form?
        if request.method == 'POST':
            form = ChangePasswordForm(current_user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Password updated successfully.')
                login(request, current_user)
                return redirect('home')
            else:
                for error in list(form.errors.values()):
                    messages.error(request, error)
        else:
            form = ChangePasswordForm(current_user)
            return render(request, 'update_password.html', {'form':form})
    else:
        messages.error(request, 'You must be logged in to update your password.')
        return redirect('login')

def update_user(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to update your profile.')
        return redirect('login')
    else:
        current_user = User.objects.get(id=request.user.id)
        user_form = UpdateUserForm(instance=current_user)
        if request.method == 'POST':
            user_form = UpdateUserForm(request.POST, instance=current_user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Profile updated successfully.')
            return redirect('update_user')
        else:
            messages.error(request, 'Error updating profile.')
    return render(request, 'update_user.html', {'user_form': user_form})  
def category_summary(request):
    categories = Category.objects.all()
    return render(request, 'category_summary.html', {'categories': categories})

def category(request, name):
    name = name.replace("-", " ")
    try:
        category = Category.objects.get(name=name)
        products = Product.objects.filter(category=category)
        return render(request, 'category.html', {'category': category, 'products': products})
    except Category.DoesNotExist:
        messages.error(request, 'Categoría no encontrada.')
        return redirect('home')
def product(request, pk):
    product = Product.objects.get(pk=pk)
    return render(request, 'product.html', {'product': product})

def home(request):
    # Obtener todos los productos (puedes filtrar, ordenar o paginar aquí)
    products = Product.objects.all()

    # Opcional: depuración en consola (útil mientras desarrollas)
    for product in products:
        dims = product.dimensions or {}  # Asegura que no sea None
        height = dims.get('height', 'N/A')
        width = dims.get('width', 'N/A')
        thickness = dims.get('thickness', 'N/A')
        #print(f"Producto: {product.title} | Dimensiones: {height} x {width} x {thickness}")

    # ¡IMPORTANTE! Devolver la respuesta HTTP con el template
    context = {
        'products': products,
        'page_title': 'Inicio - Mi Tienda',  # Opcional, para usar en el template
    }
    return render(request, 'home.html', context)

def about(request):
    return render(request, 'about.html')    

def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            #Do some shopping cart magic
            current_user = Profile.objects.get(user__id=request.user.id)
            saved_cart = current_user.old_cart
            if saved_cart != "{}":
                converted_cart = json.loads(saved_cart)
                cart = Cart(request)
                #Loop through the cart and add items to the new cart
                for key, value in converted_cart.items():
                    cart.db_add(product=key, quantity=value['quantity'])
                    #ßcart.add(int(item['product_id']), int(item['quantity']))  
            





            messages.success(request, 'Has iniciado sesión correctamente.')
            return redirect('home')
        else:
            messages.error(request, 'Credenciales inválidas.')
    return render(request, 'login.html') 
def logout_user(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('home')
def register_user(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Has registrado correctamente.')
            return redirect('home')
        else:
            messages.error(request, 'Error al registrar.')
            return render(request, 'register.html', {'form': form})
    else:
        form = SignUpForm()
        return render(request, 'register.html', {'form': form})