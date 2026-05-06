"""
usuario/pipeline.py - Pipeline post-login para Auth0.

Extrae el rol y empresa_id del JWT y los guarda en el modelo de usuario
de Django para que esten disponibles en cada request via `request.user`.

Auth0 inyecta estos claims via Action post-login (configurada en el dashboard
de Auth0):

    api.idToken.setCustomClaim("https://biteco.co/rol", event.user.app_metadata.rol);
    api.idToken.setCustomClaim("https://biteco.co/empresa_id", event.user.app_metadata.empresa_id);
"""

ROL_CLAIM = "https://biteco.co/rol"
EMPRESA_CLAIM = "https://biteco.co/empresa_id"


def save_role_and_empresa(backend, user, response, *args, **kwargs):
    """
    Adjunta rol y empresa_id al usuario Django desde el id_token de Auth0.

    `response` es el dict con la respuesta de Auth0, incluyendo el id_token
    decodificado. social_django pone los claims customizados en `response`
    directamente cuando el backend es Auth0OAuth2.
    """
    if backend.name != "auth0":
        return

    rol = response.get(ROL_CLAIM, "Usuario")
    empresa_id = response.get(EMPRESA_CLAIM)

    # Guardarlos en el User; si tu modelo Usuario es custom, ajusta aqui
    changed = False
    if hasattr(user, "rol") and getattr(user, "rol", None) != rol:
        user.rol = rol
        changed = True
    if hasattr(user, "empresa_id") and getattr(user, "empresa_id", None) != empresa_id:
        user.empresa_id = empresa_id
        changed = True

    if changed:
        user.save()
