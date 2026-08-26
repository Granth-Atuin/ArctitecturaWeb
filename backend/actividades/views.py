import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Actividad, Inscripcion

# Nombre de usuario a usar cuando se simula la sesión
PARTICIPANTE_POR_DEFECTO = "participante_demo"

def obtener_usuario_actual(request):
    """
    Simula un participante por defecto o sesión.
    Si se envía el header Authorization, usa ese usuario.
    Si no se envía, para que se pueda obtener el 401 que pide el contrato,
    podríamos devolver None. 
    """
    auth_header = request.headers.get('Authorization')
    if auth_header:
        # Extraer el token/usuario
        usuario = auth_header.replace('Bearer', '').strip()
        return usuario if usuario else PARTICIPANTE_POR_DEFECTO
    
    # Para cumplir el requerimiento de retornar 401 cuando no está autenticado,
    # verificamos si existe un header personalizado 'X-Simular-Sesion' para 
    # usar la sesión por defecto, de lo contrario asumimos no autenticado (None).
    # Como es un laboratorio, también podemos asumir que sin Authorization = 401.
    return None

@require_http_methods(["GET"])
def obtener_actividades(request):
    """ GET /activities """
    actividades = Actividad.objects.all()
    datos = [actividad.to_dict(con_descripcion=False) for actividad in actividades]
    return JsonResponse(datos, safe=False)

@require_http_methods(["GET"])
def obtener_actividad_por_id(request, id):
    """ GET /activities/<id> """
    try:
        actividad = Actividad.objects.get(id=id)
        return JsonResponse(actividad.to_dict(con_descripcion=True))
    except Actividad.DoesNotExist:
        return JsonResponse({"error": "Actividad no encontrada"}, status=404)

@require_http_methods(["GET"])
def obtener_mis_inscripciones(request):
    """ GET /me/enrollments """
    usuario = obtener_usuario_actual(request)
    
    # Si queremos que funcione siempre por defecto en GET, asignamos el default si no hay auth
    if not usuario:
        usuario = PARTICIPANTE_POR_DEFECTO
        
    inscripciones = Inscripcion.objects.filter(usuario=usuario)
    datos = [inscripcion.to_dict() for inscripcion in inscripciones]
    return JsonResponse(datos, safe=False)

@csrf_exempt
@require_http_methods(["PUT"])
def registrar_inscripcion(request, id_actividad):
    """ PUT /me/enrollments/<id_actividad> """
    usuario = obtener_usuario_actual(request)
    
    # 401 si no está autenticado
    if not usuario:
        # Como se requiere retornar 401 si no está autenticado,
        # exigimos el header Authorization para este endpoint.
        return JsonResponse({"error": "No autorizado. Falta el header Authorization."}, status=401)

    try:
        actividad = Actividad.objects.get(id=id_actividad)
    except Actividad.DoesNotExist:
        return JsonResponse({"error": "Actividad no encontrada"}, status=404)

    # 409 si ya está inscripto
    if Inscripcion.objects.filter(actividad=actividad, usuario=usuario).exists():
        return JsonResponse({"error": "Ya te encuentras inscripto a esta actividad."}, status=409)

    # 409 si sin cupo
    if actividad.disponibilidad <= 0:
        return JsonResponse({"error": "No hay cupo disponible para esta actividad."}, status=409)

    # 200/201 en caso de éxito
    Inscripcion.objects.create(actividad=actividad, usuario=usuario)
    return JsonResponse({"mensaje": "Inscripción registrada con éxito."}, status=201)
