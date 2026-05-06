"""
reporte/urls_html.py - URLs para las vistas HTML (templates).

Se montan bajo /reportes/ en bitecoapp/urls.py.
Las URLs JSON siguen en reporte/urls.py bajo /api/reportes/.
"""
from django.urls import path
from . import views_html

urlpatterns = [
    path("", views_html.reportes_index, name="reportes_index"),
]
