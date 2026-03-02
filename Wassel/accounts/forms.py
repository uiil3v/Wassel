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
            'city',          # 🔥 أضفنا المدينة هنا
            'role',
            'password1',
            'password2'
        ]

        labels = {
            'city': 'المدينة'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 ترتيب المدن أبجديًا عربي
        self.fields['city'].queryset = self.fields['city'].queryset.order_by('name_ar')