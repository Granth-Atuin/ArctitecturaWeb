# Arquitecturas Web — Sistema de Inscripciones (Entrega: Adaptador de Entrada gRPC)

Este repositorio contiene la solución completa para el sistema de inscripción a actividades con **autenticación JWT** y **múltiples adaptadores de entrada** siguiendo principios de Arquitectura Hexagonal / Clean Architecture:
1. **Frontend SSG + Isla React** (Astro + React) consumiendo la API REST.
2. **API REST HTTP** (Django).
3. **Adaptador de Entrada gRPC** (puerto `50051`) que procesa inscripciones bajo el mismo dominio de negocio y con la misma identidad JWT en la metadata.

---

## 🏛️ Topología y Adaptadores de Entrada

```
                                  ENTRADAS AL SISTEMA
                                  
     ┌────────────────────────┐                   ┌────────────────────────┐
     │   Navegador Cliente    │                   │ Cliente gRPC / grpcurl │
     │  (Astro SSG + React)   │                   │  (Scripts / Servicios) │
     └───────────┬────────────┘                   └───────────┬────────────┘
                 │ HTTP (REST)                                │ gRPC (Protobuf)
                 │ Bearer Token / Cookie HttpOnly             │ Metadata: authorization
                 ▼                                            ▼
     ┌────────────────────────┐                   ┌────────────────────────┐
     │    Django HTTP API     │                   │   Servicio gRPC        │
     │      (Puerto 8000)     │                   │   (Puerto 50051)       │
     └───────────┬────────────┘                   └───────────┬────────────┘
                 │                                            │
                 └──────────────────────┬─────────────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │      REGLAS DE NEGOCIO      │
                         │      (Dominio / Modelos)    │
                         │                             │
                         │  • Actividad (cupos)        │
                         │  • Participante / User      │
                         │  • Inscripción (idempotente)│
                         │  • Validación JWT           │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │   Base de Datos (Postgres)  │
                         └─────────────────────────────┘
```

---

## ⚡ Adaptador de Entrada gRPC

El adaptador gRPC expone la lógica de inscripción en un proceso independiente (puerto `50051`), demostrando cómo distintos protocolos activan el mismo núcleo de negocio:

### 1. Contrato Protobuf (`inscripciones.proto`)

Ubicado en `backend/actividades/grpc/inscripciones.proto`:

```protobuf
syntax = "proto3";

package inscripciones.v1;

service Inscripciones {
  // Idempotente, idéntico a PUT /api/v1/me/enrollments/{actividad_id}.
  // Identidad: metadata "authorization: Bearer <access JWT>".
  rpc Inscribir(InscribirRequest) returns (InscribirResponse);
}

message InscribirRequest {
  string actividad_id = 1;
}

message InscribirResponse {
  string actividad_id = 1;
  string participante_id = 2;
  string inscripta_en = 3;  // ISO 8601
  bool creada = 4;          // false si ya estaba inscripta
}
```

### 2. Autenticación y Mapeo de Errores

El servicio gRPC (`ServicioInscripciones` en `backend/actividades/grpc/servicio.py`) implementa la misma política de seguridad que la API HTTP:
- **Identidad**: Extrae el token JWT Bearer desde la metadata gRPC (`authorization: Bearer <token>`). Si está ausente o es inválido, devuelve el código `UNAUTHENTICATED`.
- **Idempotencia**: Si el usuario ya está inscripto, la operación no falla y devuelve `creada = false` con los datos de su inscripción.
- **Validación**:
  - `INVALID_ARGUMENT`: Si `actividad_id` no es un identificador entero válido o es menor o igual a cero.
  - `NOT_FOUND`: Si la actividad solicitada no existe en la base de datos.
  - `FAILED_PRECONDITION`: Si la capacidad de la actividad se encuentra agotada.

### 3. Ejecución del Servidor gRPC

#### Localmente (modo desarrollo):
```bash
cd backend
.\venv\Scripts\activate           # Windows
# source venv/bin/activate        # Linux / Mac

python manage.py servidor_grpc --puerto 50051
```

#### Con Docker Compose:
El servicio `grpc` viene configurado en `docker-compose.yml`:
```bash
docker compose up --build
```
El servidor gRPC queda disponible en `localhost:50051`.

### 4. Prueba con `grpcurl`

1. Obtener un Access Token desde la API HTTP:
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ana@example.com","password":"DemoPassword123!"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

2. Invocar el método `Inscribir` por gRPC:
```bash
grpcurl -plaintext \
  -proto backend/actividades/grpc/inscripciones.proto \
  -H "authorization: Bearer $TOKEN" \
  -d '{"actividad_id": "1"}' \
  localhost:50051 inscripciones.v1.Inscripciones/Inscribir
```

---

## 🔒 Seguridad y JWT

1. **Access Token:** Se almacena **exclusivamente en memoria RAM** en el frontend (React) o en variables del cliente gRPC. Tiene una vida corta (**5 minutos**) y se envía en el header `Authorization: Bearer <token>` (en HTTP) o en la metadata gRPC.
2. **Refresh Token:** Se almacena en una cookie con banderas **`HttpOnly`** y **`SameSite=Lax`**. En base de datos se guarda solo su **hash SHA-256**.
3. **Rotación:** Cada petición a `/api/v1/auth/refresh` destruye el token anterior y emite uno nuevo.

---

## 👥 Usuarios de Prueba Precargados

Al ejecutar `python seed.py` (o en la inicialización de la base):

| Nombre | Email | Contraseña |
| :--- | :--- | :--- |
| **Ana García** | `ana@example.com` | `Demo1234!` |
| **Carlos López** | `carlos@example.com` | `Demo1234!` |

---

## 📡 Catálogo de Endpoints de la API REST

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

El backend incluye tests unitarios y de integración tanto para el flujo HTTP/JWT como para el servicio gRPC:

```bash
cd backend
python manage.py test
```

### Cobertura verificada (11 tests):
- ✅ Registro de usuario y control de emails duplicados (409).
- ✅ Login con emisión de JWT y cookie HttpOnly, y rechazo ante credenciales erróneas (401).
- ✅ Rotación de refresh tokens e invalidación con logout.
- ✅ Inscripción HTTP, prevención de sobre-inscripción y cancelación.
- ✅ **gRPC: Inscripción exitosa e idempotencia (creada = True / False sin duplicar registros)**.
- ✅ **gRPC: Mapeo de errores de dominio a códigos de estado gRPC (`FAILED_PRECONDITION`, `NOT_FOUND`, `INVALID_ARGUMENT`, `UNAUTHENTICATED`)**.
- ✅ **gRPC: Rechazo de token inválido o expirado en la metadata**.
