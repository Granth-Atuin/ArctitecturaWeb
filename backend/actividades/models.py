import hashlib
import secrets
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Actividad(models.Model):
    titulo = models.CharField(max_length=255, verbose_name="Título")
    fecha = models.DateTimeField(verbose_name="Fecha")
    capacidad = models.PositiveIntegerField(verbose_name="Capacidad")
    descripcion = models.TextField(verbose_name="Descripción")

    class Meta:
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        ordering = ("fecha",)

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


class Participante(models.Model):
    """Perfil de participante vinculado al User de Django (auth)."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="participante",
        verbose_name="Usuario",
    )
    nombre = models.CharField(max_length=150, verbose_name="Nombre completo")

    class Meta:
        verbose_name = "Participante"
        verbose_name_plural = "Participantes"

    def to_dict(self):
        return {
            "id": self.pk,
            "email": self.user.email,
            "nombre": self.nombre,
        }

    def __str__(self):
        return f"{self.nombre} ({self.user.email})"


class Inscripcion(models.Model):
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name='inscripciones',
        verbose_name="Actividad",
    )
    participante = models.ForeignKey(
        Participante,
        on_delete=models.CASCADE,
        related_name='inscripciones',
        verbose_name="Participante",
    )
    fecha_inscripcion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Inscripción")

    class Meta:
        unique_together = ('actividad', 'participante')
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"

    def to_dict(self):
        return {
            "id_actividad": self.actividad.id,
            "titulo": self.actividad.titulo,
            "activity_id": str(self.actividad.id),
            "participant_id": self.participante.user.email,
            "enrolled_at": self.fecha_inscripcion.isoformat() if self.fecha_inscripcion else None
        }

    def __str__(self):
        return f"{self.participante.nombre} inscripto en {self.actividad.titulo}"


class RefreshToken(models.Model):
    """Refresh token opaco rotativo; se almacena el hash SHA-256, nunca el secreto."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
        verbose_name="Usuario",
    )
    token_hash = models.CharField(max_length=64, unique=True, verbose_name="Hash del token")
    expires_at = models.DateTimeField(verbose_name="Expira en")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado en")

    class Meta:
        verbose_name = "Refresh Token"
        verbose_name_plural = "Refresh Tokens"

    @classmethod
    def crear(cls, user):
        """Genera un token aleatorio seguro, guarda el hash y devuelve el secreto."""
        secreto = secrets.token_hex(32)
        hash_ = hashlib.sha256(secreto.encode()).hexdigest()
        expires_at = timezone.now() + timezone.timedelta(
            seconds=settings.REFRESH_SECONDS
        )
        cls.objects.create(user=user, token_hash=hash_, expires_at=expires_at)
        return secreto

    @classmethod
    def verificar(cls, secreto):
        """Busca el token por hash; devuelve la instancia o None si venció/no existe."""
        hash_ = hashlib.sha256(secreto.encode()).hexdigest()
        try:
            token = cls.objects.select_related("user").get(
                token_hash=hash_,
                expires_at__gt=timezone.now(),
            )
            return token
        except cls.DoesNotExist:
            return None

    def __str__(self):
        return f"RefreshToken de {self.user.email} (expira {self.expires_at})"
