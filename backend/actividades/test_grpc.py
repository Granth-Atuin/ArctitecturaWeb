from datetime import datetime
import grpc
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .grpc import inscripciones_pb2
from .grpc.servicio import ServicioInscripciones
from .models import Actividad, Inscripcion, Participante
from .views import hacer_access_token


class Abortado(Exception):
    pass


class ContextoFalso:
    """Imita grpc.ServicerContext: metadata de entrada y abort()."""

    def __init__(self, token=None):
        self.metadata = [("authorization", f"Bearer {token}")] if token else []
        self.codigo = None
        self.detalle = None

    def invocation_metadata(self):
        return self.metadata

    def abort(self, codigo, detalle):
        self.codigo = codigo
        self.detalle = detalle
        raise Abortado(detalle)


class ServicioInscripcionesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="ada@example.com",
            email="ada@example.com",
            password="DemoPassword123!",
        )
        self.participante = Participante.objects.create(
            user=self.user,
            nombre="Ada Lovelace",
        )
        self.token = hacer_access_token(self.user)

        self.actividad = Actividad.objects.create(
            titulo="Arquitecturas Distribuidas con gRPC",
            fecha=timezone.make_aware(datetime(2026, 12, 1, 10, 0)),
            capacidad=1,
            descripcion="Taller de gRPC y microservicios",
        )
        self.servicio = ServicioInscripciones()

    def inscribir(self, actividad_id, token="propio"):
        token_a_usar = self.token if token == "propio" else token
        contexto = ContextoFalso(token_a_usar)
        pedido = inscripciones_pb2.InscribirRequest(actividad_id=str(actividad_id))
        try:
            respuesta = self.servicio.Inscribir(pedido, contexto)
            return respuesta, contexto
        except Abortado:
            return None, contexto

    def test_inscribe_con_exito_y_es_idempotente(self):
        # Primera inscripción exitosa
        primera, ctx1 = self.inscribir(self.actividad.id)
        self.assertIsNotNone(primera)
        self.assertTrue(primera.creada)
        self.assertEqual(primera.actividad_id, str(self.actividad.id))
        self.assertEqual(primera.participante_id, str(self.participante.id))
        self.assertEqual(Inscripcion.objects.count(), 1)

        # Segunda llamada: idempotente (no crea duplicado ni falla)
        segunda, ctx2 = self.inscribir(self.actividad.id)
        self.assertIsNotNone(segunda)
        self.assertFalse(segunda.creada)
        self.assertEqual(segunda.actividad_id, str(self.actividad.id))
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_errores_del_servicio_como_codigos_grpc(self):
        User = get_user_model()
        otro_user = User.objects.create_user(
            username="grace@example.com",
            email="grace@example.com",
            password="DemoPassword123!",
        )
        Participante.objects.create(user=otro_user, nombre="Grace Hopper")
        otro_token = hacer_access_token(otro_user)

        # Llenamos el cupo con ada (capacidad=1)
        self.inscribir(self.actividad.id, token="propio")

        casos = {
            # Grace intenta inscribirse pero la capacidad ya está llena
            grpc.StatusCode.FAILED_PRECONDITION: (self.actividad.id, otro_token),
            # Actividad inexistente
            grpc.StatusCode.NOT_FOUND: (99999, "propio"),
            # ID no entero
            grpc.StatusCode.INVALID_ARGUMENT: ("no-es-numero", "propio"),
            # ID negativo
            grpc.StatusCode.INVALID_ARGUMENT: ("-1", "propio"),
            # Sin autenticación
            grpc.StatusCode.UNAUTHENTICATED: (self.actividad.id, None),
        }

        for codigo, (act_id, tkn) in casos.items():
            with self.subTest(codigo=codigo, act_id=act_id):
                respuesta, contexto = self.inscribir(act_id, token=tkn)
                self.assertIsNone(respuesta)
                self.assertEqual(contexto.codigo, codigo)

    def test_rechaza_un_token_invalido_o_expirado(self):
        respuesta, contexto = self.inscribir(self.actividad.id, token="token_invalido_xyz")
        self.assertIsNone(respuesta)
        self.assertEqual(contexto.codigo, grpc.StatusCode.UNAUTHENTICATED)
