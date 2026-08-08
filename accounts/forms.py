from django import forms
from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('display_name', 'bio', 'avatar', 'website')
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Display name'}),
            'bio': forms.Textarea(attrs={'class': 'input', 'rows': 3, 'placeholder': 'A short bio'}),
            'website': forms.URLInput(attrs={'class': 'input', 'placeholder': 'https://yoursite.com'}),
        }
