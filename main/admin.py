from django.contrib import admin
from .models import Template

# Register your models here.
admin.site.site_header = "Template Management Admin"
admin.site.register(Template)