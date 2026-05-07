"""
registroAuditoria/views_html.py - Vistas HTML del ASR Testing Hub.

3 paginas:
  /asr-hub/             -> dashboard de pruebas (HTML + JS llamando a las APIs)
  /asr-hub/auditoria/   -> tabla de RegistroAuditoria
  /asr-hub/api/audit/   -> JSON endpoint para que el dashboard polee
"""
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from registroAuditoria.models import RegistroAuditoria


@login_required
def hub(request):
    """Dashboard principal del ASR Hub - solo Admin."""
    role = getattr(request.user, 'rol', 'Usuario')
    if role != 'Admin':
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("No tienes permisos para acceder a esta página.")
    qs = RegistroAuditoria.objects.all()
    total = qs.count()
    fallidos = qs.filter(resultado="fallido").count()
    return render(request, "registroAuditoria/hub.html", {
        "total_eventos": total,
        "total_fallidos": fallidos,
    })


@login_required
def auditoria_table(request):
    """Tabla completa de auditoria con filtros."""
    accion = request.GET.get("accion", "")
    resultado = request.GET.get("resultado", "")
    usuario = request.GET.get("usuario", "")

    qs = RegistroAuditoria.objects.all().order_by("-id")
    if accion:
        qs = qs.filter(accion__icontains=accion)
    if resultado:
        qs = qs.filter(resultado=resultado)
    if usuario:
        qs = qs.filter(usuario__icontains=usuario)

    eventos = qs[:100]  # ultimos 100

    return render(request, "registroAuditoria/auditoria.html", {
        "eventos": eventos,
        "filtros": {"accion": accion, "resultado": resultado, "usuario": usuario},
        "total": qs.count(),
    })


@login_required
def auditoria_json(request):
    """Endpoint JSON para que el dashboard polee en vivo."""
    qs = RegistroAuditoria.objects.all().order_by("-id")[:50]
    eventos = [
        {
            "id": e.id,
            "fecha": e.fecha.isoformat() if e.fecha else None,
            "accion": e.accion,
            "usuario": e.usuario or "anonimo",
            "ip": e.ipOrigen or "-",
            "detalles": e.detalles or "",
            "resultado": e.resultado or "",
        }
        for e in qs
    ]
    # Stats
    total = RegistroAuditoria.objects.count()
    fallidos = RegistroAuditoria.objects.filter(resultado="fallido").count()
    return JsonResponse({
        "stats": {"total": total, "fallidos": fallidos},
        "eventos": eventos,
    })
