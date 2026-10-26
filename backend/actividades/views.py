"""Autenticación JWT: access Bearer en memoria + refresh opaco en cookie HttpOnly."""
import hashlib
import json

import jwt
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import Actividad, Inscripcion, Participante, RefreshToken

User = get_user_model()

REFRESH_COOKIE = "refresh_token"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def json_body(request):
    """Parsea el cuerpo JSON; devuelve dict o None si es inválido."""
    try:
        value = json.loads(request.body or b"{}")
        return value if isinstance(value, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


def error_response(code, mensaje, status):
    """Respuesta de error JSON estándar."""
    return JsonResponse({"code": code, "mensaje": mensaje}, status=status)


def private_json(data, status=200):
    """Respuesta JSON que nunca se cachea (datos privados del usuario)."""
    resp = JsonResponse(data, safe=isinstance(data, dict), status=status)
    resp["Cache-Control"] = "no-store"
    return resp


# ─── JWT Access ───────────────────────────────────────────────────────────────

def hacer_access_token(user):
    """Firma un access token JWT de corta duración con el id del usuario."""
    ahora = int(timezone.now().timestamp())
    return jwt.encode(
        {
            "sub": str(user.pk),
            "iat": ahora,
            "exp": ahora + settings.ACCESS_SECONDS,
            "iss": settings.JWT_ISSUER,
            "type": "access",
        },
        settings.JWT_SIGNING_KEY,
        algorithm="HS256",
    )


def usuario_desde_access(valor):
    """Verifica firma, issuer, expiración y tipo antes de buscar el usuario."""
    try:
        claims = jwt.decode(
            valor,
            settings.JWT_SIGNING_KEY,
            algorithms=["HS256"],
            issuer=settings.JWT_ISSUER,
            options={"require": ["sub", "iat", "exp", "iss", "type"]},
        )
        if claims.get("type") != "access":
            return None
        if type(claims["iat"]) is not int or type(claims["exp"]) is not int:
            return None
        if claims["iat"] < 0 or claims["exp"] <= claims["iat"]:
            return None
        subject = claims["sub"]
        if not isinstance(subject, str) or not subject.isdecimal() or len(subject) > 18:
            return None
        return User.objects.filter(pk=int(subject), is_active=True).first()
    except (jwt.PyJWTError, ValueError, TypeError, OverflowError):
        return None


def autenticar_request(request):
    """Extrae y valida el Bearer token del header Authorization."""
    partes = request.headers.get("Authorization", "").split()
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return usuario_desde_access(partes[1])
    return None


def usuario_actual(request):
    """Devuelve el Participante autenticado o None."""
    user = autenticar_request(request)
    if not user or not user.is_active:
        return None
    try:
        return user.participante
    except Participante.DoesNotExist:
        return None


def no_autorizado():
    """401 sin revelar detalles del error."""
    return error_response(
        "unauthorized",
        "Credencial ausente o inválida. Ingresá nuevamente.",
        401,
    )


# ─── Cookie helpers ───────────────────────────────────────────────────────────

def set_refresh_cookie(response, secreto):
    """Agrega el refresh token como cookie HttpOnly, SameSite=Lax."""
    response.set_cookie(
        REFRESH_COOKIE,
        secreto,
        max_age=settings.REFRESH_SECONDS,
        httponly=True,
        samesite="Lax",
        secure=False,  # True en producción con HTTPS
        path="/api/v1/auth/",
    )


def delete_refresh_cookie(response):
    """Elimina la cookie del refresh token."""
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth/")


# ─── Endpoints de autenticación ───────────────────────────────────────────────

@csrf_exempt
@require_POST
def registrar(request):
    """POST /api/v1/auth/register — Crea una cuenta nueva con email y contraseña."""
    body = json_body(request)
    if body is None:
        return error_response("bad_request", "Cuerpo JSON inválido.", 400)

    email = (body.get("email") or "").strip().lower()
    contrasena = body.get("contrasena") or body.get("password") or ""
    nombre = (body.get("nombre") or "").strip()

    if not email or not contrasena or not nombre:
        return error_response("bad_request", "email, contrasena y nombre son requeridos.", 400)

    try:
        validate_email(email)
    except ValidationError:
        return error_response("invalid_email", "El email no tiene un formato válido.", 400)

    try:
        validate_password(contrasena)
    except ValidationError as exc:
        return error_response("weak_password", exc.messages[0], 400)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                password=contrasena,
            )
            participante = Participante.objects.create(user=user, nombre=nombre)
    except IntegrityError:
        return error_response("email_taken", "Ya existe una cuenta con ese email.", 409)

    return private_json({"mensaje": "Cuenta creada.", "participante": participante.to_dict()}, 201)


