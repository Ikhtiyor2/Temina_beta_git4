from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from django.contrib.auth.models import User
from . import models



class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = User
        errors = []
    

class RegistrationForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control'
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control'
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name',  'password1', 'password2']
        widgets = {
            'email': forms.EmailInput(
                attrs={'class': 'form-control'}
            )
            ,
            'first_name': forms.TextInput(
                attrs={'class': 'form-control'}
            )
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Укажите email.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Этот email уже зарегистрирован.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user