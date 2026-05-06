"""
AuditMiddleware - ASR-14 (Integridad / Auditoria centralizada)

Implementacion exacta como la describe el informe Sprint 3, con la
mejora recomendada en "Acciones ante incumplimiento": envolver el
registro en try/except para que nunca falle silenciosamente.

Path: bitecoapp/audit_middleware.py
"""
import logging

logger = logging.getLogger("biteco.audit")


class AuditMiddleware:
    """
    Intercepta cada request a un endpoint auditable y crea un registro
    en la tabla RegistroAuditoria DESPUES de generar la respuesta
    (para capturar el status code real).
    """

    ACCIONES_AUDITABLES = (
        "/api/auth/login",
        "/api/auth/dashboard",
        "/api/reportes/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Auditar solo las rutas relevantes
        if any(request.path.startswith(p) for p in self.ACCIONES_AUDITABLES):
            self._registrar(request, response)
        return response

    def _registrar(self, request, response):
        """Tolerante a fallas: nunca rompe la respuesta al usuario."""
        try:
            from registroAuditoria.models import RegistroAuditoria

            user_obj = getattr(request, "user", None)
            usuario = (
                user_obj.username
                if user_obj is not None and getattr(user_obj, "is_authenticated", False)
                else "anonimo"
            )

            RegistroAuditoria.objects.create(
                accion=f"{request.method} {request.path}",
                usuario=usuario,
                ipOrigen=self._client_ip(request),
                detalles=f"Status: {response.status_code}",
                resultado="exitoso" if response.status_code < 400 else "fallido",
            )
        except Exception as e:  # noqa: BLE001
            # No bloquear nunca la respuesta — solo logearlo
            logger.exception("AuditMiddleware: fallo al registrar accion (%s)", e)

    @staticmethod
    def _client_ip(request) -> str:
        # Detras del ALB el IP real viene en X-Forwarded-For
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
