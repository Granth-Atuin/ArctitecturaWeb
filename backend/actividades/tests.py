import json
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from .models import Actividad, Inscripcion, Participante, RefreshToken

User = get_user_model()


class AuthJWTTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="StrongPassword123!",
        )
        self.participante = Participante.objects.create(
            user=self.user,
            nombre="Usuario Test",
        )
        self.actividad = Actividad.objects.create(
            titulo="Actividad Test",
            fecha=timezone.now() + timedelta(days=5),
            capacidad=2,
            descripcion="Descripción de prueba",
        )

    def test_registro_usuario_exitoso(self):
        resp = self.client.post(
            "/api/v1/auth/register",
            data=json.dumps({
                "nombre": "Nuevo Usuario",
                "email": "nuevo@example.com",
                "contrasena": "SuperPassword99!",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(email="nuevo@example.com").exists())
        self.assertTrue(Participante.objects.filter(nombre="Nuevo Usuario").exists())

    def test_registro_email_duplicado(self):
        resp = self.client.post(
            "/api/v1/auth/register",
            data=json.dumps({
                "nombre": "Otro Nombre",
                "email": "test@example.com",
                "contrasena": "SuperPassword99!",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)

    def test_login_exitoso(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            data=json.dumps({
                "email": "test@example.com",
                "contrasena": "StrongPassword123!",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "Bearer")
        self.assertIn("refresh_token", resp.cookies)
        self.assertTrue(resp.cookies["refresh_token"]["httponly"])

    def test_login_credenciales_invalidas(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            data=json.dumps({
                "email": "test@example.com",
                "contrasena": "IncorrectPassword!",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_refresh_token_rotacion(self):
        # 1. Login para obtener refresh token
        login_resp = self.client.post(
            "/api/v1/auth/login",
            data=json.dumps({
                "email": "test@example.com",
                "contrasena": "StrongPassword123!",
            }),
            content_type="application/json",
        )
        old_cookie = login_resp.cookies["refresh_token"].value

        # 2. Refresh usando la cookie
        refresh_resp = self.client.post(
            "/api/v1/auth/refresh",
            content_type="application/json",
        )
        self.assertEqual(refresh_resp.status_code, 200)
        new_data = refresh_resp.json()
        self.assertIn("access_token", new_data)

        # Verificar rotación: la cookie vieja ya no es válida
        new_cookie = refresh_resp.cookies["refresh_token"].value
        self.assertNotEqual(old_cookie, new_cookie)

    def test_logout_invalida_refresh_token(self):
        # Login
        self.client.post(
            "/api/v1/auth/login",
            data=json.dumps({
                "email": "test@example.com",
                "contrasena": "StrongPassword123!",
            }),
            content_type="application/json",
        )
        self.assertEqual(RefreshToken.objects.filter(user=self.user).count(), 1)

        # Logout
        logout_resp = self.client.post("/api/v1/auth/logout")
        self.assertEqual(logout_resp.status_code, 200)
        self.assertEqual(RefreshToken.objects.filter(user=self.user).count(), 0)

    def test_acceso_endpoint_protegido_me(self):
        # Sin token -> 401
        resp_anon = self.client.get("/api/v1/me")
        self.assertEqual(resp_anon.status_code, 401)

        # Con token -> 200
        login_resp = self.client.post(
            "/api/v1/auth/login",
            data=json.dumps({
                "email": "test@example.com",
                "contrasena": "StrongPassword123!",
            }),
            content_type="application/json",
        )
        token = login_resp.json()["access_token"]

        resp_auth = self.client.get(
            "/api/v1/me",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(resp_auth.status_code, 200)
        self.assertEqual(resp_auth.json()["email"], "test@example.com")

    def test_inscripcion_y_cancelacion(self):
        login_resp = self.client.post(
            "/api/v1/auth/login",
            data=json.dumps({
                "email": "test@example.com",
                "contrasena": "StrongPassword123!",
            }),
            content_type="application/json",
        )
        token = login_resp.json()["access_token"]
        auth_header = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        # 1. Inscribir
        put_resp = self.client.put(
            f"/api/v1/me/enrollments/{self.actividad.id}",
            **auth_header,
        )
        self.assertEqual(put_resp.status_code, 201)
        self.assertTrue(Inscripcion.objects.filter(actividad=self.actividad, participante=self.participante).exists())

        # 2. Inscribir de nuevo (conflicto)
        put_dup = self.client.put(
            f"/api/v1/me/enrollments/{self.actividad.id}",
            **auth_header,
        )
        self.assertEqual(put_dup.status_code, 409)

        # 3. Listar mis inscripciones
        get_resp = self.client.get(
            "/api/v1/me/enrollments",
            **auth_header,
        )
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(len(get_resp.json()), 1)

        # 4. Cancelar inscripción
        del_resp = self.client.delete(
            f"/api/v1/me/enrollments/{self.actividad.id}/cancel",
            **auth_header,
        )
        self.assertEqual(del_resp.status_code, 200)
        self.assertFalse(Inscripcion.objects.filter(actividad=self.actividad, participante=self.participante).exists())
