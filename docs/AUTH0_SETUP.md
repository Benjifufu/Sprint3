# Auth0 Setup — Configuración paso a paso

Configura Auth0 para que actúe como IdP de BITE.co (ASR-01 — Confidencialidad).

**Tiempo estimado**: 15 min.

---

## 0. Crear cuenta + tenant (solo la primera vez)

1. Ir a https://auth0.com → "Sign up" (gratis hasta 7,500 MAU)
2. Crear tenant: ej. `biteco-dev` → región US o EU
3. Anota tu **Domain**: `biteco-dev.us.auth0.com`

---

## 1. Crear la API

Esta es la API que protege tus endpoints.

1. Dashboard → **Applications → APIs → + Create API**
2. Configurar:
   - **Name**: `BITE.co API`
   - **Identifier (audience)**: `https://api.biteco.co`
   - **Signing Algorithm**: `RS256`
3. Click **Create**

### 1.1 Definir permisos (scopes)

En la pestaña **Permissions** del API, agrega:

| Permission | Description |
|---|---|
| `read:reportes` | Ver reportes mensuales |
| `write:cuentas` | Crear/editar cuentas cloud |
| `admin:full` | Acceso total (admin) |

### 1.2 Activar RBAC

En la pestaña **Settings** del API:
- ✅ **Enable RBAC**
- ✅ **Add Permissions in the Access Token**

Esto hace que los permisos del rol viajen en el JWT.

---

## 2. Crear la Application (Regular Web App)

Esta es la aplicación Django que hace login OAuth2.

1. Dashboard → **Applications → Applications → + Create Application**
2. Tipo: **Regular Web Applications**
3. Name: `BITE.co Django Web`
4. Click **Create** → escoger Django como tech (opcional)

### 2.1 Configurar callbacks

En la pestaña **Settings**:

| Campo | Valor (desarrollo) | Valor (produccion) |
|---|---|---|
| **Allowed Callback URLs** | `http://localhost:8000/complete/auth0` | `http://TU-ALB-DNS/complete/auth0` |
| **Allowed Logout URLs** | `http://localhost:8000` | `http://TU-ALB-DNS` |
| **Allowed Web Origins** | `http://localhost:8000` | `http://TU-ALB-DNS` |

> Si tienes los dos entornos, separa con coma: `http://localhost:8000/complete/auth0,http://TU-ALB-DNS/complete/auth0`

Save Changes.

### 2.2 Anotar credenciales

En **Settings** copia:
- **Domain**: `biteco-dev.us.auth0.com`
- **Client ID**: `xxxxxxxxxxxxxxxxx`
- **Client Secret**: `yyyyyyyyyyyyyyyyy`

Las pondrás en el `.env`:

```bash
AUTH0_DOMAIN=biteco-dev.us.auth0.com
AUTH0_CLIENT_ID=xxxxxxxxxxxxxxxxx
AUTH0_CLIENT_SECRET=yyyyyyyyyyyyyyyyy
```

---

## 3. Crear roles + asignarlos a permisos

1. Dashboard → **User Management → Roles → + Create Role**
2. Crear 2 roles:

| Role name | Description | Permissions |
|---|---|---|
| `Admin` | Administrador con acceso total | `read:reportes`, `write:cuentas`, `admin:full` |
| `Usuario` | Usuario regular de empresa | `read:reportes` |

Para cada rol, en la pestaña **Permissions** clickea **Add Permissions**, selecciona la API `BITE.co API` y marca los permisos correspondientes.

---

## 4. Crear usuarios de prueba

1. **User Management → Users → + Create User**
2. Crear al menos 2 usuarios:

| Email | Password | Rol | empresa_id |
|---|---|---|---|
| `admin@biteco.local` | (genera una) | `Admin` | 1 |
| `user@empresa1.com` | (genera una) | `Usuario` | 1 |
| `user@empresa2.com` | (genera una) | `Usuario` | 2 |

### 4.1 Asignar rol a cada usuario

Click en cada usuario → pestaña **Roles** → **Assign Roles** → seleccionar.

### 4.2 Agregar `empresa_id` como app_metadata

Click en cada usuario → pestaña **Details** → busca **app_metadata** → escribe:

```json
{
  "rol": "Admin",
  "empresa_id": 1
}
```

(Cambia `rol` y `empresa_id` por los del usuario)

> **`app_metadata`** vs `user_metadata`: app_metadata solo lo puedes editar tú (admin), user_metadata lo puede editar el propio usuario. Para datos de seguridad como rol/empresa siempre usa **app_metadata**.

---

## 5. Crear la Action post-login

Esta es **la pieza más importante**. La Action inyecta `rol` y `empresa_id` como claims customizados del JWT.

1. Dashboard → **Actions → Library → + Create Action**
2. Tipo: **Custom**
3. Name: `Inject role and empresa_id`
4. Trigger: **Login / Post Login**
5. Runtime: **Node 22 (Recommended)**
6. Click **Create**

### 5.1 Pegar este código

