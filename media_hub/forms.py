from django import forms
from .models import Comment


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('body',)
        widgets = {
            'body': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Add a comment…',
                'maxlength': 500,
                'autocomplete': 'off',
            }),
        }
        labels = {'body': ''}
