# Compás 360 · Sistema de evaluación del desempeño

Sistema de información para gestión humana que permite evaluar el desempeño de los colaboradores por **competencias** y **objetivos (APO)**, con **evaluación 360°** y **planes de desarrollo** basados en el modelo **SECI de Nonaka y Takeuchi**.

Propuesta académica diseñada para **mabe Colombia S.A.S., planta Manizales**. No es un sistema oficial de la empresa; los datos de ejemplo son ficticios.

**Tecnología:** Python · Flask · SQLite · HTML/CSS (plantillas Jinja)

---

## 1. Qué necesitas instalar

| Programa | Para qué | Dónde descargarlo |
|---|---|---|
| **Python 3.10 o superior** | Ejecutar el sistema | https://www.python.org/downloads/ |
| **Visual Studio Code** (recomendado) | Ver y editar el código | https://code.visualstudio.com/ |

> **Importante al instalar Python en Windows:** en la primera pantalla del instalador marca la casilla **"Add python.exe to PATH"** antes de presionar *Install Now*. Si no la marcas, la terminal no reconocerá el comando `python`.

Para comprobar que Python quedó bien instalado, abre una terminal (PowerShell) y escribe:

```powershell
python --version
```

Debe mostrar algo como `Python 3.12.4`. Si dice que no se reconoce el comando, revisa la sección de [Problemas frecuentes](#7-problemas-frecuentes).

**No necesitas instalar SQLite:** ya viene incluido en Python.

---

## 2. Preparar el proyecto

1. Copia la carpeta del proyecto en tu computador, por ejemplo en `Documentos\Trabajo Final TH`.
2. Abre esa carpeta en VS Code: **File → Open Folder…**
3. Abre una terminal dentro de VS Code: **Terminal → New Terminal** (o `Ctrl + ñ`).

La carpeta debe verse así:

```
Trabajo Final TH/
├── app.py               ← aplicación principal (rutas y páginas)
├── calculos.py          ← reglas del modelo: pesos, puntajes, clasificación, SECI
├── permisos.py          ← inicio de sesión, roles y permisos
├── database.py          ← conexión con SQLite y comandos para crear la base
├── datos_ejemplo.py     ← competencias, escala BARS y datos ficticios de prueba
├── schema.sql           ← estructura de las tablas de la base de datos
├── requirements.txt     ← librerías que necesita el proyecto
├── README.md            ← este archivo
├── static/
│   ├── css/estilos.css  ← diseño visual
│   └── js/evaluar.js    ← comportamiento del formulario de evaluación
└── templates/           ← páginas HTML (Jinja)
```

> Si recibiste la carpeta `venv` o el archivo `compas360.db`, puedes borrarlos: los vas a crear de nuevo en los siguientes pasos. La carpeta `venv` de otro computador no funciona en el tuyo.

---

## 3. Instalación (solo la primera vez)

Todos los comandos se escriben en la terminal, **dentro de la carpeta del proyecto**.

### Paso 1. Crear el entorno virtual

El entorno virtual es una carpeta (`venv`) donde se instalan las librerías solo para este proyecto.

```powershell
python -m venv venv
```

### Paso 2. Activar el entorno virtual

**Windows (PowerShell):**

```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**

```cmd
venv\Scripts\activate.bat
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

Sabrás que funcionó porque al inicio de la línea de la terminal aparece **`(venv)`**.

> Si PowerShell muestra un error rojo que dice *"la ejecución de scripts está deshabilitada en este sistema"*, ejecuta primero este comando y vuelve a intentar:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```
> Este permiso dura solo mientras esté abierta esa terminal.

### Paso 3. Instalar las librerías

```powershell
pip install -r requirements.txt
```

Si por alguna razón no tienes el archivo `requirements.txt`, basta con:

```powershell
pip install flask
```

### Paso 4. Crear la base de datos con los datos de ejemplo

```powershell
flask --app app seed-db
```

Debe responder algo así:

```
Base de datos creada con datos de ejemplo:
  empleados: 14
  evaluaciones: 48
  puntajes: 314
  objetivos: 39
  acciones_desarrollo: 8
  retroalimentaciones: 2
  usuarios: 15
```

Se crea el archivo **`compas360.db`**: esa es la base de datos SQLite.

---

## 4. Ejecutar el sistema

Con el entorno virtual activo `(venv)`:

```powershell
python app.py
```

Abre en el navegador: **http://127.0.0.1:5000**

Para detener el servidor, presiona `Ctrl + C` en la terminal.

### Cada vez que vuelvas a trabajar

No hay que instalar nada de nuevo. Solo:

1. Abrir la carpeta del proyecto en VS Code.
2. Activar el entorno virtual (Paso 2).
3. Ejecutar `python app.py`.

---

## 5. Usuarios de prueba

Todos los usuarios de ejemplo tienen la contraseña **`Mabe2026*`**.

| Usuario | Persona (ficticia) | Rol |
|---|---|---|
| `jzuluaga` | Juliana Zuluaga Henao · Jefe de Gestión Humana | Gestión Humana |
| `vrestrepo` | Valentina Restrepo Gil · Analista de Gestión Humana | Gestión Humana |
| `cospina` | Carolina Ospina Ríos · Jefe de Producción | Jefe |
| `agiraldo` | Andrés Felipe Giraldo · Supervisor de ensamble | Jefe |
| `mvalencia` | Mauricio Valencia Cardona · Coordinador de mantenimiento | Jefe |
| `rsalazar` | Ricardo Salazar Mejía · Coordinador de calidad | Jefe |
| `fcastano` | Felipe Castaño Arias · Coordinador de logística | Jefe |
| `jmarin` | Jhon Fredy Marín · Operario de ensamble | Colaborador |
| `larango` | Luisa Fernanda Arango · Operaria de ensamble | Colaborador |
| `dhenao` | Diana Marcela Henao · Operaria de espumado | Colaborador |
| `scardona` | Sebastián Cardona López · Técnico de mantenimiento | Colaborador |
| `pgomez` | Paula Andrea Gómez · Inspectora de calidad | Colaborador |
| `nrios` | Natalia Ríos Quintero · Analista de logística | Colaborador |
| `cloaiza` | Camilo Loaiza Duque · Ingeniero de procesos | Colaborador |

Además existe el usuario **`admin`** (contraseña `Mabe2026*`), un administrador de Gestión Humana que el sistema obliga a cambiar la contraseña en su primer ingreso.

Para probar rápido los tres roles: **`jzuluaga`** (Gestión Humana), **`agiraldo`** (Jefe) y **`jmarin`** (Colaborador).

### Qué puede hacer cada rol

| Sección | Gestión Humana | Jefe | Colaborador |
|---|---|---|---|
| **Panel** | Toda la planta, con filtro por área | Solo su equipo directo | No lo ve |
| **Colaboradores** | Registrar, editar, retirar y asignar roles | No lo ve | No lo ve |
| **Evaluar** | A cualquiera, eligiendo la relación (por ejemplo, para digitar formatos en papel) | A cualquiera; la relación la decide el sistema según el organigrama | Igual que el jefe |
| **Resultados 360°** | De todos | Los suyos y los de su equipo | Solo los suyos |
| **Objetivos y planes de desarrollo** | Edita los de todos | Edita los de su equipo (no los propios) | Solo consulta los suyos |
| **Cómo funciona** | Sí | Sí | Sí |

---

## 6. Módulos del sistema

- **Panel de indicadores:** desempeño promedio, distribución por clasificación, promedio por área y por competencia, matriz de competencias frente a resultados, personas que requieren atención y mejores resultados.
- **Colaboradores:** registro con cargo, área, nivel de talento (NT), jefe inmediato y rol de acceso. Si una persona ya tiene evaluaciones, al retirarla queda inactiva para conservar su historial.
- **Evaluar:** evaluación 360° por competencias con escala de conductas (BARS) de 1 a 5. Muestra las evaluaciones pendientes.
- **Resultados 360°:** puntaje final, clasificación, resultado por competencia y por fuente, fortalezas, oportunidades de mejora, brechas de percepción, objetivos (APO) y comentarios.
- **Planes de desarrollo:** acciones por competencia según el modelo SECI, sugerencias automáticas, estados, reunión de retroalimentación y seguimiento.
- **Cómo funciona:** flujo de operación, reglas de cálculo y escala BARS.

### Reglas de cálculo principales

Todas se pueden cambiar en el archivo **`calculos.py`**.

- **Pesos 360°:** jefe inmediato 40 %, pares 25 %, colaboradores a cargo 20 %, autoevaluación 15 %. Si falta una fuente, su peso se reparte entre las demás.
- **Puntaje final** = 60 % competencias + 40 % objetivos.
- **Clasificación:** Sobresaliente (90 a 100) · Cumple (75 a 89,9) · En desarrollo (60 a 74,9) · Requiere mejora (menos de 60).
- **Objetivos:** si "mayor es mejor", el cumplimiento es *resultado ÷ meta*; si "menor es mejor" (defectos, tiempos, accidentes), es *meta ÷ resultado*. Cada objetivo tiene un tope de 120 %.
- **Fortaleza:** competencia con 4,0 o más · **Oportunidad de mejora:** menos de 3,5 · **Brecha de percepción:** diferencia de 1 punto o más entre la autoevaluación y lo que opinan los demás.

---

## 7. Problemas frecuentes

| Problema | Solución |
|---|---|
| `python` no se reconoce como comando | Python no quedó en el PATH. Reinstálalo marcando **"Add python.exe to PATH"**, o prueba con `py` en lugar de `python` (por ejemplo `py -m venv venv`). |
| Error rojo al activar el entorno: *"la ejecución de scripts está deshabilitada"* | Ejecuta `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` y vuelve a activar. |
| `flask` no se reconoce como comando | El entorno virtual no está activo: revisa que aparezca `(venv)` y actívalo (Paso 2). |
| `ModuleNotFoundError: No module named 'flask'` | Activa el entorno virtual y ejecuta `pip install -r requirements.txt`. |
| `sqlite3.OperationalError: no such table` | La base de datos no existe o es de una versión anterior. Ejecuta `flask --app app seed-db`. |
| La página no carga en http://127.0.0.1:5000 | Revisa que la terminal muestre `Running on http://127.0.0.1:5000` y que no la hayas cerrado. |
| `Address already in use` o el puerto 5000 está ocupado | Ya hay otro servidor abierto. Ciérralo con `Ctrl + C` en la otra terminal, o ejecuta `flask --app app run --port 5001` y abre http://127.0.0.1:5001 |
| Olvidé la contraseña que cambié | Ingresa con un usuario de Gestión Humana, ve a **Colaboradores → Editar** y marca **"Restablecer la contraseña a la inicial"**. |
| Quiero volver a los datos de ejemplo | Detén el servidor y ejecuta `flask --app app seed-db`. **Ojo:** borra todo lo que hayas registrado. |

### Comandos de la base de datos

| Comando | Qué hace |
|---|---|
| `flask --app app seed-db` | Crea la base **con** los 14 colaboradores de ejemplo, evaluaciones, objetivos y planes. |
| `flask --app app init-db` | Crea la base **vacía** (solo el modelo: competencias, escala BARS, pesos y períodos) con el usuario `admin`. |

Los dos comandos **borran la base anterior** y la crean de nuevo.

---

## 8. Recomendaciones

- Instala en VS Code la extensión **SQLite Viewer** para abrir `compas360.db` y ver las tablas por dentro.
- Instala la extensión **Better Jinja** para que VS Code reconozca la sintaxis de las plantillas (`{{ }}` y `{% %}`) y no marque errores falsos.
- Antes de pasar el proyecto a otra persona, no incluyas la carpeta `venv` ni `__pycache__`: cada quien crea su propio entorno con los pasos de este README.
- El servidor de Flask (`python app.py`) es solo para desarrollo y presentaciones, no para uso en producción.
