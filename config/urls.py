from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("explorer.urls")),
]

# manage.py runserver wires this up automatically (only in DEBUG), but
# `manage.py serve` (waitress) talks to the WSGI app directly and needs
# it added explicitly to still serve CSS/JS/piece images.
urlpatterns += staticfiles_urlpatterns()
