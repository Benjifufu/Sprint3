"""
usuario/models.py - Custom user model.

Bug fixes:
- rol = models.CharField()  -> faltaba max_length
- ForeignKey SET_NULL sin null=True
- Agregamos `empresa_id` (Integer) ya que `usuario.pipeline.save_role_and_empresa`
  lo lee y guarda desde el JWT de Auth0. Esto cumple ASR-01 (cross-empresa check).

Nota arquitectonica:
  Este modelo extiende django.contrib.auth.models.User para que social-auth-app-django
  pueda asociar el usuario de Auth0 con un User Django. La forma simple
  recomendada es heredar de AbstractUser; si tu equipo prefiere un modelo
  Usuario separado del User builtin, hay que agregar un OneToOne.
  Aqui adopto la heredacion AbstractUser para minimizar friccion.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    User extendido. Hereda username/password/email/first_name/last_name/...
    de AbstractUser, y agrega los campos de negocio.
    """
    # Campos de negocio
    nombre_negocio = models.CharField(max_length=100, blank=True)  # alias del nombre real
    apellido = models.CharField(max_length=100, blank=True)
    rol = models.CharField(max_length=50, default="Usuario")  # "Admin" | "Usuario"
    telefono = models.CharField(max_length=15, blank=True)
    estado = models.CharField(max_length=50, default="activo")
    fechaCreacion = models.DateField(auto_now_add=True)
    ultimoAcceso = models.DateField(auto_now=True)

    # ID de la empresa del JWT (Auth0 Action post-login lo inyecta)
    # Usamos IntegerField para evitar acoplar al modelo Empresa (que vive
    # en otra BD). Si quieres FK formal, considera ManyToMany o cross-DB joins.
    empresa_id = models.IntegerField(null=True, blank=True, db_index=True)

    def __str__(self):
        return f"{self.username} ({self.rol})"

    class Meta:
        app_label = "usuario"
