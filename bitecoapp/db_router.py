"""
bitecoapp/db_router.py - Routes reads to monitoring_replica, writes to monitoring.

Implementa la separacion lectura/escritura del ASR-07 (Streaming Replication).

Para activarlo, agrega a settings.py:

    DATABASE_ROUTERS = ["bitecoapp.db_router.MonitoringReplicaRouter"]
"""

# Apps cuyos modelos viven en la BD monitoring (no accounts_db)
MONITORING_APPS = {
    "alerta",
    "cuentaCloud",
    "factura",
    "pago",
    "proyecto",
    "recursoCloud",
    "registroCosto",
    "reporte",
    # registroAuditoria queda en accounts_db (la BD default) por simplicidad
}


class MonitoringReplicaRouter:
    """
    Reads -> monitoring_replica
    Writes -> monitoring
    Para todo lo demas (auth, admin, registroAuditoria) -> default (accounts_db)
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label in MONITORING_APPS:
            return "monitoring_replica"
        return None  # default

    def db_for_write(self, model, **hints):
        if model._meta.app_label in MONITORING_APPS:
            return "monitoring"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Permitir relaciones entre objetos que viven en monitoring* y default
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Migrar las apps de monitoring solo a la BD primary
        if app_label in MONITORING_APPS:
            return db == "monitoring"
        # Default: solo migra al default
        if db in ("monitoring", "monitoring_replica"):
            return False
        return db == "default"
