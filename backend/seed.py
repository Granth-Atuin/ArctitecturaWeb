import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configuracion.settings')
django.setup()

from actividades.models import Actividad

def ejecutar_seed():
    if Actividad.objects.count() == 0:
        print("Creando datos iniciales...")
        ahora = timezone.now()
        
        Actividad.objects.create(
            titulo="Introducción a Django",
            fecha=ahora + timedelta(days=2),
            capacidad=20,
            descripcion="Aprende los conceptos básicos de Django creando una aplicación web desde cero."
        )
        
        Actividad.objects.create(
            titulo="Taller de React y APIs",
            fecha=ahora + timedelta(days=5),
            capacidad=15,
            descripcion="Integra un frontend en React con una API RESTful."
        )
        
        Actividad.objects.create(
            titulo="Masterclass de Arquitectura Web",
            fecha=ahora + timedelta(days=10),
            capacidad=50,
            descripcion="Charla magistral sobre patrones y mejores prácticas en la arquitectura de aplicaciones web modernas."
        )
        print("¡Datos iniciales creados exitosamente!")
    else:
        print("Ya existen actividades en la base de datos.")

if __name__ == '__main__':
    ejecutar_seed()
