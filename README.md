# Arquitecturas Web - Sistema de Inscripción
Este repositorio contiene la implementación del sistema de actividades e inscripciones, incluyendo el frontend en Astro y el backend en Django.
## Modos de Ejecución
Para poder correr este proyecto, existen dos modos dependiendo de tus necesidades:
### 1. Modo Desarrollo
Este modo es ideal para programar y hacer cambios en tiempo real, conservando herramientas habituales de recarga automática.
**Pasos:**
1. Levanta la base de datos PostgreSQL utilizando Docker (opcional, si prefieres usar SQLite, puedes omitir configurar `DB_NAME` en el entorno).
   bash
   docker-compose up -d db
2. Inicia el backend (Django):
   bash
   cd backend
   source .venv/bin/activate
   python manage.py migrate
   python manage.py runserver
3. Inicia el frontend (Astro/Vite):
   bash
   cd frontend
   npm install
   npm run dev
### 2. Modo Objetivo (Producción/Reproducible)
Este modo levanta la topología completa usando Docker Compose. En este modo:
- **Nginx** sirve como el **único punto de entrada** (Puerto 80).
- El frontend (Astro) se compila a archivos estáticos (SSG) al iniciar.
- El backend corre con **Gunicorn**.
- La persistencia se maneja con un contenedor de **PostgreSQL** y su volumen de datos.
**Pasos:**
1. Asegúrate de tener los puertos 80 y 5432 libres.
2. Desde la raíz del repositorio, ejecuta:
   bash
   docker-compose up --build
3. Abre tu navegador en `http://localhost/`. Las peticiones a la API serán automáticamente redirigidas por Nginx hacia el backend a través de `/api/*`.
Para detener la ejecución y preservar los datos:
bash
docker-compose down

Si deseas destruir también los datos almacenados en la base de datos PostgreSQL:
bash
docker-compose down -v
