"""Inicio de sesión, roles y permisos de Compás 360.

Roles:
- gh          Gestión Humana: administra todo el sistema y ve a toda la planta.
- jefe        Ve y gestiona a su equipo directo (objetivos, planes, retroalimentación)
              y evalúa a sus colaboradores.
- colaborador Se autoevalúa, evalúa a pares y a su jefe, y consulta sus propios resultados.
"""
import re
import unicodedata
from functools import wraps

from flask import abort, flash, g, redirect, request, url_for
from werkzeug.security import check_password_hash, generate_password_hash

ROLES = {"gh": "Gestión Humana", "jefe": "Jefe", "colaborador": "Colaborador"}
CLAVE_INICIAL = "Mabe2026*"     # la debe cambiar el usuario en su primer ingreso
LARGO_MINIMO_CLAVE = 8


# ---------------------------------------------------------------------
# Contraseñas y usuarios
# ---------------------------------------------------------------------
def cifrar(clave):
    """Nunca se guarda la contraseña: se guarda un hash (huella irreversible)."""
    return generate_password_hash(clave)


def clave_correcta(hash_guardado, clave):
    return check_password_hash(hash_guardado, clave)


def validar_clave_nueva(clave, confirmacion):
    errores = []
    if len(clave) < LARGO_MINIMO_CLAVE:
        errores.append(f"La contraseña debe tener al menos {LARGO_MINIMO_CLAVE} caracteres.")
    if not re.search(r"\d", clave) or not re.search(r"[A-Za-z]", clave):
        errores.append("La contraseña debe combinar letras y números.")
    if clave != confirmacion:
        errores.append("La confirmación no coincide con la contraseña nueva.")
    return errores


def generar_usuario(db, nombre):
    """Inicial del nombre + primer apellido, sin tildes: 'Carolina Ospina Ríos' -> 'cospina'."""
    limpio = unicodedata.normalize("NFD", nombre.lower())
    limpio = "".join(c for c in limpio if unicodedata.category(c) != "Mn")
    partes = re.findall(r"[a-z]+", limpio)
    if not partes:
        partes = ["usuario"]
    # con 4 palabras o más se asume nombre compuesto: 'Andrés Felipe Giraldo Ruiz' -> 'agiraldo'
    apellido = partes[2] if len(partes) >= 4 else (partes[1] if len(partes) >= 2 else "")
    base = partes[0][0] + apellido
    usuario, n = base, 2
    while db.execute("SELECT 1 FROM usuarios WHERE usuario = ?", (usuario,)).fetchone():
        usuario, n = f"{base}{n}", n + 1
    return usuario


def rol_sugerido(empleado):
    if empleado["area"] == "Gestión Humana":
        return "gh"
    return "jefe" if empleado["es_lider"] else "colaborador"


def cargar_usuario(db, usuario_id):
    """Usuario con los datos de su empleado. Devuelve None si no existe o está inactivo."""
    if not usuario_id:
        return None
    u = db.execute(
        """SELECT u.*, e.nombre, e.cargo, e.jefe_id, e.activo AS empleado_activo
           FROM usuarios u LEFT JOIN empleados e ON e.id = u.empleado_id
           WHERE u.id = ? AND u.activo = 1""", (usuario_id,)).fetchone()
    if u is None or (u["empleado_id"] and not u["empleado_activo"]):
        return None
    return u


# ---------------------------------------------------------------------
# Quién puede ver y gestionar a quién
# ---------------------------------------------------------------------
def es_gh():
    return g.usuario is not None and g.usuario["rol"] == "gh"


def equipo_directo(db, empleado_id):
    return {f["id"] for f in db.execute(
        "SELECT id FROM empleados WHERE jefe_id = ? AND activo = 1", (empleado_id,))}


def ids_visibles(db):
    """Colaboradores que el usuario puede consultar. None significa 'todos'."""
    u = g.usuario
    if u["rol"] == "gh":
        return None
    ids = {u["empleado_id"]} if u["empleado_id"] else set()
    if u["rol"] == "jefe" and u["empleado_id"]:
        ids |= equipo_directo(db, u["empleado_id"])
    return ids


def puede_ver(db, empleado_id):
    ids = ids_visibles(db)
    return ids is None or empleado_id in ids


def puede_gestionar(db, empleado_id):
    """Editar objetivos, plan de desarrollo y retroalimentación: Gestión Humana o el jefe directo."""
    u = g.usuario
    if u["rol"] == "gh":
        return True
    if u["rol"] == "jefe" and u["empleado_id"]:
        return empleado_id in equipo_directo(db, u["empleado_id"])
    return False


def exigir_gestion(db, empleado_id):
    if not puede_gestionar(db, empleado_id):
        abort(403)


def relacion_con(evaluador_emp, evaluado):
    """Relación 360° que tiene quien evalúa con el evaluado (para roles distintos de GH)."""
    if evaluado["id"] == evaluador_emp["id"]:
        return "auto"
    if evaluado["jefe_id"] == evaluador_emp["id"]:
        return "jefe"
    if evaluador_emp["jefe_id"] == evaluado["id"]:
        return "colab"
    return "par"


# ---------------------------------------------------------------------
# Decorador para proteger páginas por rol
# ---------------------------------------------------------------------
def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if g.usuario is None:
                return redirect(url_for("login", siguiente=request.path))
            if g.usuario["rol"] not in roles:
                flash("No tienes permiso para entrar a esa sección.", "error")
                return redirect(url_for("inicio"))
            return vista(*args, **kwargs)
        return envoltura
    return decorador