@csrf_exempt
@require_POST
def login(request):
    """POST /api/v1/auth/login — Valida credenciales y devuelve access + refresh token."""
    body = json_body(request)
    if body is None:
        return error_response("bad_request", "Cuerpo JSON inválido.", 400)

    email = (body.get("email") or "").strip().lower()
    contrasena = body.get("contrasena") or body.get("password") or ""

    if not email or not contrasena:
        return error_response("bad_request", "email y contrasena son requeridos.", 400)

    user = authenticate(request, username=email, password=contrasena)
    if user is None or not user.is_active:
        return error_response("invalid_credentials", "Email o contraseña incorrectos.", 401)

    try:
        participante = user.participante
    except Participante.DoesNotExist:
        return error_response("no_profile", "Esta cuenta no tiene perfil de participante.", 403)

    access = hacer_access_token(user)
    secreto_refresh = RefreshToken.crear(user)

    resp = private_json({
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": settings.ACCESS_SECONDS,
        "participante": participante.to_dict(),
    })
    set_refresh_cookie(resp, secreto_refresh)
    # Enviamos el CSRF token para que el frontend pueda usarlo en refresh/logout
    get_token(request)
    return resp


@csrf_exempt
@require_POST
def refresh(request):
    """POST /api/v1/auth/refresh — Rota el refresh token y emite un nuevo access token."""
    secreto = request.COOKIES.get(REFRESH_COOKIE)
    if not secreto:
        return error_response("no_refresh", "No hay refresh token.", 401)

    token_obj = RefreshToken.verificar(secreto)
    if token_obj is None:
        resp = error_response("expired_refresh", "El refresh token venció o es inválido. Ingresá nuevamente.", 401)
        delete_refresh_cookie(resp)
        return resp

    # Rotación: eliminar el viejo y crear uno nuevo
    user = token_obj.user
    token_obj.delete()
    secreto_nuevo = RefreshToken.crear(user)
    access = hacer_access_token(user)

    resp = private_json({
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": settings.ACCESS_SECONDS,
    })
    set_refresh_cookie(resp, secreto_nuevo)
    return resp


@csrf_exempt
@require_POST
def logout(request):
    """POST /api/v1/auth/logout — Invalida el refresh token y limpia la cookie."""
    secreto = request.COOKIES.get(REFRESH_COOKIE)
    if secreto:
        hash_ = hashlib.sha256(secreto.encode()).hexdigest()
        RefreshToken.objects.filter(token_hash=hash_).delete()

    resp = private_json({"mensaje": "Sesión cerrada."})
    delete_refresh_cookie(resp)
    return resp


# ─── Endpoints de usuario ─────────────────────────────────────────────────────

@require_GET
def me(request):
    """GET /api/v1/me — Perfil del participante autenticado."""
    participante = usuario_actual(request)
    if participante is None:
        return no_autorizado()
    return private_json(participante.to_dict())


# ─── Endpoints de actividades ─────────────────────────────────────────────────

@require_GET
def obtener_actividades(request):
    """GET /api/v1/activities — Lista pública de actividades."""
    actividades = Actividad.objects.all()
    datos = [a.to_dict(con_descripcion=False) for a in actividades]
    return JsonResponse(datos, safe=False)


@require_GET
def obtener_actividad_por_id(request, id):
    """GET /api/v1/activities/<id> — Detalle de una actividad."""
    try:
        actividad = Actividad.objects.get(id=id)
        return JsonResponse(actividad.to_dict(con_descripcion=True))
    except Actividad.DoesNotExist:
        return error_response("not_found", "Actividad no encontrada.", 404)


# ─── Endpoints de inscripciones ───────────────────────────────────────────────

@require_GET
def mis_inscripciones(request):
    """GET /api/v1/me/enrollments — Inscripciones del participante autenticado."""
    participante = usuario_actual(request)
    if participante is None:
        return no_autorizado()
    inscripciones = Inscripcion.objects.filter(participante=participante).select_related("actividad")
    datos = [i.to_dict() for i in inscripciones]
    return private_json(datos)


@csrf_exempt
@require_http_methods(["PUT"])
def inscripcion(request, id_actividad):
    """PUT /api/v1/me/enrollments/<id> — Inscribir al participante autenticado."""
    participante = usuario_actual(request)
    if participante is None:
        return no_autorizado()

    try:
        actividad = Actividad.objects.get(id=id_actividad)
    except Actividad.DoesNotExist:
        return error_response("not_found", "Actividad no encontrada.", 404)

    if Inscripcion.objects.filter(actividad=actividad, participante=participante).exists():
        return error_response("already_enrolled", "Ya te encontrás inscripto a esta actividad.", 409)

    if actividad.disponibilidad <= 0:
        return error_response("no_capacity", "No hay cupo disponible para esta actividad.", 409)

    Inscripcion.objects.create(actividad=actividad, participante=participante)
    return private_json({"mensaje": "Inscripción registrada con éxito."}, 201)


@csrf_exempt
@require_http_methods(["DELETE"])
def cancelar_inscripcion(request, id_actividad):
    """DELETE /api/v1/me/enrollments/<id> — Cancelar inscripción del participante."""
    participante = usuario_actual(request)
    if participante is None:
        return no_autorizado()

    try:
        actividad = Actividad.objects.get(id=id_actividad)
    except Actividad.DoesNotExist:
        return error_response("not_found", "Actividad no encontrada.", 404)

    deleted, _ = Inscripcion.objects.filter(
        actividad=actividad, participante=participante
    ).delete()

    if deleted == 0:
        return error_response("not_enrolled", "No estás inscripto a esta actividad.", 404)

    return private_json({"mensaje": "Inscripción cancelada."})
