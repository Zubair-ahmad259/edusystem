# forms.py
from django import forms
from .models import ClearFee

class ClearFeeForm(forms.ModelForm):
    class Meta:
        model = ClearFee
        fields = ['receipt_number', 'cleared_amount', 'payment_method', 'collector_name', 'remarks']
        widgets = {
            'receipt_number': forms.TextInput(attrs={'class': 'form-control'}),
            'cleared_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'collector_name': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }