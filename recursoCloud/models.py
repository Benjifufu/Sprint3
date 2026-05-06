from django.db import models

from cuentaCloud.models import CuentaCloud
from proyecto.models import Proyecto


class RecursoCloud(models.Model):
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    tamano = models.CharField(max_length=100)
    estado = models.CharField(max_length=50)
    fechaCreacion = models.DateField(auto_now_add=True)
    etiquetas = models.CharField(max_length=200, blank=True)

    # Bug fix: SET_NULL requiere null=True
    cuentaCloud = models.ForeignKey(
        CuentaCloud,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="cuentaCloud",
    )
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="proyecto",
    )

    def __str__(self):
        return f"{self.nombre} creado en {self.fechaCreacion}"

    class Meta:
        app_label = "recursoCloud"
