import datetime

from django.db import models

from planSuscripcion.models import PlanSuscripcion


class Empresa(models.Model):
    nombre = models.CharField(max_length=100)
    razonSocial = models.CharField(max_length=100)
    nit = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    fechaRegistro = models.DateField(default=datetime.date.today)
    estado = models.CharField(max_length=100)

    # Bug fix: SET_NULL requiere null=True
    plan_suscripcion = models.ForeignKey(
        PlanSuscripcion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    # Bug fix: el original usaba self.name (no existe; el campo es 'nombre')
    def __str__(self):
        return f"{self.nombre}, {self.nit}"

    class Meta:
        app_label = "empresa"
