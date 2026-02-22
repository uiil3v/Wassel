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
            'username',
            'first_name',
            'last_name',
            'email',
            'phone',
            'role',
            'password1',
            'password2'
        ]

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        # إزالة المسافات
        phone = phone.replace(" ", "")

        # لو المستخدم كتب 05XXXXXXXX نحوله إلى +9665XXXXXXXX
        if phone.startswith("05") and len(phone) == 10:
            phone = "+966" + phone[1:]

        # تحقق من الصيغة السعودية الدولية
        if not re.match(r'^\+9665\d{8}$', phone):
            raise forms.ValidationError("رقم الجوال غير صحيح. استخدم 05XXXXXXXX")

        return phone