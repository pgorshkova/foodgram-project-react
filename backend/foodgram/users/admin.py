from django.contrib import admin

from .forms import MyUserForm
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username']
    search_fields = ['email', 'username']
    list_filter = ['email', 'username']
    form = MyUserForm
