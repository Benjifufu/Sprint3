# ASR Testing — Validación ante el profesor

Cómo demostrar que cada ASR del Sprint 3 se cumple. Hay 3 maneras de
validar: **CLI con curl**, **JMeter** (siguiendo el informe), y el
**ASR Testing Hub** (`/asr-hub/` en la UI).

**Tiempo total**: ~15 min para los 3 experimentos.

---

## Pre-requisitos

```bash
# Variables que vas a reusar
export ALB=http://TU-ALB-DNS                      # de docs/AWS_SETUP.md
export AUTH0_DOMAIN=biteco-dev.us.auth0.com       # de docs/AUTH0_SETUP.md
export M2M_CLIENT_ID=xxx
export M2M_CLIENT_SECRET=yyy

# Obtener un token Auth0 valido
TOKEN=$(curl -s -X POST https://$AUTH0_DOMAIN/oauth/token \
  -H "content-type: application/json" \
  -d "{\"client_id\":\"$M2M_CLIENT_ID\",\"client_secret\":\"$M2M_CLIENT_SECRET\",\"audience\":\"https://api.biteco.co\",\"grant_type\":\"client_credentials\"}" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
echo "Token: ${TOKEN:0:40}..."
```

---

## ASR-01 — Bloqueo de acceso no autorizado

### Vía CLI

```bash
# Test 1: sin token
curl -i $ALB/api/reportes/mensual?empresa_id=1
# Esperado: HTTP/1.1 401 Unauthorized
#           {"error":"Unauthorized","reason":"Authentication required"}

# Test 2: con token invalido
curl -i -H "Authorization: Bearer fake.invalid.signature" \
  $ALB/api/reportes/mensual?empresa_id=1
# Esperado: HTTP/1.1 401 Unauthorized

# Test 3: con token valido (deberia funcionar)
# Para esto NECESITAS un token de un usuario humano (no M2M).
# Loguea via browser y copia la sessionid:
#   open $ALB/login/auth0
#   browser DevTools → Application → Cookies → sessionid
COOKIE="sessionid=TU-SESSION-ID-AQUI"
curl -i -H "Cookie: $COOKIE" \
  $ALB/api/reportes/mensual?empresa_id=1&mes=3&anio=2026
# Esperado: HTTP/1.1 200 OK
#           {"empresa_id":1,"mes":3,"anio":2026,"total_por_proveedor":{...}}

# Test 4: cross-empresa (login como user de empresa=1, request a empresa=99)
curl -i -H "Cookie: $COOKIE" \
  "$ALB/api/reportes/mensual?empresa_id=99&mes=3&anio=2026"
# Esperado: HTTP/1.1 403 Forbidden
#           {"error":"Forbidden","reason":"Cross-empresa access blocked",...}
```

### Vía el ASR Hub (más visual para mostrar al profesor)

1. Abrir `$ALB/asr-hub/` (loguea primero con admin/admin si es local, o con Auth0 en prod)
2. En la sección **ASR-01**, click en cada uno de los 4 botones:
   - **Sin token** → terminal muestra `HTTP 401`
   - **Token invalido** → `HTTP 401`
   - **25 requests rapidos** → 25 × `HTTP 401` (carga)
   - **Acceso cruzado entre empresas** → `HTTP 403`

### Vía JMeter (plan del informe Sprint 3)

```
Thread Group: Acceso sin autenticación
  Threads: 100
  Ramp-up: 10s
  Duración: 60s
  HTTP Request: GET /api/reportes/mensual?empresa_id=1&mes=3&anio=2026
  (sin headers de auth)

Listener: Aggregate Report
  Esperado: 100% Error% (porque debe retornar 401)
```

### Verificar que todo quedó auditado

```sql
-- En la BD accounts_db
SELECT accion, usuario, ipOrigen, detalles, resultado, COUNT(*)
FROM registroauditoria_registroauditoria
WHERE accion LIKE '%/api/reportes/%'
GROUP BY 1, 2, 3, 4, 5
ORDER BY COUNT(*) DESC;
```

**Criterio de éxito ASR-01**: 100% de requests sin auth → 401/403 + entrada en `RegistroAuditoria`.

---

## ASR-07 — Recuperación automática

### Setup

Necesitas 2 terminales abiertas.

### Terminal A: polling continuo

```bash
while true; do
  printf "$(date +%H:%M:%S) → "
  curl -s -o /dev/null -w "HTTP %{http_code} (%{time_total}s)\n" $ALB/health-check/
  sleep 1
done
```

### Terminal B: matar una EC2 Web

> **Nota**: el informe del equipo NO usa Auto Scaling Group, sino 2 EC2
> directamente registradas en el target group. El experimento se hace
> "tumbando" Django (no terminando la VM completa) para simular falla
> parcial.

```bash
# Listar las EC2 Web
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=biteco-web-*" "Name=instance-state-name,Values=running" \
  --query 'Reservations[*].Instances[*].[InstanceId,PublicIpAddress,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# Conectarse a Web 1 y matar gunicorn
WEB1_IP=...   # del listado de arriba
ssh -i TU_KEY.pem ubuntu@$WEB1_IP "sudo systemctl stop biteco"
```

### Lo que debes mostrar al profesor

En **Terminal A** debes ver:

