import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

@csrf_exempt
def login(request):
    if request.method == 'POST':
        body = json.loads(request.body)
        username = body.get('username')
        password = body.get('password')

        user = authenticate(username=username, password=password)

        if user is not None:
            return HttpResponse(
                json.dumps({
                    'status': 'ok',
                    'user_id': user.id,
                    'username': user.username
                }),
                content_type='application/json'
            )
        else:
            return HttpResponse(
                json.dumps({'error': 'Credenciales inválidas'}),
                content_type='application/json',
                status=401
            )

    return HttpResponse(
        json.dumps({'error': 'Método no permitido'}),
        content_type='application/json',
        status=405
    )

@csrf_exempt
def dashboard(request):
    if request.method == 'GET':
        username = request.GET.get('username', 'anonimo')
        return HttpResponse(
            json.dumps({
                'status': 'ok',
                'message': 'Dashboard cargado correctamente',
                'username': username
            }),
            content_type='application/json'
        )

    return HttpResponse(
        json.dumps({'error': 'Método no permitido'}),
        content_type='application/json',
        status=405
    )