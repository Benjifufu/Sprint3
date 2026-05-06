"""
reporte/logic/logic_reporte.py - Logica de negocio de reportes.

Sin cambios funcionales respecto al original, pero:
- ConsumoCloud ahora SI esta declarado en reporte/models.py (estaba ausente).
- El router de BD (bitecoapp/db_router.py) dirige reads a `monitoring_replica`
  automaticamente para apps en MONITORING_APPS, asi que ya NO necesitamos
  el `.using('monitoring')` explicito (pero lo dejamos para que en caso de
  router desactivado siga funcionando).
"""
from collections import defaultdict
from decimal import Decimal

from reporte.models import ConsumoCloud


def get_reporte_mensual(empresa_id, mes, anio):
    """Devuelve queryset de ConsumoCloud para una empresa y periodo."""
    return ConsumoCloud.objects.using("monitoring_replica").filter(
        empresa_id=empresa_id,
        mes=mes,
        anio=anio,
    )


def get_total_por_proveedor(empresa_id, mes, anio):
    """
    Agregacion por proveedor. Hace SUM en Python; si la tabla crece, mover
    a aggregate(SUM) en SQL para hacerlo en un solo round-trip.
    """
    consumos = get_reporte_mensual(empresa_id, mes, anio)
    totales = defaultdict(Decimal)
    for c in consumos:
        totales[c.proveedor] += c.costo
    return {k: float(v) for k, v in totales.items()}