```
14:32:01 → HTTP 200 (0.04s)
14:32:02 → HTTP 200 (0.04s)
14:32:03 → HTTP 200 (0.04s)   ← matas Web1 aqui
14:32:04 → HTTP 200 (0.05s)   ← ALB rutea solo a Web2 (pero todavia
14:32:05 → HTTP 200 (0.04s)     no marca Web1 unhealthy)
...
14:32:31 → HTTP 200 (0.04s)   ← health check #1 fallo (timeout 5s)
14:32:33 → HTTP 200 (0.04s)
14:32:35 → HTTP 200 (0.04s)
14:33:01 → HTTP 200 (0.04s)   ← ALB confirma Web1 unhealthy (despues
                                de 2 fallas) y la saca del pool
                                permanentemente. Solo Web2 sirve.
```

**El polling NUNCA muestra HTTP 5xx ni timeout** → ASR-07 cumplido.

### Verificar en la consola AWS

- EC2 → Target Groups → `biteco-tg` → pestaña Targets:
  - Web 1: `unhealthy`
  - Web 2: `healthy`

### Recuperación manual (para volver al estado original)

```bash
ssh -i TU_KEY.pem ubuntu@$WEB1_IP "sudo systemctl start biteco"
# En ~30s, el ALB la marca healthy de nuevo
```

### Vía JMeter (plan del informe)

```
Thread Group: Carga sostenida
  Threads: 500
  Ramp-up: 10s
  Duración: 5 min
  HTTP Request: GET /health-check/

Mientras corre, en otra terminal: stop de gunicorn en una EC2
Esperado en JMeter: 0% Error% durante toda la prueba
```

**Criterio de éxito ASR-07**: 0% de errores en JMeter durante los 5 minutos, incluyendo el momento de la falla.

---

## ASR-14 — Auditoría 100%

### Setup: limpiar tabla antes de la prueba

```bash
ssh ubuntu@$ACCOUNTS_IP "sudo -u postgres psql accounts_db -c \
  'TRUNCATE TABLE registroauditoria_registroauditoria;'"
```

### Vía CLI

```bash
# Disparar 100 requests al endpoint auditable
for i in $(seq 1 100); do
  curl -s -o /dev/null $ALB/api/auth/login -X POST \
    -d '{"username":"x","password":"y"}' \
    -H "Content-Type: application/json"
done

# Contar registros
ssh ubuntu@$ACCOUNTS_IP "sudo -u postgres psql accounts_db -c \
  'SELECT COUNT(*) FROM registroauditoria_registroauditoria;'"
# Esperado: count=100
```

### Vía JMeter (plan del informe Sprint 3)

3 escenarios separados, cada uno con 12,000 requests:

| Escenario | Endpoint | Esperado en BD |
|---|---|---|
| Logins exitosos | POST /api/auth/login (creds validas) | 12,000 con resultado='exitoso' |
| Logins fallidos | POST /api/auth/login (creds invalidas) | 12,000 con resultado='fallido' |
| Consultas de reportes | GET /api/reportes/mensual (con token) | 12,000 con accion='GET /api/reportes/mensual' |

Después de cada escenario:

```sql
-- Conteo por accion y resultado
SELECT accion, resultado, COUNT(*)
FROM registroauditoria_registroauditoria
GROUP BY accion, resultado;

-- Total general
SELECT COUNT(*) FROM registroauditoria_registroauditoria;

-- Limpiar entre escenarios
DELETE FROM registroauditoria_registroauditoria;
```

### Vía el ASR Hub

Abrir `$ALB/asr-hub/` y observar la tabla del fondo (sección ASR-14).
Cada vez que disparas una prueba ASR-01 desde el Hub, aparece una nueva
fila ahí en menos de 3s (polling).

**Criterio de éxito ASR-14**: `COUNT(*)` en BD == número de requests enviados.

---

## Resumen — checklist final

Antes de la demo, verifica:

- [ ] `curl $ALB/health-check/` → `200 OK`
- [ ] `curl $ALB/api/reportes/mensual` (sin auth) → `401`
- [ ] Login interactivo en `$ALB/login/auth0` funciona
- [ ] Después del login, `$ALB/dashboard/` muestra el rol y empresa_id correctos
- [ ] El ASR Hub muestra los 3 KPIs y la tabla viva
- [ ] Tienes el comando para tumbar Web1 listo (terminal abierta + key SSH)
- [ ] Tabla `registroauditoria_registroauditoria` no está vacía pero tampoco saturada
- [ ] Tienes `psql` listo para hacer `SELECT COUNT(*)` después de los tests

---

## Plan de presentación al profesor (5 minutos)

1. **(30s) Mostrar el dashboard** `$ALB/dashboard/` — "esta es la app, autenticada con Auth0"
2. **(60s) ASR-01** desde el Hub: click en los 4 botones, mostrar terminal con 401/403, mostrar tabla de auditoría que se actualiza
3. **(90s) ASR-07** chaos:
   - Iniciar polling en terminal A
   - Matar Web1 desde terminal B
   - "Mientras Web1 está caída, el polling sigue verde"
   - Mostrar AWS Console → Target Group para confirmar
4. **(60s) ASR-14**: query SQL `SELECT COUNT(*)` antes y después de un burst de requests, confirmar que match
5. **(30s) Q&A**: "el AuditMiddleware está en `bitecoapp/audit_middleware.py`, lo activé en MIDDLEWARE en settings"
