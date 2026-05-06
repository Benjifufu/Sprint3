from django.db import models


class PlanSuscripcion(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200)
    # Bug fix: DecimalField requiere max_digits
    precioMensual = models.DecimalField(max_digits=12, decimal_places=2)
    maxUsuarios = models.IntegerField()
    maxProyectos = models.IntegerField()
    soportePremium = models.BooleanField(default=False)
    analisisAvanzado = models.BooleanField(default=False)
    # Bug fix: CharField requiere max_length
    estado = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.nombre}: {self.descripcion}"

    class Meta:
        app_label = "planSuscripcion"
