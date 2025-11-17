from django.contrib import admin
from .models import User

@admin.register(User)
class AccountsAdmin(admin.ModelAdmin):
    list_display = ('username', 'email')
    search_fields = ('username', 'email')
# Register your models here.
