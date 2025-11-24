from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .forms import RegisterForm, ProfileEditForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash

def home(request):
    return redirect('login')
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('profile')  # куда ведём после логина
        else:
            messages.error(request, "Неверный логин или пароль")

    return render(request, 'accounts/login.html')
@login_required(login_url='login')
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})
@login_required(login_url='login')
def logout_view(request):
    logout(request)
    return redirect('login')
@login_required(login_url='login')
def profile_edit(request):
    if request.method == "POST":
        form = ProfileEditForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()

            # НЕ разлогиниваем пользователя, если он менял пароль
            if form.cleaned_data.get("new_password"):
                update_session_auth_hash(request, user)

            return redirect("profile")  # твоя страница профиля

    else:
        form = ProfileEditForm(request.user, initial={
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
        })

    return render(request, "accounts/profile_edit.html", {"form": form})