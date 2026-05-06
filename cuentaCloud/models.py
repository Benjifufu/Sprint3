from django.db import models

# Bug fix: el original importaba Empresa desde alerta.models (incorrecto)
from empresa.models import Empresa


class CuentaCloud(models.Model):
    proveedor = models.CharField(max_length=100)
    accountId = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    credenciales = models.CharField(max_length=200)  # tokens/keys son largos
    fechaIntegracion = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=100)

    # Bug fix: ForeignKey sin on_delete falla en Django 4+
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        verbose_name="empresa",
    )

    def __str__(self):
        return f"{self.accountId}, Estado: {self.estado}"

    class Meta:
        app_label = "cuentaCloud"
