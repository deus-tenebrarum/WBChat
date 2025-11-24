from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import password_validation
from .models import User

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'department', 'avatar', ]
class ProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(required=False, label="Имя")
    last_name = forms.CharField(required=False, label="Фамилия")
    email = forms.EmailField(required=False, label="Email")

    old_password = forms.CharField(required=False, widget=forms.PasswordInput, label="Старый пароль")
    new_password = forms.CharField(required=False, widget=forms.PasswordInput, label="Новый пароль")
    confirm_password = forms.CharField(required=False, widget=forms.PasswordInput, label="Подтверждение нового пароля")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()

        old = cleaned.get("old_password")
        new = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")

        # Если пользователь хочет сменить пароль — проверяем всё
        if old or new or confirm:
            if not old:
                raise forms.ValidationError("Введите старый пароль.")
            if not self.user.check_password(old):
                raise forms.ValidationError("Старый пароль неверный.")
            if not new:
                raise forms.ValidationError("Введите новый пароль.")
            if new != confirm:
                raise forms.ValidationError("Новые пароли не совпадают.")

        return cleaned

    def save(self, commit=True):
        user = self.user

        # Обновляем данные
        user.first_name = self.cleaned_data.get("first_name")
        user.last_name = self.cleaned_data.get("last_name")
        user.email = self.cleaned_data.get("email")

        # Если пароль изменяется
        new = self.cleaned_data.get("new_password")
        if new:
            user.set_password(new)

        if commit:
            user.save()

        return user