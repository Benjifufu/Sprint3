"""
bitecoapp/urls.py - URLs raíz

Cambios respecto al original:
1. Agregadas rutas de social_django (/login/auth0/, /complete/auth0/, /logout/)
2. Agregada vista HTML del dashboard ASR (/asr-hub/)
3. Agregadas vistas HTML de reportes (/reportes/)
4. Las rutas API (/api/...) siguen funcionando igual
"""
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.urls import path, include
from django.http import HttpResponse


def health_check(request):
    """Endpoint para el ALB. NO auditado, NO autenticado."""
    return HttpResponse("OK", status=200)


def home(request):
    """Landing page: si no hay sesion -> login Auth0; si hay -> dashboard."""
    if request.user.is_authenticated:
        return redirect("/dashboard/")
    return render(request, "base/home.html")


@login_required
def dashboard_view(request):
    """Dashboard principal con links a reportes y al ASR Hub."""
    return render(request, "base/dashboard.html", {
        "user": request.user,
        "rol": getattr(request.user, "rol", "Usuario"),
        "empresa_id": getattr(request.user, "empresa_id", None),
    })


def custom_logout(request):
    logout(request)
    return redirect(
        f"https://dev-lhsedsl4b3teyxes.us.auth0.com/v2/logout"
        f"?client_id=UGG4z0BT5d2t3HcOt6LdVehrY5K5Qpkw"
        f"&returnTo=http://biteco-alb-49945009.us-east-1.elb.amazonaws.com"
    )


urlpatterns = [
    # Admin Django
    path("admin/", admin.site.urls),

    # Health check (para el ALB)
    path("health-check/", health_check, name="health_check"),

    # Auth0 OAuth2 (social_django)
    path("", include("social_django.urls", namespace="social")),
    path("logout/", custom_logout, name="logout"),

    # Vistas HTML
    path("", home, name="home"),
    path("dashboard/", dashboard_view, name="dashboard"),

    # Apps con sus templates HTML
    path("reportes/", include("reporte.urls_html")),
    path("asr-hub/", include("registroAuditoria.urls_html")),

    # APIs JSON (sin cambios — para JMeter y curl)
    path("api/auth/", include("usuario.urls")),
    path("api/reportes/", include("reporte.urls")),
]
