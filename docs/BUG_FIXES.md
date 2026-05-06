# Bug Fixes — Sprint 3

Lista exhaustiva de los bugs corregidos en los modelos del repo
`App_Biteco-Camilo`. Todos verificados con `python manage.py check` (0 issues).

| App | Bug | Fix |
|---|---|---|
| `alerta` | `verbose_name=_("...")` sin `from django.utils.translation import gettext as _` | Reemplazado por string literal: `verbose_name="..."` |
| `alerta` | `ForeignKey(SET_NULL)` sin `null=True` (Django requiere `null=True` cuando `on_delete=SET_NULL`) | Agregado `null=True, blank=True` |
| `cuentaCloud` | `from alerta.models import Empresa` (apunta a la app incorrecta) | Cambiado a `from empresa.models import Empresa` |
| `cuentaCloud` | `models.ForeignKey(Empresa)` sin `on_delete` (obligatorio en Django ≥2.0) | Agregado `on_delete=models.CASCADE` |
| `empresa` | `__str__` usa `self.name` — el campo se llama `nombre` | Cambiado a `self.nombre` |
| `empresa` | `ForeignKey(plan_suscripcion, SET_NULL)` sin `null=True` | Agregado `null=True, blank=True` |
| `factura` | `class ItemFactura(models.model)` (m minúscula, no compila) | Corregido a `models.Model` |
| `factura` | `IntegerField(min=1)` — `min` no es un argumento válido | Reemplazado por `validators=[MinValueValidator(1)]` |
| `factura` | `default=cantidad*precioUnitario` — no se puede usar otro campo como default a nivel de declaración | Calculado en override de `save()` |
| `factura` | `DecimalField(decimal_places=2)` sin `max_digits` (obligatorio) | Agregado `max_digits=14` |
| `pago` | `comprobante = models.CharField()` sin `max_length` | Agregado `max_length=255, blank=True` |
| `pago` | `DecimalField` sin `max_digits` | Agregado `max_digits=14` |
| `planSuscripcion` | `estado = models.CharField()` sin `max_length` | Agregado `max_length=50` |
| `planSuscripcion` | `DecimalField` sin `max_digits` | Agregado `max_digits=12` |
| `proyecto` | `models.models.DecimalField(...)` (doble `models.` — no existe) | Corregido a `models.DecimalField` |
| `proyecto` | `DecimalField` sin `max_digits` | Agregado `max_digits=14` |
| `recursoCloud` | 2 ForeignKey con `SET_NULL` sin `null=True` | Agregado `null=True, blank=True` |
| `registroAuditoria` | `models.models.CharField` (3 veces) | Corregido a `models.CharField` |
| `registroAuditoria` | FK a Empresa/Usuario complican multi-DB | Removidas, `usuario` queda como String (alineado con el informe) |
| `registroCosto` | `class registroCosto` (minúscula — viola PEP-8) | Renombrado a `class RegistroCosto`, alias `registroCosto = RegistroCosto` para compat |
| `registroCosto` | `__str__` usa `self.accountId, self.estado` (ningún campo del modelo) | Reemplazado por uno coherente con los campos reales |
| `registroCosto` | `DecimalField` sin `max_digits` | Agregado `max_digits=14` |
| `reporte` | `__str__` usa `self.empresa_nombre, self.proveedor, self.mes, self.anio` (ningún campo del modelo Reporte) | Reemplazado por uno coherente |
| `reporte` | 3 ForeignKey con `SET_NULL` sin `null=True` | Agregado `null=True, blank=True` |
| `reporte` | `ConsumoCloud` se importaba en `logic_reporte.py` pero NUNCA estaba declarado en `models.py` (la migración 0001_initial sí la tenía como `CreateModel` huérfano) | Declarado el modelo `ConsumoCloud` en `models.py` matching exacto con la migración existente |
| `usuario` | `rol = models.CharField()` sin `max_length` | Agregado `max_length=50, default="Usuario"` |
| `usuario` | Modelo no extendía `AbstractUser` — el `Auth0Middleware` necesita `is_authenticated`, `username`, etc. | Cambiado a `class Usuario(AbstractUser)`. Agregado `AUTH_USER_MODEL` en settings |
| `usuario` | Faltaban los campos `rol` y `empresa_id` que el JWT de Auth0 inyecta via Action post-login | Agregados como campos del modelo |

## Verificación

```bash
# 0 issues
$ python manage.py check
System check identified no issues (0 silenced).

# Migraciones se generan limpias
$ python manage.py makemigrations
Migrations for 'planSuscripcion':  ...
Migrations for 'empresa':          ...
Migrations for 'usuario':          ...
... (14 apps)

# Migrate funciona en las 2 BDs
$ python manage.py migrate
$ python manage.py migrate --database=monitoring

# El comando seed_demo crea datos demo
$ python manage.py seed_demo
Plan: Pro: Plan profesional
Empresa: Empresa Demo 1, ...
ConsumoCloud: 27 filas
Superuser admin/admin creado (rol=Admin, empresa=1)
```

## Migraciones del repo original

El repo `App_Biteco-Camilo` venía con 2 migraciones desincronizadas
(`usuario/migrations/0001_initial.py` declaraba un modelo `Empresa` que
no corresponde a la app, y `reporte/migrations/0001_initial.py` con
`ConsumoCloud` que nunca estaba declarado en `models.py`).

**Solución**: borrar todas las migraciones existentes y dejar que
`makemigrations` las regenere desde los modelos arreglados.

```bash
find . -path "*/migrations/0*.py" -delete
python manage.py makemigrations
```

Las nuevas migraciones SÍ se commitean al repo (convención Django).
