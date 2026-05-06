"""
reporte/models.py - Modelo Reporte (entidad de negocio) + ConsumoCloud
(tabla agregada por la que se filtra en logic_reporte.py).

Bug fixes:
- __str__ de Reporte usaba campos inexistentes (self.empresa_nombre, self.proveedor, ...)
- ForeignKey con SET_NULL sin null=True
- Se agrega ConsumoCloud que el codigo de negocio (get_total_por_proveedor) ya usa
  via reporte.logic.logic_reporte pero que NUNCA estaba declarado en models.
  Sin este modelo el `from reporte.models import ConsumoCloud` falla con
  ImportError al arrancar Django.
"""
from django.db import models

from empresa.models import Empresa
from proyecto.models import Proyecto
from usuario.models import Usuario


class Reporte(models.Model):
    titulo = models.CharField(max_length=100)
    tipo = models.CharField(max_length=100)
    fechaGeneracion = models.DateField(auto_now_add=True)
    periodoInicio = models.DateField()
    periodoFin = models.DateField()
    formato = models.CharField(max_length=50)

    # Relaciones (SET_NULL requiere null=True)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="usuario",
    )
    empresa = models.ForeignKey(
        Empresa, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="empresa",
    )
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="proyecto",
    )

    # Bug fix: el __str__ original usaba campos inexistentes
    def __str__(self):
        return f"{self.titulo} ({self.periodoInicio} -> {self.periodoFin})"

    class Meta:
        app_label = "reporte"


class ConsumoCloud(models.Model):
    """
    Tabla agregada de consumo. Hace match exacto con la migracion existente
    en `reporte/migrations/0001_initial.py` (no rompe la BD del equipo).

    La consume `reporte.logic.logic_reporte.get_total_por_proveedor`.

    Vive en la BD `monitoring` (vease bitecoapp/db_router.py) - el router
    se encarga de dirigir lecturas a la replica y escrituras al primary.
    """
    empresa_id = models.IntegerField(db_index=True)
    empresa_nombre = models.CharField(max_length=100)
    proveedor = models.CharField(max_length=20)        # AWS, GCP, Azure
    servicio = models.CharField(max_length=100)
    costo = models.DecimalField(max_digits=12, decimal_places=4)
    mes = models.IntegerField()
    anio = models.IntegerField()
    region = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        app_label = "reporte"
        # Indice clave para get_total_por_proveedor
        indexes = [
            models.Index(
                fields=["empresa_id", "anio", "mes"],
                name="idx_consumo_lookup",
            ),
        ]

    def __str__(self):
        return f"{self.empresa_nombre} {self.proveedor} {self.mes}/{self.anio}: {self.costo}"
