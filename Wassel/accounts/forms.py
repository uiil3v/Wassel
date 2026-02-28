from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
import re

class RegisterForm(UserCreationForm):

    phone = forms.CharField(
        max_length=20,
        required=True,
        label="رقم الجوال"
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'role',
            'password1',
            'password2'
        ]