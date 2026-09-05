# DownVas Web

Descarga archivos de cursos de Canvas LMS a traves de una interfaz web.

## Funcionalidades

- Obtiene el arbol completo del curso desde Canvas: modulos, paginas, carpetas, tareas, discusiones y silabo
- Extrae enlaces de archivos embebidos en contenido HTML (paginas, tareas, discusiones)
- Explora y selecciona archivos mediante una vista de arbol con checkboxes (individuales, por seccion o seleccionar todo)
- Descarga archivos individuales o multiples archivos como archivo `.zip`
- Descargas paralelas (5 workers) para mayor velocidad
- Control de limite de tasa con reintentos automaticos
- Soporte multi-idioma (Ingles / Espanol)
- Diseno responsivo con barra lateral colapsable
- Sin base de datos -- toda la informacion se guarda en la sesion

## Requisitos

- Python 3.10+
- Una instancia de Canvas LMS con acceso a la API habilitado
- Un token de API de Canvas

## Instalacion

1. Clona el repositorio:

```bash
git clone <url-del-repositorio>
cd downvas
```

2. Crea y activa un entorno virtual:

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\activate
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

4. Genera una clave secreta unica:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

5. Crea tu archivo de configuracion:

macOS / Linux:

```bash
cp .env.example .env
```

Windows (PowerShell):

```powershell
copy .env.example .env
```

6. Edita `.env` y completa tus valores:

```env
SECRET_KEY=<pega la clave generada aqui>
DEBUG=false
ALLOWED_HOSTS=localhost,127.0.0.1
```

| Variable | Descripcion | Valor por defecto |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Django (requerida) | -- |
| `DEBUG` | Habilitar modo de depuracion | `false` |
| `ALLOWED_HOSTS` | Hostnames permitidos separados por coma | `localhost,127.0.0.1` |

## Ejecutar

macOS / Linux:

```bash
source .venv/bin/activate
python manage.py runserver
```

Windows (PowerShell):

```powershell
.venv\Scripts\activate
python manage.py runserver
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000) en tu navegador.

> **Nota:** Para ingresar a la aplicacion, abre `http://localhost:8000`.

## Uso

1. Ve a **Configuracion**, elige tu **Idioma** (Espanol / Ingles) e ingresa tu URL de Canvas y token de API
2. Navega a la pagina principal e ingresa el ID del curso o la URL completa del curso
3. El arbol del curso se cargara con todos los archivos organizados por modulos, paginas y carpetas
4. Selecciona archivos usando los checkboxes (individuales o por seccion)
5. Haz clic en **Descargar seleccionados** para descargar directamente a tu navegador

El idioma de la interfaz se puede cambiar en cualquier momento desde **Configuracion > Idioma**. Los cambios se aplican de inmediato y se conservan por sesion de navegador.

## Como obtener un token de API de Canvas

1. Inicia sesion en tu instancia de Canvas
2. Ve a Cuenta > Configuracion
3. Haz clic en **Nuevo token de acceso**
4. Copia el token generado

## Estructura del proyecto

```
downvas/
  manage.py                  # Punto de entrada de Django
  requirements.txt           # Dependencias (django, requests, python-dotenv)
  .env                       # Configuracion en tiempo de ejecucion
  downvas/                   # Configuracion y enrutamiento de Django
  core/                      # UI web: vistas, formularios, plantillas, archivos estaticos
  canvas_client/             # Cliente API de Canvas LMS y descargador de archivos
    api_client.py            # Cliente REST con paginacion y manejo de limite de tasa
    downloader.py            # Descargador paralelo de archivos con soporte zip
    html_parser.py           # Extrae enlaces de archivos de contenido HTML
    exceptions.py            # Jerarquia de excepciones personalizadas
    models.py                # Dataclasses: CanvasCourse, CanvasFolder, CanvasFile, CourseTree
  locale/                    # Catalogos de traduccion (en / es)
  sessions/                  # Almacenamiento de sesiones basado en archivos (gitignored)
```

Para actualizar las traducciones despues de editar cadenas:

```bash
python manage.py makemessages -l es --ignore=.venv
python manage.py compilemessages --ignore=.venv
```

## Stack tecnico

- **Backend**: Python, Django 5.0+
- **HTTP**: requests 2.31+
- **Frontend**: Plantillas Django, CSS/JS vanilla
- **Almacenamiento de sesiones**: Basado en archivos (sin base de datos)
- **Entorno**: python-dotenv
