from django.contrib import admin 
from .models import User

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('fullName', 'email', 'is_staff', 'is_verified')
    list_filter = ('is_verified', 'is_staff')
    search_field = ('fullName', 'email')
    
    def verifyUser(self, request, queryset):
        queryset.update(isverified=True)
        self.message_user(request, "Selected users has been verified.")
        
    def unverifyUser(self, request, queryset):
        queryset.update(is_verified=False)
        self.message(request, "Selected users has been unverified.")
    
    actions = ['verify_user', 'unverify_user']