from django.db import models

class Actividad(models.Model):
    titulo = models.CharField(max_length=255, verbose_name="Título")
    fecha = models.DateTimeField(verbose_name="Fecha")
    capacidad = models.IntegerField(verbose_name="Capacidad")
    descripcion = models.TextField(verbose_name="Descripción")

    @property
    def disponibilidad(self):
        cantidad_inscritos = self.inscripciones.count()
        return max(0, self.capacidad - cantidad_inscritos)

    def to_dict(self, con_descripcion=False):
        data = {
            "id": self.id,
            "titulo": self.titulo,
            "fecha": self.fecha.isoformat(),
            "capacidad": self.capacidad,
            "disponibilidad": self.disponibilidad
        }
        if con_descripcion:
            data["descripcion"] = self.descripcion
        return data

    def to_dict_v2(self, con_descripcion=False):
        data = {
            "id": str(self.id),
            "titulo": self.titulo,
            "fecha": self.fecha.isoformat(),
            "availability": {
                "capacity": self.capacidad,
                "available_slots": self.disponibilidad
            }
        }
        if con_descripcion:
            data["descripcion"] = self.descripcion
        return data

    def __str__(self):
        return self.titulo

class Inscripcion(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='inscripciones', verbose_name="Actividad")
    usuario = models.CharField(max_length=150, verbose_name="Usuario")
    fecha_inscripcion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Inscripción")

    class Meta:
        unique_together = ('actividad', 'usuario')
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"

    def to_dict(self):
        return {
            "activity_id": str(self.actividad.id),
            "participant_id": self.usuario,
            "enrolled_at": self.fecha_inscripcion.isoformat() if self.fecha_inscripcion else None
        }

    def __str__(self):
        return f"{self.usuario} inscrito en {self.actividad.titulo}"
