from django.contrib import admin
from .models import CustomUser, Record

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'is_staff','is_superuser']
    search_fields = ['username', 'email']   
    list_filter = ['role', 'is_staff', 'is_superuser']

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get("password") and not obj.password.startswith("pbkdf2_"):  
            obj.set_password(form.cleaned_data["password"])  
        super().save_model(request, obj, form, change)

class RecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'name', 'title','description', 'created_at']
    search_fields = ['name', 'title', 'description']    
    list_filter = ['created_at']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Record, RecordAdmin)