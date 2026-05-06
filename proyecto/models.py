from django.db import models

from empresa.models import Empresa
from usuario.models import Usuario


class Proyecto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200)
    # Bug fix: era models.models.DecimalField (doble) + faltaba max_digits
    presupuestoMensual = models.DecimalField(max_digits=14, decimal_places=2)
    fechaInicio = models.DateField()
    fechaFin = models.DateField()
    estado = models.CharField(max_length=50)

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        verbose_name="empresa",
    )
    usuarios = models.ManyToManyField(Usuario, blank=True)

    def __str__(self):
        return f"{self.nombre}, Estado: {self.estado}"

    class Meta:
        app_label = "proyecto"
