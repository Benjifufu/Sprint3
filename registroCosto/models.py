from django.db import models

from proyecto.models import Proyecto
from recursoCloud.models import RecursoCloud


# Bug fix: clase con minuscula -> RegistroCosto (PascalCase es la convencion)
class RegistroCosto(models.Model):
    fecha = models.DateField(auto_now_add=True)
    # Bug fix: DecimalField requiere max_digits
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    moneda = models.CharField(max_length=10)
    servicioCloud = models.CharField(max_length=100)
    unidadMedida = models.CharField(max_length=50)
    cantidad = models.DecimalField(max_digits=14, decimal_places=2)

    # Bug fix: SET_NULL requiere null=True
    recursoCloud = models.ForeignKey(
        RecursoCloud,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="recursoCloud",
    )
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="proyecto",
    )

    # Bug fix: el __str__ original referenciaba campos inexistentes
    # (self.accountId, self.estado). Reemplazado por algo coherente.
    def __str__(self):
        return f"{self.servicioCloud} - {self.monto}{self.moneda} ({self.fecha})"

    class Meta:
        app_label = "registroCosto"


# Alias para no romper imports antiguos: from registroCosto.models import registroCosto
registroCosto = RegistroCosto
