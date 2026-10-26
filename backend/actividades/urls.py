from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('auth/register', views.registrar, name='registrar'),
    path('auth/login', views.login, name='login'),
    path('auth/refresh', views.refresh, name='refresh'),
    path('auth/logout', views.logout, name='logout'),

    # Usuario
    path('me', views.me, name='me'),
    path('me/enrollments', views.mis_inscripciones, name='mis_inscripciones'),
    path('me/enrollments/<int:id_actividad>', views.inscripcion, name='inscripcion'),
    path('me/enrollments/<int:id_actividad>/cancel', views.cancelar_inscripcion, name='cancelar_inscripcion'),

    # Actividades (públicas)
    path('activities', views.obtener_actividades, name='obtener_actividades'),
    path('activities/<int:id>', views.obtener_actividad_por_id, name='obtener_actividad_por_id'),

    # Compatibilidad con versiones previas
    path('activities/<int:id>/enrollments', views.inscripcion, name='compat_inscripcion'),
]
