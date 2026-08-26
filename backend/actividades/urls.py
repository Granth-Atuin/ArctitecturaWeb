from django.urls import path
from . import views

urlpatterns = [
    path('activities', views.obtener_actividades, name='obtener_actividades'),
    path('activities/<int:id>', views.obtener_actividad_por_id, name='obtener_actividad_por_id'),
    path('me/enrollments', views.obtener_mis_inscripciones, name='obtener_mis_inscripciones'),
    path('me/enrollments/<int:id_actividad>', views.registrar_inscripcion, name='registrar_inscripcion'),
]
