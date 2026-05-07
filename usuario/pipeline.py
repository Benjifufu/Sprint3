"""
usuario/pipeline.py - Pipeline post-login para Auth0.

Extrae el rol y empresa_id del JWT y los guarda en el modelo de usuario
de Django para que esten disponibles en cada request via `request.user`.

Auth0 inyecta estos claims via Action post-login (configurada en el dashboard
de Auth0):

    api.idToken.setCustomClaim("https://biteco.co/rol", event.user.app_metadata.rol);
    api.idToken.setCustomClaim("https://biteco.co/empresa_id", event.user.app_metadata.empresa_id);
"""

import jwt

ROL_CLAIM = "https://biteco.co/rol"
EMPRESA_CLAIM = "https://biteco.co/empresa_id"

def save_role_and_empresa(backend, user, response, *args, **kwargs):
    if backend.name != "auth0":
        return
    try:
        id_token = response.get("id_token", "")
        decoded = jwt.decode(id_token, options={"verify_signature": False})
        rol = decoded.get(ROL_CLAIM, "Usuario")
        empresa_id = decoded.get(EMPRESA_CLAIM)
    except Exception:
        rol = "Usuario"
        empresa_id = None
    user.rol = rol
    if empresa_id:
        user.empresa_id = empresa_id
    user.save()