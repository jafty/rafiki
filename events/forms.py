from django import forms

class CertificationForm(forms.Form):
    sender_email = forms.EmailField(
        label="Votre adresse email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Votre email'}),
        required=True
    )
    attachment_id = forms.FileField(
        label="Joindre une pièce d'identité",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        required=True
    )
    attachment_pic = forms.FileField(
        label="Joindre une photo de vous avec votre pseudonyme écrit sur un papier",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        required=True
    )
