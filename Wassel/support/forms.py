from django import forms
from .models import (
    SupportTicket,
    SupportMessage,
)


class SupportTicketForm(forms.ModelForm):

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["category"].choices = [
            ("", "اختر نوع الطلب"),
        ] + list(self.fields["category"].choices)

        # إذا المستخدم مسجل دخول
        if user and user.is_authenticated:

            self.fields["name"].widget.attrs["readonly"] = True
            self.fields["email"].widget.attrs["readonly"] = True
            self.fields["phone"].widget.attrs["readonly"] = True

    class Meta:
        model = SupportTicket

        fields = [
            "name",
            "email",
            "phone",
            "category",
            "subject",
            "message",
            "attachment",
        ]

        widgets = {

            "name": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "email": forms.EmailInput(attrs={
                "class": "form-control"
            }),

            "phone": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "category": forms.Select(attrs={
                "class": "form-select"
            }),

            "subject": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "message": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 6
            }),

            "attachment": forms.FileInput(attrs={
                "class": "form-control"
            }),
        }

        labels = {
            "name": "الاسم الكامل",
            "email": "البريد الإلكتروني",
            "phone": "رقم الجوال",
            "category": "نوع الطلب",
            "subject": "عنوان الطلب",
            "message": "تفاصيل الطلب",
            "attachment": "مرفق (اختياري)",
        }
        
        
class TicketTrackingForm(forms.Form):

    ticket_number = forms.CharField(
        label="رقم التذكرة",
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "TKT-000001"
        })
    )

    email = forms.EmailField(
        label="البريد الإلكتروني",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "example@email.com"
        })
    )
    
    
class SupportMessageForm(forms.ModelForm):

    class Meta:

        model = SupportMessage

        fields = [
            "message",
        ]

        widgets = {

            "message": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "اكتب رسالتك هنا..."
            }),

        }

        labels = {
            "message": "الرسالة",
        }

    def clean_message(self):

        message = self.cleaned_data["message"].strip()

        if not message:

            raise forms.ValidationError(
                "لا يمكن إرسال رسالة فارغة."
            )

        return message