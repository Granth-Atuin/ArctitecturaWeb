"""Levanta el servidor gRPC de inscripciones (otro proceso, mismo código)."""

from concurrent import futures

import grpc
from django.core.management.base import BaseCommand

from actividades.grpc import inscripciones_pb2_grpc
from actividades.grpc.servicio import ServicioInscripciones


class Command(BaseCommand):
    help = "Levanta el servidor gRPC de inscripciones."

    def add_arguments(self, parser):
        parser.add_argument("--puerto", type=int, default=50051)

    def handle(self, *args, puerto, **options):
        servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        inscripciones_pb2_grpc.add_InscripcionesServicer_to_server(
            ServicioInscripciones(), servidor
        )
        servidor.add_insecure_port(f"[::]:{puerto}")
        servidor.start()
        self.stdout.write(f"Servidor gRPC escuchando en el puerto {puerto}")
        try:
            servidor.wait_for_termination()
        except KeyboardInterrupt:
            self.stdout.write("Deteniendo servidor gRPC...")
            servidor.stop(0)

