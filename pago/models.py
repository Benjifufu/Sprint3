from django.db import models

from empresa.models import Empresa
from factura.models import Factura


class Pago(models.Model):
    fecha = models.DateField()
    # Bug fix: DecimalField requiere max_digits
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    moneda = models.CharField(max_length=10)
    metodoPago = models.CharField(max_length=50)
    referencia = models.CharField(max_length=100)
    estado = models.CharField(max_length=50)
    # Bug fix: CharField requiere max_length
    comprobante = models.CharField(max_length=255, blank=True)

    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        verbose_name="factura",
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        verbose_name="empresa",
    )

    def __str__(self):
        return f"{self.monto}{self.moneda} en {self.fecha}. Estado: {self.estado}"

    class Meta:
        app_label = "pago"
