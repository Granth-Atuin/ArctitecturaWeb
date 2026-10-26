# Sistema de Inscripciones — Hito 2

Sistema de inscripciones a actividades con autenticación JWT (access token + refresh token rotativo).

## Estructura del proyecto

```
Entrgable/
├── backend/          # Django (API REST con JWT)
│   ├── actividades/  # App principal
│   ├── configuracion/ # Settings, URLs raíz
│   ├── manage.py
│   └── seed.py       # Datos iniciales y usuarios de prueba
└── frontend/         # Astro + React (Isla de inscripción)
    └── src/
        ├── pages/    # Listado y detalle de actividades
        └── components/IslaInscripcion.jsx  # Componente JWT
```

## Cómo ejecutar el proyecto

### Backend (Django)

```bash
cd backend

# Activar entorno virtual
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# Instalar dependencias (si es primera vez)
pip install django django-cors-headers PyJWT

# Aplicar migraciones
python manage.py migrate

# Cargar datos iniciales y usuarios de prueba
python seed.py

# Iniciar servidor
python manage.py runserver
```

El backend queda disponible en `http://127.0.0.1:8000`.

### Frontend (Astro)

```bash
cd frontend

# Instalar dependencias (si es primera vez)
npm install

# Iniciar servidor de desarrollo (requiere el backend corriendo)
npm run dev
```

El frontend queda disponible en `http://localhost:4321`.

## Usuarios de prueba

| Nombre       | Email                | Contraseña  |
|--------------|----------------------|-------------|
| Ana García   | ana@example.com      | Demo1234!   |
| Carlos López | carlos@example.com   | Demo1234!   |

## Endpoints de la API

### Autenticación

| Método | URL                        | Descripción                         |
|--------|----------------------------|-------------------------------------|
| POST   | `/api/v1/auth/register`    | Crear cuenta (nombre, email, contraseña) |
| POST   | `/api/v1/auth/login`       | Iniciar sesión → access + refresh token |
| POST   | `/api/v1/auth/refresh`     | Renovar access token                |
| POST   | `/api/v1/auth/logout`      | Invalidar refresh token             |

### Usuario

| Método | URL                                       | Auth requerida |
|--------|-------------------------------------------|----------------|
| GET    | `/api/v1/me`                              | Bearer         |
| GET    | `/api/v1/me/enrollments`                  | Bearer         |
| PUT    | `/api/v1/me/enrollments/<id>`             | Bearer         |
| DELETE | `/api/v1/me/enrollments/<id>/cancel`      | Bearer         |

### Actividades (públicas)

| Método | URL                          |
|--------|------------------------------|
| GET    | `/api/v1/activities`         |
| GET    | `/api/v1/activities/<id>`    |

## Diagrama de componentes y comunicaciones

```
                    ┌──────────────────────────────────────┐
                    │         NAVEGADOR DEL USUARIO        │
                    │                                      │
                    │  ┌────────────────────────────────┐  │
                    │  │   Astro (SSG)                  │  │
                    │  │   /activities          (build)  │  │
                    │  │   /activities/:id      (build)  │  │
                    │  └──────────────┬─────────────────┘  │
                    │                 │ hidrata             │
                    │  ┌──────────────▼─────────────────┐  │
                    │  │   React: IslaInscripcion.jsx   │  │
                    │  │                                │  │
                    │  │  access token: MEMORIA RAM     │  │
                    │  │  refresh token: cookie HttpOnly│  │
                    │  └──────────────┬─────────────────┘  │
                    └─────────────────┼────────────────────┘
                                      │ HTTP + Bearer / cookie
                                      ▼
                    ┌─────────────────────────────────────┐
                    │           Django (API)              │
                    │                                     │
                    │  /api/v1/auth/*  →  autenticación   │
                    │  /api/v1/me      →  perfil + inscr. │
                    │  /api/v1/activities → catálogo      │
                    │                                     │
                    │  ┌─────────────────────────────┐   │
                    │  │          SQLite              │   │
                    │  │  - Actividad                │   │
                    │  │  - Participante (→ User)    │   │
                    │  │  - Inscripcion              │   │
                    │  │  - RefreshToken (hash SHA256)│  │
                    │  └─────────────────────────────┘   │
                    └─────────────────────────────────────┘
```

## Dónde se guarda cada dato

| Dato               | Dónde                        |
|--------------------|------------------------------|
| Access token       | Memoria RAM del navegador (módulo JS, no localStorage) |
| Refresh token      | Cookie `HttpOnly, SameSite=Lax` (inaccesible desde JS) |
| Hash del refresh   | Tabla `RefreshToken` en SQLite (SHA-256, no el secreto) |
| Contraseña         | Tabla `auth_user` de Django (hash PBKDF2, jamás en texto plano) |

## Decisiones de diseño

### Flujo de autenticación

1. El usuario envía email + contraseña al backend (`POST /api/v1/auth/login`).
2. El backend valida con Django Auth, firma un **access token JWT** (HS256, 5 min de vida) y genera un **refresh token opaco** (64 bytes hex aleatorios).
3. El access token se devuelve en el cuerpo JSON → el frontend lo guarda **solo en memoria** (variable de módulo JS).
4. El refresh token se envía como **cookie HttpOnly** → el navegador lo envía automáticamente.
5. Cuando el access token expira, el frontend llama a `POST /api/v1/auth/refresh` (cookie se incluye automáticamente). El backend valida el refresh, lo **elimina** y emite uno nuevo (**rotación**).
6. En logout: el frontend llama a `POST /api/v1/auth/logout`; el backend invalida el refresh token de la BD y elimina la cookie.

### ¿Qué pasa con un access token ya emitido después del logout?

**Límite de la solución**: el access token de corta vida (5 minutos) sigue siendo válido hasta su expiración natural porque los JWT son stateless. El backend no mantiene una lista negra de access tokens. Esto es intencional: mantener la ventana de ataque acotada (≤ 5 min) es el trade-off estándar del patrón Bearer + refresh.

Para invalidación inmediata se necesitaría una lista negra de tokens (Redis, por ejemplo), lo que agregaría complejidad de infraestructura.

### Por qué el access token va en memoria y no en localStorage

`localStorage` es accesible desde cualquier script JS de la página, haciéndolo vulnerable a XSS. Al guardar el access token en una variable de módulo (RAM), si un script inyectado corre en otro contexto de módulo o recarga la página, pierde el token. El refresh token en cookie HttpOnly es invisible para JS.
