"""
reporte/views.py - API JSON de reportes.

Cambios respecto al original:
1. Si el usuario no esta autenticado (no hay sesion Django), retorna 401.
2. Si el usuario autenticado intenta acceder a otra empresa que la del JWT,
   retorna 403 (cumpliendo ASR-01 escenario 4 del informe).
3. La auditoria se hace automaticamente en AuditMiddleware - no se duplica aqui.
"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from reporte.logic.logic_reporte import get_total_por_proveedor


@csrf_exempt
def reporte_mensual(request):
    if request.method != "GET":
        return JsonResponse({"error": "Metodo no permitido"}, status=405)

    # === ASR-01: Autenticación ===
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "Unauthorized", "reason": "Authentication required"},
            status=401,
        )

    # === Parametros ===
    try:
        empresa_id_param = int(request.GET.get("empresa_id", 1))
        mes = int(request.GET.get("mes", 3))
        anio = int(request.GET.get("anio", 2026))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Parametros invalidos"}, status=400)

    # === ASR-01: Acceso cruzado entre empresas ===
    user_empresa = getattr(request.user, "empresa_id", None)
    user_rol = getattr(request.user, "rol", "Usuario")

    if user_rol != "Admin" and user_empresa is not None and empresa_id_param != user_empresa:
        return JsonResponse(
            {
                "error": "Forbidden",
                "reason": "Cross-empresa access blocked",
                "your_empresa": user_empresa,
                "requested": empresa_id_param,
            },
            status=403,
        )

    # === Lógica de negocio ===
    totales = get_total_por_proveedor(empresa_id_param, mes, anio)

    return JsonResponse({
        "empresa_id": empresa_id_param,
        "mes": mes,
        "anio": anio,
        "total_por_proveedor": totales,
    })
