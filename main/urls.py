from django.conf.urls.static import static
from django.urls import path

from jinjaGenerator import settings
from main.views import load_template, render_template

urlpatterns = [
    path('template/load', load_template),
    path('template/render', render_template),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)