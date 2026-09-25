import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Actividad, Inscripcion
import logging
import json

logger = logging.getLogger('actividades')
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
    datos = [actividad.to_dict_v2(con_descripcion=False) for actividad in actividades]
    return JsonResponse(datos, safe=False)

@require_http_methods(["GET"])
def obtener_actividad_por_id(request, id):
    """ GET /activities/<id> """
    try:
        actividad = Actividad.objects.get(id=id)
        return JsonResponse(actividad.to_dict_v2(con_descripcion=True))
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
@require_http_methods(["PUT", "DELETE"])
def gestionar_inscripcion(request, id_actividad):
    """ PUT /me/enrollments/<id_actividad> """
    usuario = obtener_usuario_actual(request)
    
    # 401 si no está autenticado
    if not usuario:
        return JsonResponse({"code": "authentication_required", "message": "Se requiere identidad."}, status=401)

    try:
        actividad = Actividad.objects.get(id=id_actividad)
    except Actividad.DoesNotExist:
        return JsonResponse({"code": "activity_not_found", "message": "La actividad indicada no existe."}, status=404)

    if request.method == "PUT":
        # Idempotencia: si ya está inscripto, devuelve 200
        inscripcion = Inscripcion.objects.filter(actividad=actividad, usuario=usuario).first()
        if inscripcion:
            logger.info(json.dumps({
                "timestamp": timezone.now().isoformat(),
                "level": "info",
                "event": "enrollment_reused",
                "correlation_id": getattr(request, 'correlation_id', 'unknown'),
                "method": "PUT",
                "path": request.path,
                "result": "reused"
            }))
            return JsonResponse(inscripcion.to_dict(), status=200)

        # 409 si sin cupo
        if actividad.disponibilidad <= 0:
            logger.info(json.dumps({
                "timestamp": timezone.now().isoformat(),
                "level": "warn",
                "event": "enrollment_rejected",
                "correlation_id": getattr(request, 'correlation_id', 'unknown'),
                "method": "PUT",
                "path": request.path,
                "result": "capacity_exhausted"
            }))
            return JsonResponse({"code": "capacity_exhausted", "message": "No hay lugares disponibles."}, status=409)

        # 201 en caso de éxito
        nueva_inscripcion = Inscripcion.objects.create(actividad=actividad, usuario=usuario)
        logger.info(json.dumps({
            "timestamp": timezone.now().isoformat(),
            "level": "info",
            "event": "enrollment_created",
            "correlation_id": getattr(request, 'correlation_id', 'unknown'),
            "method": "PUT",
            "path": request.path,
            "result": "created"
        }))
        return JsonResponse(nueva_inscripcion.to_dict(), status=201)
        
    elif request.method == "DELETE":
        inscripcion = Inscripcion.objects.filter(actividad=actividad, usuario=usuario).first()
        if inscripcion:
            inscripcion.delete()
            logger.info(json.dumps({
                "timestamp": timezone.now().isoformat(),
                "level": "info",
                "event": "enrollment_cancelled",
                "correlation_id": getattr(request, 'correlation_id', 'unknown'),
                "method": "DELETE",
                "path": request.path,
                "result": "cancelled"
            }))
        from django.http import HttpResponse
        return HttpResponse(status=204)
