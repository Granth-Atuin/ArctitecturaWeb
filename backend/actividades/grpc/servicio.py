"""Adaptador de entrada gRPC: traduce el protocolo gRPC a la lógica de inscripción."""

import grpc
from django.db import close_old_connections, transaction

from ..models import Actividad, Inscripcion, Participante
from ..views import usuario_desde_access
from . import inscripciones_pb2, inscripciones_pb2_grpc


class ServicioInscripciones(inscripciones_pb2_grpc.InscripcionesServicer):
    """Implementa el servicio gRPC definido en inscripciones.proto."""

    def Inscribir(self, request, context):
        close_old_connections()
        try:
            participante = _participante_autenticado(context)

            try:
                actividad_id = int(request.actividad_id)
                if actividad_id <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "actividad_id debe ser un entero positivo.")

            try:
                actividad = Actividad.objects.get(id=actividad_id)
            except Actividad.DoesNotExist:
                context.abort(grpc.StatusCode.NOT_FOUND, "La actividad no existe.")

            with transaction.atomic():
                # Idempotencia: si ya estaba inscripto, retornamos creada=False
                inscripcion_existente = Inscripcion.objects.filter(
                    actividad=actividad, participante=participante
                ).first()
                if inscripcion_existente:
                    return inscripciones_pb2.InscribirResponse(
                        actividad_id=str(actividad.id),
                        participante_id=str(participante.id),
                        inscripta_en=inscripcion_existente.fecha_inscripcion.isoformat()
                        if inscripcion_existente.fecha_inscripcion
                        else "",
                        creada=False,
                    )

                # Regla de negocio: verificar cupo
                if actividad.disponibilidad <= 0:
                    context.abort(grpc.StatusCode.FAILED_PRECONDITION, "No hay cupos disponibles.")

                inscripcion = Inscripcion.objects.create(
                    actividad=actividad, participante=participante
                )

            return inscripciones_pb2.InscribirResponse(
                actividad_id=str(actividad.id),
                participante_id=str(participante.id),
                inscripta_en=inscripcion.fecha_inscripcion.isoformat()
                if inscripcion.fecha_inscripcion
                else "",
                creada=True,
            )
        finally:
            close_old_connections()


def _participante_autenticado(context):
    """Valida la identidad del usuario desde la metadata gRPC (mismo JWT Bearer)."""
    metadata = dict(context.invocation_metadata())
    auth_header = metadata.get("authorization", "")
    esquema, _, token = auth_header.partition(" ")
    if esquema.lower() != "bearer" or not token:
        context.abort(grpc.StatusCode.UNAUTHENTICATED, "Falta el token Bearer en metadata.")

    usuario = usuario_desde_access(token)
    if not usuario or not usuario.is_active:
        context.abort(grpc.StatusCode.UNAUTHENTICATED, "Token inválido o expirado.")

    try:
        return usuario.participante
    except Participante.DoesNotExist:
        context.abort(grpc.StatusCode.UNAUTHENTICATED, "El usuario no posee perfil de participante.")

