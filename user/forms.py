from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Record

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not (user and user.is_authenticated and user.role == 'admin'):
            self.fields['role'].choices = [('employee', 'Employee')]
        else:
            self.fields['role'].choices = [('employee', 'Employee'), ('admin', 'Admin')]

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()