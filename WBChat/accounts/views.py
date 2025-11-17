from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .forms import RegisterForm
from django.contrib.auth.decorators import login_required

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