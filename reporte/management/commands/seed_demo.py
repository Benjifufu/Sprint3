"""
Management command para sembrar datos demo.

Uso:
    python manage.py seed_demo

Genera:
- 1 PlanSuscripcion
- 3 Empresas (id 1, 2, 3)
- 3 ConsumoCloud por empresa con AWS/GCP/Azure para mes=3 anio=2026
- 1 superusuario admin/admin (solo en DEBUG=True)
"""
from decimal import Decimal
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

from empresa.models import Empresa
from planSuscripcion.models import PlanSuscripcion
from reporte.models import ConsumoCloud


PROVIDERS = [
    ("AWS", Decimal("12450.30"), Decimal("9870.20"), Decimal("4180.50")),
    ("GCP", Decimal("8230.50"), Decimal("6120.10"), Decimal("3210.00")),
    ("Azure", Decimal("4180.20"), Decimal("3450.80"), Decimal("1980.40")),
]


class Command(BaseCommand):
    help = "Siembra datos demo para BITE.co (Sprint 3)"

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. Plan
        plan, _ = PlanSuscripcion.objects.get_or_create(
            nombre="Pro",
            defaults={
                "descripcion": "Plan profesional",
                "precioMensual": Decimal("99.00"),
                "maxUsuarios": 50,
                "maxProyectos": 100,
                "soportePremium": True,
                "analisisAvanzado": True,
                "estado": "activo",
            },
        )
        self.stdout.write(f"Plan: {plan}")

        # 2. Empresas (1, 2, 3)
        empresas = []
        for i in range(1, 4):
            e, _ = Empresa.objects.update_or_create(
                id=i,
                defaults={
                    "nombre": f"Empresa Demo {i}",
                    "razonSocial": f"Demo {i} S.A.S.",
                    "nit": f"900{i:06d}-{i}",
                    "sector": "Tecnologia",
                    "estado": "activo",
                    "plan_suscripcion": plan,
                },
            )
            empresas.append(e)
            self.stdout.write(f"Empresa: {e}")

        # 3. ConsumoCloud para mes=3, anio=2026 (en BD monitoring)
        for idx, e in enumerate(empresas):
            for prov, *costos in PROVIDERS:
                costo = costos[idx]
                # Una fila por servicio (servicios genericos para demo)
                for servicio in ("compute", "storage", "network"):
                    ConsumoCloud.objects.using("monitoring").update_or_create(
                        empresa_id=e.id,
                        empresa_nombre=e.nombre,
                        proveedor=prov,
                        servicio=servicio,
                        mes=3,
                        anio=2026,
                        defaults={
                            "costo": costo / 3,
                            "region": "us-east-1",
                        },
                    )
        self.stdout.write(
            f"ConsumoCloud: {ConsumoCloud.objects.using('monitoring').count()} filas"
        )

        # 4. Admin
        if os.environ.get("DJANGO_DEBUG", "True").lower() == "true":
            User = get_user_model()
            if not User.objects.filter(username="admin").exists():
                u = User.objects.create_superuser(
                    username="admin",
                    email="admin@biteco.local",
                    password="admin",
                )
                u.rol = "Admin"
                u.empresa_id = 1
                u.save()
                self.stdout.write(self.style.SUCCESS("Superuser admin/admin creado (rol=Admin, empresa=1)"))

        self.stdout.write(self.style.SUCCESS("Seed completo."))
