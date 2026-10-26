# Arquitecturas Web — Sistema de Inscripciones (Entrega 4: Autenticación JWT)

Este repositorio contiene la solución completa para el sistema de inscripción a actividades con **autenticación JWT** (Access Token de corta duración en memoria RAM + Refresh Token opaco rotativo en cookie `HttpOnly`), siguiendo la arquitectura web desacoplada con **Astro** (Frontend SSG + Isla React) y **Django** (Backend API REST).

---

## 🏛️ Arquitectura y Seguridad JWT

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                  NAVEGADOR CLIENTE                      │
                    │                                                         │
                    │  ┌───────────────────────────────────────────────────┐  │
                    │  │ Astro (SSG)                                       │  │
                    │  │ /activities                                       │  │
                    │  │ /activities/:id                                   │  │
                    │  └─────────────────────────┬─────────────────────────┘  │
                    │                            │ monta e hidrata            │
                    │  ┌─────────────────────────▼─────────────────────────┐  │
                    │  │ Isla React (IslaInscripcion.jsx)                  │  │
                    │  │                                                   │  │
                    │  │  • Access Token  : Solo en memoria (RAM)          │  │
                    │  │  • Refresh Token : Cookie HttpOnly (SameSite=Lax) │  │
                    │  └─────────────────────────┬─────────────────────────┘  │
                    └────────────────────────────┼────────────────────────────┘
                                                 │ HTTPS / HTTP
                                                 │ Header: Authorization: Bearer <token>
                                                 │ Cookie: refresh_token=<secreto>
                                                 ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │                   BACKEND (Django REST)                 │
                    │                                                         │
                    │   /api/v1/auth/*     -> Registro, Login, Refresh, Logout│
                    │   /api/v1/me/*       -> Perfil e Inscripciones usuario  │
                    │   /api/v1/activities -> Catálogo público de actividades │
                    │                                                         │
                    │  ┌───────────────────────────────────────────────────┐  │
                    │  │                    Base de Datos                  │  │
                    │  │  • Actividad                                      │  │
                    │  │  • Participante (1-a-1 con auth.User)             │  │
                    │  │  • Inscripcion (relación N:M)                     │  │
                    │  │  • RefreshToken (solo hash SHA-256 almacenado)    │  │
                    │  └───────────────────────────────────────────────────┘  │
                    └─────────────────────────────────────────────────────────┘
```

### Respuestas a Decisiones de Diseño Clave

1. **¿Dónde se guarda cada dato y por qué?**
   - **Access Token:** Se almacena **exclusivamente en memoria RAM** (variable local dentro del módulo JS de React). Nunca en `localStorage` ni `sessionStorage` para mitigar vulnerabilidades de robo de tokens vía ataques **XSS (Cross-Site Scripting)**.
   - **Refresh Token:** Se almacena en una cookie con banderas **`HttpOnly`** (inaccesible desde cualquier script JavaScript) y **`SameSite=Lax`**.
   - **Hash del Refresh Token:** En la base de datos se almacena **únicamente el hash SHA-256** del token, nunca el secreto en texto plano. Si la base de datos fuera comprometida, los atacantes no podrían usar los tokens para autenticarse.
   - **Contraseñas:** Hasheadas mediante el algoritmo seguro de Django (PBKDF2 con SHA-256).

2. **Rotación de Refresh Tokens:**
   - Cada vez que se invoca `POST /api/v1/auth/refresh`, el token actual se valida, se **destruye** de la base de datos y se emite un nuevo par de access token y refresh token con cookie renovada.

3. **¿Qué sucede con un Access Token tras el Logout?**
   - El logout invalida de inmediato el refresh token en la base de datos y elimina la cookie en el cliente.
   - Debido a que los JWT son *stateless*, un access token ya firmado seguirá siendo válido hasta que expire naturalmente (configurado en **5 minutos** / `ACCESS_SECONDS = 300`). Mantener una ventana corta de expiración es el estándar de la industria que evita sobrecargar la API con listas negras en memoria compartida (Redis).

---

## 🚀 Modos de Ejecución

### Modo 1: Desarrollo Local

Ideal para programar con recarga automática:

#### Backend (Django)
```bash
cd backend

# Activar entorno virtual
.\venv\Scripts\activate          # En Windows PowerShell
# source venv/bin/activate       # En Linux / Mac

# Instalar dependencias
pip install -r requirements.txt

# Aplicar migraciones
python manage.py migrate

# Cargar datos iniciales y usuarios de prueba
python seed.py

# Iniciar servidor
python manage.py runserver
```
El backend quedará en `http://127.0.0.1:8000`.

#### Frontend (Astro + React)
En otra terminal:
```bash
cd frontend
npm install
npm run dev
```
El frontend estará en `http://localhost:4321`.

---

### Modo 2: Objetivo (Docker Compose / Producción)

Levanta la topología completa (Nginx, Gunicorn, PostgreSQL y Frontend estático):

```bash
docker-compose up --build
```

Abre `http://localhost/`. Nginx se encarga de servir el frontend y redirigir `/api/*` al backend.

Para detener:
```bash
docker-compose down
```

---

## 👥 Usuarios de Prueba Precargados

Al ejecutar `python seed.py`, se crean las siguientes cuentas listas para probar el flujo de inscripción:

| Nombre | Email | Contraseña |
| :--- | :--- | :--- |
| **Ana García** | `ana@example.com` | `Demo1234!` |
| **Carlos López** | `carlos@example.com` | `Demo1234!` |

*(También es posible crear nuevas cuentas desde el botón "¿No tenés cuenta? Registrate" en la interfaz).*

---

## 📡 Catálogo de Endpoints de la API

### Autenticación (`/api/v1/auth/`)

| Método | Endpoint | Descripción | Acceso |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Crea usuario y participante | Público |
| `POST` | `/api/v1/auth/login` | Valida credenciales, emite Access JWT y cookie Refresh | Público |
| `POST` | `/api/v1/auth/refresh` | Rota el Refresh Token y entrega nuevo Access Token | Cookie `refresh_token` |
| `POST` | `/api/v1/auth/logout` | Invalida el Refresh Token en BD y elimina cookie | Cookie `refresh_token` |

### Perfil y Gestión de Inscripciones (`/api/v1/me/`)

| Método | Endpoint | Descripción | Autenticación |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/me` | Obtiene los datos del participante autenticado | `Bearer <token>` |
| `GET` | `/api/v1/me/enrollments` | Lista las inscripciones del participante | `Bearer <token>` |
| `PUT` | `/api/v1/me/enrollments/<id>` | Inscribe al participante en la actividad | `Bearer <token>` |
| `DELETE` | `/api/v1/me/enrollments/<id>/cancel` | Cancela la inscripción en la actividad | `Bearer <token>` |

### Actividades Públicas (`/api/v1/activities`)

| Método | Endpoint | Descripción | Acceso |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/activities` | Listado general de actividades | Público |
| `GET` | `/api/v1/activities/<id>` | Detalle de una actividad específica | Público |

---

## 🧪 Pruebas Automatizadas

El backend incluye tests unitarios y de integración para validar todo el flujo de autenticación, persistencia y seguridad:

```bash
cd backend
python manage.py test
```

Resultados cubiertos:
- Registro de nuevo usuario y control de email duplicado (409).
- Login exitoso (Access Token + Cookie HttpOnly) y rechazo ante credenciales erróneas (401).
- Rotación efectiva del refresh token.
- Invalidación de sesión con logout.
- Acceso denegado a endpoints privados sin Bearer token.
- Flujo completo de inscripción, prevención de sobre-inscripción y cancelación.
