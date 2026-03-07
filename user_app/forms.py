from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    """Форма входа по email"""
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control mystic-input',
            'placeholder': 'Введите ваш email',
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control mystic-input',
            'placeholder': 'Введите пароль'
        })
    )


class MysticUserCreationForm(UserCreationForm):
    """Форма регистрации"""
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control mystic-input',
            'placeholder': 'Ваш волшебный email'
        })
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control mystic-input',
            'placeholder': 'Создайте сильный пароль'
        })
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control mystic-input',
            'placeholder': 'Повторите пароль'
        })
    )
    first_name = forms.CharField(
        label='Имя',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control mystic-input',
            'placeholder': 'Ваше магическое имя'
        })
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'password1', 'password2')


class ProfileUpdateForm(forms.ModelForm):
    """Форма редактирования профиля"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'birth_date', 'birth_time']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control mystic-input', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control mystic-input', 'placeholder': 'Фамилия'}),
            'email': forms.EmailInput(attrs={'class': 'form-control mystic-input', 'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control mystic-input', 'placeholder': 'Телефон'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control mystic-input', 'type': 'date'}),
            'birth_time': forms.TimeInput(attrs={'class': 'form-control mystic-input', 'type': 'time'}),
        }