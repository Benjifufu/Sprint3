from django.contrib.auth.models import User

def get_usuario(username):
    usuario = User.objects.get(username=username)
    return usuario

def get_todos_usuarios():
    usuarios = User.objects.all()
    return usuarios