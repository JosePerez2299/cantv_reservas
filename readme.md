# Reservas App

Reservas App es una aplicación web desarrollada en Django para la gestión de reservas de espacios. Permite la administración de usuarios (con roles y permisos diferenciados), espacios disponibles y reservas, e incluye funcionalidades avanzadas como validaciones, reportes y comandos de carga de datos de prueba.

## Índice

- Características
- Tecnologías
- Arquitectura y Estructura del Proyecto
- Instalación y Configuración
- Uso y Comandos Personalizados
- Desarrollo y Mantenimiento
- Notas y Recomendaciones
- Licencia

## Características

- Gestión de reservas de espacios con validaciones y manejo de conflictos.
- Administración de usuarios con roles (administrador, usuario).
- Panel de administración (Django Admin) integrado y personalizado.
- Generación de datos de prueba mediante comandos personalizados como:
  - `crear_usuarios_demo`
- Interfaz moderna con Tailwind CSS + DaisyUI.
- Soporte para filtros y búsquedas dentro de las reservas, espacios y usuarios.
- Registro de actividad y errores para facilitar el mantenimiento.


## Tecnologías

- **Lenguaje:** Python 3.x
- **Framework:** Django (versión 5.2 o superior)
- **Base de datos:** Postgresql.
- **Front-end:** HTML, CSS (Tailwind CSS), DaisyUI (Tailwind Library) JavaScript
- **Dependencias adicionales:**  
  - **Django:** Framework web para el desarrollo de aplicaciones web.
   - **django-filter:** Filtros avanzados en vistas y formularios.
   - **django-widget-tweaks:** Personalización de widgets en plantillas.
   - **django-compressor:** Optimización y compresión de archivos estáticos.
   - **pandas:** Procesamiento y análisis de datos para reportes.
   - **django-auditlog:** Registro automático de cambios y auditoría.
   - **django-formtools:** Formularios flexibles y personalizables.
   - **fontawesomefree:** Iconos modernos para la interfaz.
   - **pillow:** Procesamiento de imágenes.
   - **django-phonenumber-field:** Validación de números de teléfono.
   - **django-auth-ldap:** Autenticación con LDAP.
   - **psycopg[binary]:** Base de datos Postgresql.
   - **requests:** Hacer peticiones HTTP.
   - **django-environ:** Variables de entorno.

- **Herramientas de desarrollo:**
  - Tailwind CSS CLI
  - Comandos personalizados para la carga de datos y pruebas

## Arquitectura y Estructura del Proyecto

El proyecto se organiza de la siguiente forma:

```
Reservas_app/
│
├── apps/                   # Contiene las diferentes aplicaciones Django
│   ├── auth/               # Módulo para autenticación y gestión de usuarios
│   ├── core/               # Funcionalidades centrales y comandos de gestión (incluye comandos demo)
│   ├── espacios/           # Gestión de espacios (salas, ubicaciones, disponibilidad)
│   ├── logs/               # Registro y seguimiento de acciones y errores
│   ├── reportes/           # Generación de reportes
│   ├── reservas/           # Funcionalidades de reservas, validaciones, gestión de estados
│   └── usuarios/           # Administración y perfil de usuarios
│
├── config/                 # Configuración principal del proyecto Django
│   ├── asgi.py
│   ├── settings.py         # Configuración global del proyecto
│   ├── urls.py             # Ruteo global de la aplicación
│   └── wsgi.py
│
├── library/                # Librerías y utilidades compartidas entre aplicaciones
│   ├── context_proccesors/ # Procesadores para inyectar variables en las plantillas
│   ├── mixins/             # Funciones utilitarias y mixins reutilizables
│   └── utils/              # Funciones generales y helpers
│
├── static/                 # Archivos estáticos (CSS, JavaScript, imágenes)
│   ├── src/                # Archivos fuente, como el input de Tailwind CSS
│   └── css/                # Hojas de estilo compiladas
│
├── templates/              # Plantillas HTML que definen la interfaz de usuario
│   ├── base.html           # Plantilla base que se extiende en otras vistas
│   └── ...                 # Vistas específicas para reservas, usuarios, etc.
│
├── manage.py               # Script de administración de Django
├── package.json            # Configuración de dependencias de Tailwind CSS y otras herramientas en Node.js
├── requirements.txt        # Dependencias de Python
└── readme.md               # Este documento, que incluye ideas de instalación, uso e instrucciones generales
```

## Instalación y Configuración

1. **Clonar el repositorio:**
   ```bash
   git clone <URL-del-repositorio>
   cd Reservas_app
   ```

2. **Crear y activar el entorno virtual (recomendado):**
   ```bash
   python -m venv venv
   source venv/bin/activate    # en Windows (usa venv\Scripts\activate en CMD o PowerShell)
   ```

3. **Instalar dependencias de Python:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Instalar dependencias de Tailwind CSS:**
   Revisar el archivo package.json y ejecutar:
   ```bash
   npm install
   ```

5. **Compilar archivos estáticos con Tailwind CSS:**
   ```bash
   npm run build:tailwind
   ```
   (Asegúrate de tener el CLI de Tailwind correctamente configurado)

6. **Aplicar migraciones y arrancar el servidor:**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

7. **Crear un superusuario para el acceso al panel administrativo:**
   ```bash
   python manage.py createsuperuser
   ```
8. **Por defecto, los usuarios creados son usuarios normales. para darle permisos al usuario, se debe ir al panel administrativo y darle permisos al usuario. (cambiar de grupo)**
   
9. **IMPORTANTE**: Es necesario que el archivo .env se encuentre en la raiz del proyecto, con las configuraciones adecuadas para Poder correr el proyecto 

## Uso y Comandos Personalizados

La aplicación incluye varios comandos personalizados para facilitar la generación de datos de prueba y realizar tareas administrativas:

- **Crear usuarios demo:**
  ```bash
  python manage.py crear_usuarios_demo
  ```
  Este comando poblará la base de datos con usuarios de prueba sin privilegios de superusuario.

## Desarrollo y Mantenimiento

- **Estructura de código:**
  Las diferentes funcionalidades están separadas en aplicaciones (apps) específicas para facilitar su mantenimiento y escalabilidad. Cada módulo maneja una parte del proceso (usuarios, reservas, espacios, logs).

- **Plantillas y Front-end:**
  La carpeta templates contiene las vistas HTML basadas en una plantilla base (`base.html`). Elementos comunes como el menú, mensajes de alerta y formularios reutilizan componentes parciales incluidos en includes.

