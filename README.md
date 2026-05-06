# BITE.co — Sprint 3

Plataforma de optimización de costos cloud (AWS y GCP) para múltiples empresas.

## Stack

- **Backend**: Django 4.2 + PostgreSQL 16
- **Auth**: Auth0 OAuth2 + RBAC (via `social-auth-app-django`)
- **Auditoría**: middleware Django + `RegistroAuditoria` en PostgreSQL
- **Disponibilidad**: PostgreSQL Streaming Replication (Primary + Replica) + ALB Multi-AZ
- **UI**: Django templates + Tailwind CSS (CDN)

## ASRs cubiertos en Sprint 3

| ASR | Atributo | Mecanismo |
|---|---|---|
| **ASR-01** | Confidencialidad | Auth0 JWT validation + cross-empresa check + `@login_required` |
| **ASR-07** | Disponibilidad | ALB Multi-AZ + ASG min=2 + RDS Streaming Replication |
| **ASR-14** | Integridad | `AuditMiddleware` registra 100% de acciones en `RegistroAuditoria` |

## Estructura

```
.
├── bitecoapp/                  # Configuración central
│   ├── settings.py             # DBs, Auth0, middleware, AUTH_USER_MODEL
│   ├── urls.py                 # Rutas raíz (OAuth2 + APIs + HTML)
│   ├── audit_middleware.py     # ASR-14 - intercepta cada request auditable
│   └── db_router.py            # ASR-07 - reads → replica, writes → primary
│
├── usuario/                    # Modelo Usuario (extiende AbstractUser)
│   ├── models.py               # + rol, empresa_id (de claims JWT)
│   ├── pipeline.py             # post-login: extrae claims del JWT
│   └── views.py                # /api/auth/login, /api/auth/dashboard
│
├── reporte/
│   ├── models.py               # Reporte + ConsumoCloud
│   ├── logic/logic_reporte.py  # get_total_por_proveedor(empresa, mes, año)
│   ├── views.py                # API JSON con check de cross-empresa
│   ├── views_html.py           # Vista HTML con filtros
│   ├── urls.py                 # /api/reportes/...
│   ├── urls_html.py            # /reportes/
│   ├── templates/              # index.html
│   └── management/commands/seed_demo.py
│
├── registroAuditoria/
│   ├── models.py               # RegistroAuditoria (PK, accion, usuario, fecha, ip, detalles, resultado)
│   ├── views_html.py           # ASR Hub + tabla auditoria + JSON polling
│   ├── urls_html.py            # /asr-hub/
│   └── templates/registroAuditoria/{hub.html, auditoria.html}
│
├── alerta, cuentaCloud, empresa, factura, pago, planSuscripcion,
├── proyecto, recursoCloud, registroCosto/   ← apps de dominio (todos modelos arreglados)
│
├── templates/base/             # Layout global + home + dashboard
│   ├── base.html, home.html, dashboard.html
│
├── manage.py
├── requirements.txt
├── .env.example                # template de variables de entorno
└── .gitignore
```

## Quick start (desarrollo local)

```bash
# 1. Clonar y entrar
git clone <repo>
cd biteco

# 2. Virtualenv + dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Variables de entorno
cp .env.example .env
$EDITOR .env       # llena las credenciales reales

# 4. Postgres local (2 BDs)
sudo -u postgres psql <<EOF
CREATE USER biteco_user WITH PASSWORD 'biteco_pass';
CREATE DATABASE accounts_db OWNER biteco_user;
CREATE DATABASE monitoring_db OWNER biteco_user;
EOF

# 5. Migrar
python manage.py makemigrations
python manage.py migrate                          # accounts_db
python manage.py migrate --database=monitoring    # monitoring_db

# 6. Seed (datos demo + admin/admin)
python manage.py seed_demo

# 7. Correr
python manage.py runserver
# → http://localhost:8000
```

## URLs principales

| Ruta | Descripción | Auth |
|---|---|---|
| `/` | Landing publica | — |
| `/login/auth0` | Inicia OAuth2 con Auth0 | — |
| `/dashboard/` | Dashboard post-login | login |
| `/reportes/` | Reporte mensual (HTML) | login |
| `/asr-hub/` | **ASR Testing Hub** | login |
| `/asr-hub/auditoria/` | Tabla completa de auditoría | login |
| `/asr-hub/api/audit/` | Polling JSON de auditoría | login |
| `/admin/` | Django admin | superuser |
| `/api/auth/login` | API JSON login (JMeter) | — |
| `/api/reportes/mensual` | API JSON de reporte | JWT |
| `/health-check/` | Para el ALB | — |

## Documentación adicional

- **`docs/AWS_SETUP.md`** — Despliegue AWS paso a paso (RDS Streaming Replication, EC2, ALB)
- **`docs/AUTH0_SETUP.md`** — Configuración Auth0 (tenant, API, Action post-login, claims)
- **`docs/ASR_TESTING.md`** — Cómo validar cada ASR ante el profesor (CLI + JMeter + Hub)
- **`docs/BUG_FIXES.md`** — Lista de bugs corregidos en los modelos
