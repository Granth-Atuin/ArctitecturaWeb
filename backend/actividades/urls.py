from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('api/v1/auth/register', views.registrar, name='registrar'),
    path('api/v1/auth/login', views.login, name='login'),
    path('api/v1/auth/refresh', views.refresh, name='refresh'),
    path('api/v1/auth/logout', views.logout, name='logout'),

    # Usuario
    path('api/v1/me', views.me, name='me'),
    path('api/v1/me/enrollments', views.mis_inscripciones, name='mis_inscripciones'),
    path('api/v1/me/enrollments/<int:id_actividad>', views.inscripcion, name='inscripcion'),
    path('api/v1/me/enrollments/<int:id_actividad>/cancel', views.cancelar_inscripcion, name='cancelar_inscripcion'),

    # Actividades (públicas)
    path('api/v1/activities', views.obtener_actividades, name='obtener_actividades'),
    path('api/v1/activities/<int:id>', views.obtener_actividad_por_id, name='obtener_actividad_por_id'),
]
