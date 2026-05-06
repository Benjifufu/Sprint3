"""
registroAuditoria/models.py - Modelo del trail de auditoria (ASR-14).

Reescrito segun la especificacion del informe Sprint 3:
- Sin FK a Empresa/Usuario por ahora (queda como string para evitar
  contamines con la BD monitoring).
- Typos corregidos (`models.models.` -> `models.`)
- `usuario` puede ser `null/blank` para los requests anonimos.
"""
from django.db import models


class RegistroAuditoria(models.Model):
    accion = models.CharField(max_length=200)
    usuario = models.CharField(max_length=100, null=True, blank=True)
    fecha = models.DateField(auto_now_add=True)
    ipOrigen = models.CharField(max_length=100)
    detalles = models.CharField(max_length=200)
    resultado = models.CharField(max_length=50)

    class Meta:
        app_label = "registroAuditoria"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["accion"], name="idx_audit_accion"),
            models.Index(fields=["resultado"], name="idx_audit_resultado"),
            models.Index(fields=["usuario"], name="idx_audit_usuario"),
        ]

    def __str__(self):
        return f"#{self.pk} {self.accion} ({self.resultado})"
