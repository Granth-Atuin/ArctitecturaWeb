"""
Seed inicial para el Hito 2.
Crea actividades y usuarios de prueba con sus perfiles de participante.

Usuarios de prueba:
  - ana@example.com / Demo1234!
  - carlos@example.com / Demo1234!
"""
import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configuracion.settings')
django.setup()

from django.contrib.auth.models import User
from actividades.models import Actividad, Participante


def ejecutar_seed():
    # --- Actividades ---
    if Actividad.objects.count() == 0:
        print("Creando actividades...")
        ahora = timezone.now()

        Actividad.objects.create(
            titulo="Introducción a Django",
            fecha=ahora + timedelta(days=2),
            capacidad=20,
            descripcion="Aprende los conceptos básicos de Django creando una aplicación web desde cero.",
        )
        Actividad.objects.create(
            titulo="Taller de React y APIs",
            fecha=ahora + timedelta(days=5),
            capacidad=15,
            descripcion="Integra un frontend en React con una API RESTful.",
        )
        Actividad.objects.create(
            titulo="Masterclass de Arquitectura Web",
            fecha=ahora + timedelta(days=10),
            capacidad=50,
            descripcion="Charla magistral sobre patrones y mejores prácticas en arquitecturas web modernas.",
        )
        print("  [OK] 3 actividades creadas.")
    else:
        print("  [--] Actividades ya existen, se omite la creacion.")

    # --- Usuarios de prueba ---
    USUARIOS = [
        {"email": "ana@example.com", "nombre": "Ana García", "password": "Demo1234!"},
        {"email": "carlos@example.com", "nombre": "Carlos López", "password": "Demo1234!"},
    ]

    for u in USUARIOS:
        if not User.objects.filter(username=u["email"]).exists():
            user = User.objects.create_user(
                username=u["email"],
                email=u["email"],
                password=u["password"],
            )
            Participante.objects.create(user=user, nombre=u["nombre"])
            print(f"  [OK] Participante creado: {u['nombre']} ({u['email']})")
        else:
            print(f"  [--] Participante ya existe: {u['email']}")

    print("\nSeed completado.")
    print("\nCredenciales de prueba:")
    for u in USUARIOS:
        print(f"  Email: {u['email']}  |  Contraseña: {u['password']}")


if __name__ == '__main__':
    ejecutar_seed()
