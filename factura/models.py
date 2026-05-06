from datetime import date

from django.db import models
from django.core.validators import MinValueValidator

from empresa.models import Empresa


class Factura(models.Model):
    numeroFactura = models.CharField(max_length=100)
    fecha = models.DateField(default=date.today)
    fechaVencimiento = models.DateField()

    # Bug fix: DecimalField requiere max_digits
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    impuestos = models.DecimalField(max_digits=14, decimal_places=2)
    total = models.DecimalField(max_digits=14, decimal_places=2)

    moneda = models.CharField(max_length=10)
    estado = models.CharField(max_length=50)
    conceptos = models.CharField(max_length=200)

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        verbose_name="empresa",
    )

    def __str__(self):
        return f"{self.numeroFactura} en {self.fecha}. Total: {self.total}{self.moneda}"

    class Meta:
        app_label = "factura"


class ItemFactura(models.Model):  # Bug fix: era models.model (minuscula)
    concepto = models.CharField(max_length=100)
    # Bug fix: IntegerField no acepta `min=1`. Se usa validators.
    cantidad = models.IntegerField(validators=[MinValueValidator(1)])
    precioUnitario = models.DecimalField(max_digits=14, decimal_places=2)
    # Bug fix: no se puede usar default=expr_de_otros_campos.
    # El subtotal se calcula en save() o en una propiedad.
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        verbose_name="factura",
        related_name="items",
    )

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precioUnitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.concepto} = {self.subtotal}"

    class Meta:
        app_label = "factura"
