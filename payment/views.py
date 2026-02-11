from django.shortcuts import render, redirect
from django.http import HttpResponse

def checkout(request):
    return HttpResponse("Checkout Placeholder")

def billing_info(request):
    return HttpResponse("Billing Info Placeholder")

def process_order(request):
    return HttpResponse("Process Order Placeholder")

def payment_success(request):
    return render(request, 'payment/payment_success.html')
