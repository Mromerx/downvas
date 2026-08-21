# DownVas Web

Descarga cursos de Canvas LMS a traves de una interfaz web.

## Requisitos

- Python 3.10 o superior
- Una instancia de Canvas LMS
- Un token de API de Canvas

## Instalacion

1. Clona el repositorio:

```bash
git clone <url-del-repositorio>
cd downvas
```

2. Crea y activa un entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

4. Genera una clave secreta unica:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

5. Copia el archivo de ejemplo de configuracion y editalo:

```bash
cp .env.example .env
```

6. Edita `.env` y completa tus datos:

```env
SECRET_KEY=<pega la clave generada aqui>
CANVAS_URL=https://tu-instancia-canvas.com
CANVAS_TOKEN=tu-token-de-api-aqui
```

## Ejecutar

```bash
source .venv/bin/activate
python manage.py runserver
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000) en tu navegador.

## Uso

1. Ingresa tu URL de Canvas y token de API
2. Ingresa el ID del curso o la URL completa del curso
3. El arbol del curso se cargara con todos los archivos organizados por modulos, paginas y carpetas
4. Selecciona archivos usando los checkboxes (individuales o por seccion)
5. Haz clic en "Descargar seleccionados" para descargar directamente a tu navegador

## Como obtener un token de API de Canvas

1. Inicia sesion en tu instancia de Canvas
2. Ve a Cuenta > Configuracion
3. Haz clic en "Nuevo token de acceso"
4. Copia el token generado


