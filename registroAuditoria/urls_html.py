"""
registroAuditoria/urls_html.py - Rutas del ASR Testing Hub.
"""
from django.urls import path
from . import views_html

urlpatterns = [
    path("", views_html.hub, name="asr_hub"),
    path("auditoria/", views_html.auditoria_table, name="auditoria_table"),
    path("api/audit/", views_html.auditoria_json, name="auditoria_json"),
]
