from django.urls import path
from . import views

urlpatterns = [
    path('mensual', views.reporte_mensual, name='reporte_mensual'),
]