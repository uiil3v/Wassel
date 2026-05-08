
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
        ]

        widgets = {

            "comment": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "اكتب تجربتك..."
            }),
        }

        labels = {
            "comment": "التعليق",
        }

