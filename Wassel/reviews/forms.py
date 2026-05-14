from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):

    rating = forms.IntegerField(
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Review

        fields = [
            "rating",
            "comment",
            "is_anonymous",
        ]

        widgets = {

            "comment": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "اكتب تجربتك..."
            }),

            "is_anonymous": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }

        labels = {
            "comment": "التعليق",
            "is_anonymous": "إخفاء اسمي",
        }