```javascript
/**
 * Action post-login: inyecta `rol` y `empresa_id` desde app_metadata
 * en el id_token + access_token, como claims customizados.
 *
 * El namespace `https://biteco.co/` es obligatorio en Auth0 para claims
 * customizados (no se aceptan claims sin namespace).
 */
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://biteco.co';
  const rol = event.user.app_metadata?.rol || 'Usuario';
  const empresaId = event.user.app_metadata?.empresa_id || 1;

  // ID Token (lo lee social-auth-app-django via /userinfo)
  api.idToken.setCustomClaim(`${namespace}/rol`, rol);
  api.idToken.setCustomClaim(`${namespace}/empresa_id`, empresaId);

  // Access Token (por si lo lees directamente en el backend)
  api.accessToken.setCustomClaim(`${namespace}/rol`, rol);
  api.accessToken.setCustomClaim(`${namespace}/empresa_id`, empresaId);
};
```

7. Click **Deploy**

### 5.2 Activar la Action en el flow

1. Dashboard → **Actions → Triggers → post-login**
2. Drag & drop la Action `Inject role and empresa_id` al flow
3. Click **Apply**

> Si saltaste este paso, los claims `rol` y `empresa_id` no aparecerán en el JWT y el cross-empresa check del Sprint 3 no funcionará.

---

## 6. Verificar que todo funciona

### 6.1 Test del JWT con curl (M2M flow)

Si quieres probar sin login interactivo, primero crea una M2M Application:

1. Applications → **+ Create Application** → **Machine to Machine**
2. Authorize for: `BITE.co API`
3. Asigna scopes: `read:reportes`
4. Anota su Client ID y Secret

Luego:

```bash
export AUTH0_DOMAIN=biteco-dev.us.auth0.com
export M2M_CLIENT_ID=xxx
export M2M_CLIENT_SECRET=yyy

# Pedir token
TOKEN=$(curl -s -X POST https://$AUTH0_DOMAIN/oauth/token \
  -H "content-type: application/json" \
  -d "{
    \"client_id\":\"$M2M_CLIENT_ID\",
    \"client_secret\":\"$M2M_CLIENT_SECRET\",
    \"audience\":\"https://api.biteco.co\",
    \"grant_type\":\"client_credentials\"
  }" | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"

# Decodificar el payload (parte del medio del JWT)
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | python3 -m json.tool
# Deberia mostrar: aud, iss, scope, https://biteco.co/rol, https://biteco.co/empresa_id
```

> **Ojo**: el M2M flow no ejecuta la Action post-login (esa Action solo
> corre en login interactivo de un usuario). Para los M2M tokens, los
> claims `rol`/`empresa_id` no aparecen — usalos solo para tests de
> "token valido". Para test de cross-empresa hay que loguear un usuario
> humano y robar la cookie de sesión.

### 6.2 Test interactivo

```bash
# Levanta el server local
cd biteco
python manage.py runserver

# Abre http://localhost:8000
# Click "Login con Auth0"
# Usa admin@biteco.local
# Una vez en /dashboard/, abre la consola Django:
python manage.py shell
>>> from usuario.models import Usuario
>>> u = Usuario.objects.get(email='admin@biteco.local')
>>> print(u.rol, u.empresa_id)
Admin 1
```

Si ves `Admin 1`, **todo funciona**: el pipeline `save_role_and_empresa` extrajo los claims del JWT y los persistió en el modelo.

---

## 7. Troubleshooting

| Síntoma | Causa probable | Fix |
|---|---|---|
| `redirect_uri is not in the list of allowed callback URLs` | Falta agregar la URL en Application Settings | Agregar `http://TU-DNS/complete/auth0` |
| Login funciona pero `request.user.rol` queda en default `"Usuario"` | La Action no se está ejecutando | Verifica que esté en el flow del trigger post-login |
| `request.user.empresa_id` es `None` | El usuario no tiene `app_metadata.empresa_id` | Edita el usuario en Auth0 → Details → app_metadata |
| El JWT no trae los claims customizados | Falta el namespace | Tiene que ser exactamente `https://biteco.co/rol` con el slash final del namespace |
| Login da 500 en Django | `social_django` no migrado | `python manage.py migrate` |
| `Forbidden` 403 en `/complete/auth0` | CSRF token mismatch | Asegúrate de que `CSRF_TRUSTED_ORIGINS` incluya el dominio del ALB |

---

## 8. Hardening para producción

Antes de presentar al profesor:

- [ ] Tenant en producción (no `dev`)
- [ ] Logout completo: usar `https://$AUTH0_DOMAIN/v2/logout` para terminar la sesión también del lado de Auth0
- [ ] Refresh tokens habilitados con rotación
- [ ] Brute force protection ON (Settings → Attack Protection)
- [ ] Bot detection ON
- [ ] MFA habilitado al menos para rol Admin
- [ ] Allowed Origins solo el dominio del ALB (no `*`)
- [ ] Logs de Auth0 → CloudWatch (via integración Auth0 → AWS)
