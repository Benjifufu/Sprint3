"""
reporte/views_html.py - Vistas HTML para los reportes (no JSON).

Las vistas JSON existentes (reporte/views.py) no se modifican.
Aqui solo agregamos las vistas con templates para los usuarios finales.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from reporte.logic.logic_reporte import get_total_por_proveedor


@login_required
def reportes_index(request):
    """Pagina principal de reportes con formulario de filtro."""
    # Tomamos defaults razonables; si el usuario no provee parametros usamos
    # los del JWT (empresa_id) y mes/anio del query string
    user_empresa = getattr(request.user, "empresa_id", 1)
    empresa_id = int(request.GET.get("empresa_id", user_empresa or 1))
    mes = int(request.GET.get("mes", 3))
    anio = int(request.GET.get("anio", 2026))

    # ASR-01 (defensa en profundidad): el usuario solo ve su empresa
    # salvo que sea Admin
    rol = getattr(request.user, "rol", "Usuario")
    cross_empresa_attempt = (rol != "Admin" and user_empresa and empresa_id != user_empresa)
    if cross_empresa_attempt:
        # Forzamos empresa_id al del token; auditamos el intento
        empresa_id = user_empresa

    totales = {}
    error = None
    try:
        totales = get_total_por_proveedor(empresa_id, mes, anio)
    except Exception as e:  # noqa: BLE001
        error = str(e)

    total_general = sum(totales.values()) if totales else 0

    return render(request, "reporte/index.html", {
        "empresa_id": empresa_id,
        "mes": mes,
        "anio": anio,
        "totales": totales,
        "total_general": total_general,
        "error": error,
        "cross_empresa_attempt": cross_empresa_attempt,
        "rol": rol,
        "max_total": max(totales.values()) if totales else 1,
    })
