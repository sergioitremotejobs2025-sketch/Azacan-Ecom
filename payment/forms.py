from django import forms
from .models import ShippingAddress
from django.contrib.auth.models import User
class ShippingForm(forms.ModelForm):
    shipping_full_name = forms.CharField(label='Full Name', widget=forms.TextInput(attrs={'class': 'form-control'}), max_length=255, required=True)
    shipping_email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'form-control'}), max_length=255, required=True)
    shipping_address1 = forms.CharField(label='Address 1', widget=forms.TextInput(attrs={'class': 'form-control'}), max_length=255, required=True)
    shipping_address2 = forms.CharField(label='Address 2', widget=forms.TextInput(attrs={'class': 'form-control'}), max_length=255, required=True)
    shipping_city = forms.CharField(label='City', widget=forms.TextInput(attrs={'class': 'form-control'}), max_length=255, required=True)
    shipping_state = forms.CharField(label='State', widget=forms.TextInput(attrs={'class': 'form-control'}), max_length=255, required=True)
    shipping_country = forms.CharField(label='Country', widget=forms.TextInput(attrs={'class': 'form-control'}), max_length=255, required=True)
    shipping_pincode = forms.CharField(label='Pincode', widget=forms.TextInput(attrs={'class': 'form-control'}), max_length=255, required=True)
    shipping_phone = forms.CharField(label='Phone', widget=forms.TextInput(attrs={'class': 'form-control'}), max_length=255, required=True)
    class Meta:
        model = ShippingAddress
        fields = [
            'shipping_full_name',
            'shipping_email',
            'shipping_address1',
            'shipping_address2',
            'shipping_city',
            'shipping_state',
            'shipping_country',
            'shipping_pincode',
            'shipping_phone',
        ]   
        exclude = ['user',]