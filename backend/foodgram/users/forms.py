from django.contrib.auth.hashers import make_password
from django.forms import ModelForm


class MyUserForm(ModelForm):
    class Meta:
        fields = [
            'email',
            'username',
            'password',
            'first_name',
            'last_name',
            'is_superuser',
            'is_active'

        ]

    def clean_password(self):
        password = make_password(self.cleaned_data['password'])
        return password
