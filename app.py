from datetime import date, timedelta

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for

import calculos
import database
import permisos as perm

AREAS = ["Producción", "Mantenimiento", "Calidad", "Logística", "Ingeniería", "Gestión Humana"]
NIVELES = ["NT 2", "NT 3", "NT 4", "NT 5", "NT 6", "NT 7"]

app = Flask(__name__)
app.config["SECRET_KEY"] = "cambia-esta-clave"  # necesaria para la sesión y los mensajes
database.init_app(app)

TODOS = {"gh", "jefe", "colaborador"}
# Pestañas del menú: (nombre de la función, texto visible, roles que la ven)
MENU = [
    ("inicio", "Panel", {"gh", "jefe"}),
    ("colaboradores", "Colaboradores", {"gh"}),
    ("evaluar", "Evaluar", TODOS),
    ("resultados", "Resultados 360°", TODOS),
    ("planes", "Planes de desarrollo", TODOS),
    ("metodologia", "Cómo funciona", TODOS),
]


# ---------------------------------------------------------------------
# Sesión: cada petición verifica quién es el usuario
# ---------------------------------------------------------------------
@app.before_request
def verificar_sesion():
    g.usuario = perm.cargar_usuario(database.get_db(), session.get("usuario_id"))
    if request.endpoint in ("login", "static"):
        return None
    if g.usuario is None:
        session.pop("usuario_id", None)
        siguiente = request.path if request.method == "GET" and request.path != "/" else None
        return redirect(url_for("login", siguiente=siguiente))
    if g.usuario["debe_cambiar"] and request.endpoint not in ("cuenta", "logout"):
        flash("Por seguridad, cambia tu contraseña inicial antes de continuar.", "error")
        return redirect(url_for("cuenta"))
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario:
        return redirect(url_for("inicio"))
    siguiente = request.args.get("siguiente") or ""
    if request.method == "POST":
        db = database.get_db()
        fila = db.execute("SELECT * FROM usuarios WHERE usuario = ?",
                          (request.form.get("usuario", "").strip().lower(),)).fetchone()
        usuario = perm.cargar_usuario(db, fila["id"]) if fila else None
        # Mismo mensaje si falla el usuario o la clave: no se revela cuál de los dos existe
        if usuario and perm.clave_correcta(fila["clave_hash"], request.form.get("clave", "")):
            session.clear()
            session["usuario_id"] = usuario["id"]
            destino = siguiente if siguiente.startswith("/") and not siguiente.startswith("//") else url_for("inicio")
            return redirect(destino)
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("login.html", siguiente=siguiente)


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.")
    return redirect(url_for("login"))


@app.route("/cuenta", methods=["GET", "POST"])
def cuenta():
    if request.method == "POST":
        db = database.get_db()
        fila = db.execute("SELECT clave_hash FROM usuarios WHERE id = ?", (g.usuario["id"],)).fetchone()
        actual, nueva, confirmar = (request.form.get(k, "") for k in ("actual", "nueva", "confirmar"))
        errores = []
        if not perm.clave_correcta(fila["clave_hash"], actual):
            errores.append("La contraseña actual no es correcta.")
        errores += perm.validar_clave_nueva(nueva, confirmar)
        if nueva and (nueva == actual or nueva == perm.CLAVE_INICIAL):
            errores.append("La contraseña nueva debe ser distinta de la actual y de la inicial.")
        if errores:
            for e in errores:
                flash(e, "error")
        else:
            db.execute("UPDATE usuarios SET clave_hash = ?, debe_cambiar = 0 WHERE id = ?",
                       (perm.cifrar(nueva), g.usuario["id"]))
            db.commit()
            flash("Contraseña actualizada.")
            return redirect(url_for("inicio"))
    return render_template("cuenta.html")


# ---------------------------------------------------------------------
# Período de trabajo y datos comunes
# ---------------------------------------------------------------------
def periodo_actual():
    """Período elegido por el usuario; si no ha elegido, el período abierto más reciente."""
    if "periodo" in session:
        return session["periodo"]
    fila = database.get_db().execute(
        "SELECT id FROM periodos ORDER BY estado = 'abierto' DESC, id DESC LIMIT 1"
    ).fetchone()
    return fila["id"] if fila else None


@app.template_filter("dec")
def formato_decimal(valor, decimales=1):
    """Número con coma decimal, como se escribe en Colombia: 3.75 -> '3,8'."""
    if valor is None:
        return "—"
    return f"{valor:.{decimales}f}".replace(".", ",")


@app.context_processor
def datos_comunes():
    """Variables disponibles en todas las plantillas."""
    periodos = database.get_db().execute("SELECT id, estado FROM periodos ORDER BY id").fetchall()
    u = g.get("usuario")
    menu = [(e, n) for e, n, roles in MENU if u and u["rol"] in roles]
    return {"menu": menu, "periodos": periodos, "periodo_actual": periodo_actual(),
            "usuario": u, "es_gh": bool(u and u["rol"] == "gh"), "roles": perm.ROLES}


@app.post("/periodo")
def cambiar_periodo():
    session["periodo"] = request.form["periodo"]
    volver = request.form.get("volver", "/")
    return redirect(volver if volver.startswith("/") else url_for("inicio"))


def periodo_abierto(db, per):
    fila = db.execute("SELECT estado FROM periodos WHERE id = ?", (per,)).fetchone()
    return fila is not None and fila["estado"] == "abierto"


# ---------------------------------------------------------------------
# Panel de indicadores
# ---------------------------------------------------------------------
@app.route("/")
def inicio():
    """Gestión Humana ve toda la planta (o un área); cada jefe ve a su equipo directo."""
    if g.usuario["rol"] == "colaborador":
        return redirect(url_for("resultados"))
    db = database.get_db()
    per = periodo_actual()
    area, ids = "", None
    if perm.es_gh():
        area = request.args.get("area", "")
        if area not in AREAS:
            area = ""
    else:
        ids = perm.equipo_directo(db, g.usuario["empleado_id"])
    resumen = calculos.resumen_periodo(db, per, area or None, ids)

    sql = """SELECT COUNT(*) AS total, SUM(a.estado = 'Cumplida') AS cumplidas,
                    SUM(a.estado <> 'Cumplida' AND a.fecha_limite < date('now')) AS vencidas
             FROM acciones_desarrollo a JOIN empleados e ON e.id = a.empleado_id
             WHERE a.periodo_id = ? AND e.activo = 1 AND (? = '' OR e.area = ?)"""
    params = [per, area, area]
    if ids is not None:
        lista = list(ids) or [0]
        sql += f" AND e.id IN ({','.join('?' * len(lista))})"
        params += lista
    acciones = db.execute(sql, params).fetchone()
    return render_template("inicio.html", s=resumen, acciones=acciones, area=area, areas=AREAS,
                           clasificar=calculos.clasificar, alcance="tu equipo" if ids is not None else None)


# ---------------------------------------------------------------------
# Módulo de colaboradores (solo Gestión Humana)
# ---------------------------------------------------------------------
@app.route("/colaboradores")
@perm.rol_requerido("gh")
def colaboradores():
    db = database.get_db()
    buscar = request.args.get("buscar", "").strip()
    area = request.args.get("area", "")
    ver_inactivos = request.args.get("inactivos") == "1"

    sql = """
        SELECT e.*, j.nombre AS jefe, u.usuario, u.rol,
               (SELECT COUNT(*) FROM evaluaciones v
                 WHERE v.empleado_id = e.id AND v.periodo_id = ?) AS num_evaluaciones,
               (SELECT COUNT(*) FROM evaluaciones v
                 WHERE v.empleado_id = e.id AND v.periodo_id = ? AND v.relacion_id IN ('auto', 'jefe')) AS auto_jefe
        FROM empleados e
        LEFT JOIN empleados j ON j.id = e.jefe_id
        LEFT JOIN usuarios u ON u.empleado_id = e.id
        WHERE 1 = 1
    """
    per = periodo_actual()
    params = [per, per]
    if not ver_inactivos:
        sql += " AND e.activo = 1"
    if buscar:
        sql += " AND (e.nombre LIKE ? OR e.cargo LIKE ?)"
        params += [f"%{buscar}%", f"%{buscar}%"]
    if area:
        sql += " AND e.area = ?"
        params.append(area)
    sql += " ORDER BY e.nombre"

    lista = db.execute(sql, params).fetchall()
    return render_template("colaboradores.html", lista=lista, areas=AREAS,
                           buscar=buscar, area=area, ver_inactivos=ver_inactivos)


def leer_formulario_empleado(empleado_id=None):
    """Lee y valida el formulario. Devuelve (datos, lista_de_errores)."""
    f = request.form
    datos = {
        "nombre": f.get("nombre", "").strip(),
        "cargo": f.get("cargo", "").strip(),
        "area": f.get("area", ""),
        "nivel": f.get("nivel", ""),
        "jefe_id": int(f["jefe_id"]) if f.get("jefe_id") else None,
        "es_lider": 1 if f.get("es_lider") else 0,
        "fecha_ingreso": f.get("fecha_ingreso") or None,
        "activo": 1 if f.get("activo") else 0,
        "rol": f.get("rol", "colaborador"),
    }
    errores = []
    if not datos["nombre"]:
        errores.append("Escribe el nombre completo.")
    if not datos["cargo"]:
        errores.append("Escribe el cargo.")
    if datos["area"] not in AREAS:
        errores.append("Elige un área válida.")
    if datos["nivel"] not in NIVELES:
        errores.append("Elige un nivel de talento válido.")
    if datos["jefe_id"] is not None and datos["jefe_id"] == empleado_id:
        errores.append("Una persona no puede ser su propio jefe.")
    if datos["rol"] not in perm.ROLES:
        errores.append("Elige un rol válido.")
    if datos["rol"] == "jefe" and not datos["es_lider"]:
        errores.append("El rol Jefe es para quien tiene personal a cargo: marca esa casilla o elige otro rol.")
    return datos, errores


def opciones_jefe(excluir_id=None):
    return database.get_db().execute(
        "SELECT id, nombre, cargo FROM empleados WHERE activo = 1 AND id IS NOT ? ORDER BY nombre",
        (excluir_id,)).fetchall()


@app.route("/colaboradores/nuevo", methods=["GET", "POST"])
@perm.rol_requerido("gh")
def colaboradores_nuevo():
    datos = {"area": AREAS[0], "nivel": "NT 7", "activo": 1, "rol": "colaborador"}
    if request.method == "POST":
        datos, errores = leer_formulario_empleado()
        if not errores:
            db = database.get_db()
            cur = db.execute(
                """INSERT INTO empleados (nombre, cargo, area, nivel, jefe_id, es_lider, fecha_ingreso, activo)
                   VALUES (:nombre, :cargo, :area, :nivel, :jefe_id, :es_lider, :fecha_ingreso, :activo)""",
                datos)
            # Cada colaborador recibe su usuario con la contraseña inicial (debe cambiarla al entrar)
            usuario = perm.generar_usuario(db, datos["nombre"])
            db.execute("INSERT INTO usuarios (usuario, clave_hash, rol, empleado_id) VALUES (?, ?, ?, ?)",
                       (usuario, perm.cifrar(perm.CLAVE_INICIAL), datos["rol"], cur.lastrowid))
            db.commit()
            flash(f"Colaborador registrado: {datos['nombre']}. Usuario: {usuario} · "
                  f"contraseña inicial: {perm.CLAVE_INICIAL} (se le pedirá cambiarla al ingresar).")
            return redirect(url_for("colaboradores"))
        for e in errores:
            flash(e, "error")
    return render_template("colaborador_form.html", datos=datos, nuevo=True,
                           areas=AREAS, niveles=NIVELES, jefes=opciones_jefe())


@app.route("/colaboradores/<int:empleado_id>/editar", methods=["GET", "POST"])
@perm.rol_requerido("gh")
def colaboradores_editar(empleado_id):
    db = database.get_db()
    fila = db.execute(
        """SELECT e.*, u.usuario, u.rol FROM empleados e LEFT JOIN usuarios u ON u.empleado_id = e.id
           WHERE e.id = ?""", (empleado_id,)).fetchone()
    if fila is None:
        abort(404)
    datos = dict(fila)
    if request.method == "POST":
        datos, errores = leer_formulario_empleado(empleado_id)
        if empleado_id == g.usuario["empleado_id"] and datos["rol"] != "gh":
            errores.append("No puedes quitarte a ti mismo el rol de Gestión Humana.")
        if not errores:
            datos["id"] = empleado_id
            db.execute(
                """UPDATE empleados SET nombre = :nombre, cargo = :cargo, area = :area, nivel = :nivel,
                          jefe_id = :jefe_id, es_lider = :es_lider, fecha_ingreso = :fecha_ingreso, activo = :activo
                   WHERE id = :id""",
                datos)
            if fila["usuario"]:
                db.execute("UPDATE usuarios SET rol = ? WHERE empleado_id = ?", (datos["rol"], empleado_id))
                if request.form.get("restablecer"):
                    db.execute("UPDATE usuarios SET clave_hash = ?, debe_cambiar = 1 WHERE empleado_id = ?",
                               (perm.cifrar(perm.CLAVE_INICIAL), empleado_id))
                    flash(f"Contraseña restablecida a la inicial ({perm.CLAVE_INICIAL}).")
            else:
                usuario = perm.generar_usuario(db, datos["nombre"])
                db.execute("INSERT INTO usuarios (usuario, clave_hash, rol, empleado_id) VALUES (?, ?, ?, ?)",
                           (usuario, perm.cifrar(perm.CLAVE_INICIAL), datos["rol"], empleado_id))
                flash(f"Se creó el usuario {usuario} con la contraseña inicial.")
            db.commit()
            flash(f"Cambios guardados: {datos['nombre']}.")
            return redirect(url_for("colaboradores"))
        for e in errores:
            flash(e, "error")
        datos["id"] = empleado_id
        datos["usuario"] = fila["usuario"]
    num_eval = db.execute("SELECT COUNT(*) FROM evaluaciones WHERE empleado_id = ?", (empleado_id,)).fetchone()[0]
    return render_template("colaborador_form.html", datos=datos, nuevo=False, num_eval=num_eval,
                           areas=AREAS, niveles=NIVELES, jefes=opciones_jefe(empleado_id))


@app.post("/colaboradores/<int:empleado_id>/eliminar")
@perm.rol_requerido("gh")
def colaboradores_eliminar(empleado_id):
    """Si la persona ya tiene evaluaciones, se marca como inactiva para conservar el historial."""
    db = database.get_db()
    fila = db.execute("SELECT nombre FROM empleados WHERE id = ?", (empleado_id,)).fetchone()
    if fila is None:
        abort(404)
    if empleado_id == g.usuario["empleado_id"]:
        flash("No puedes retirarte a ti mismo del sistema.", "error")
        return redirect(url_for("colaboradores"))
    tiene_historial = db.execute(
        "SELECT COUNT(*) FROM evaluaciones WHERE empleado_id = ?", (empleado_id,)).fetchone()[0] > 0
    if tiene_historial:
        db.execute("UPDATE empleados SET activo = 0 WHERE id = ?", (empleado_id,))
        flash(f"{fila['nombre']} quedó inactivo: ya no puede ingresar, pero se conserva su historial.")
    else:
        db.execute("DELETE FROM empleados WHERE id = ?", (empleado_id,))  # su usuario se borra en cascada
        flash(f"{fila['nombre']} fue eliminado.")
    db.commit()
    return redirect(url_for("colaboradores"))


# ---------------------------------------------------------------------
# Módulo de evaluación 360°
# ---------------------------------------------------------------------
def competencias_con_niveles():
    """Competencias en orden, cada una con sus 5 conductas (escala BARS)."""
    db = database.get_db()
    comps = [dict(c) for c in db.execute("SELECT * FROM competencias ORDER BY orden")]
    niveles = {}
    for n in db.execute("SELECT * FROM niveles_competencia ORDER BY nivel"):
        niveles.setdefault(n["competencia_id"], []).append(n["descripcion"])
    for c in comps:
        c["niveles"] = niveles.get(c["id"], [])
    return comps


def evaluaciones_pendientes(db, per, yo=None):
    """Gestión Humana: a quién le falta auto o jefe en toda la planta.
    Otros roles: solo lo que le toca hacer a esa persona."""
    if yo is None:
        filas = db.execute(
            """SELECT e.id, e.nombre,
                      EXISTS(SELECT 1 FROM evaluaciones v WHERE v.empleado_id = e.id
                             AND v.periodo_id = ? AND v.relacion_id = 'auto') AS tiene_auto,
                      EXISTS(SELECT 1 FROM evaluaciones v WHERE v.empleado_id = e.id
                             AND v.periodo_id = ? AND v.relacion_id = 'jefe') AS tiene_jefe
               FROM empleados e WHERE e.activo = 1 ORDER BY e.nombre""", (per, per)).fetchall()
        pendientes = []
        for f in filas:
            if not f["tiene_auto"]:
                pendientes.append({"id": f["id"], "nombre": f["nombre"], "relacion": "auto", "texto": "Auto"})
            if not f["tiene_jefe"]:
                pendientes.append({"id": f["id"], "nombre": f["nombre"], "relacion": "jefe", "texto": "Jefe"})
        return pendientes

    def ya_evaluo(emp_id, relacion):
        return db.execute(
            """SELECT 1 FROM evaluaciones WHERE empleado_id = ? AND periodo_id = ?
               AND relacion_id = ? AND evaluador = ?""", (emp_id, per, relacion, yo["nombre"])).fetchone()

    pendientes = []
    if not ya_evaluo(yo["empleado_id"], "auto"):
        pendientes.append({"id": yo["empleado_id"], "nombre": "Tu autoevaluación", "relacion": "auto", "texto": "Auto"})
    for e in db.execute("SELECT id, nombre FROM empleados WHERE jefe_id = ? AND activo = 1 ORDER BY nombre",
                        (yo["empleado_id"],)):
        if not ya_evaluo(e["id"], "jefe"):
            pendientes.append({"id": e["id"], "nombre": e["nombre"], "relacion": "jefe", "texto": "Tu colaborador"})
    jefe = db.execute("SELECT id, nombre FROM empleados WHERE id = ? AND activo = 1", (yo["jefe_id"],)).fetchone()
    if jefe and not ya_evaluo(jefe["id"], "colab"):
        pendientes.append({"id": jefe["id"], "nombre": jefe["nombre"], "relacion": "colab", "texto": "Tu jefe"})
    return pendientes


@app.route("/evaluar", methods=["GET", "POST"])
def evaluar():
    db = database.get_db()
    per = periodo_actual()
    gh = perm.es_gh()
    yo = g.usuario if not gh else None
    if yo is not None and not yo["empleado_id"]:
        abort(403)
    periodo = db.execute("SELECT * FROM periodos WHERE id = ?", (per,)).fetchone()
    empleados = db.execute(
        """SELECT e.id, e.nombre, e.cargo, e.es_lider, e.jefe_id, j.nombre AS jefe
           FROM empleados e LEFT JOIN empleados j ON j.id = e.jefe_id
           WHERE e.activo = 1 ORDER BY e.nombre""").fetchall()
    relaciones = db.execute("SELECT * FROM relaciones ORDER BY peso DESC").fetchall()
    nombres_rel = {r["id"]: r["nombre"] for r in relaciones}
    competencias = competencias_con_niveles()

    # Para jefes y colaboradores la relación no se elige: se deduce del organigrama
    yo_emp = {"id": yo["empleado_id"], "jefe_id": yo["jefe_id"]} if yo else None
    relacion_de = {e["id"]: perm.relacion_con(yo_emp, e) for e in empleados} if yo else {}

    form = {
        "empleado_id": request.args.get("empleado", type=int),
        "relacion_id": request.args.get("relacion", "jefe"),
        "evaluador": yo["nombre"] if yo else "", "fortalezas": "", "mejoras": "", "puntajes": {},
    }
    emp_sel = next((e for e in empleados if e["id"] == form["empleado_id"]), None)
    if gh and emp_sel and form["relacion_id"] == "auto":
        form["evaluador"] = emp_sel["nombre"]
    elif gh and emp_sel and form["relacion_id"] == "jefe":
        form["evaluador"] = emp_sel["jefe"] or ""

    if request.method == "POST":
        f = request.form
        form = {
            "empleado_id": f.get("empleado_id", type=int),
            "relacion_id": f.get("relacion_id", ""),
            "evaluador": f.get("evaluador", "").strip(),
            "fortalezas": f.get("fortalezas", "").strip(),
            "mejoras": f.get("mejoras", "").strip(),
            "puntajes": {c["id"]: f.get(f"c_{c['id']}", type=int) for c in competencias},
        }
        evaluado = next((e for e in empleados if e["id"] == form["empleado_id"]), None)
        if yo and evaluado:
            # El servidor decide la relación y firma con el nombre del usuario: no se puede suplantar
            form["relacion_id"] = relacion_de[evaluado["id"]]
            form["evaluador"] = yo["nombre"]
        errores = []

        if periodo is None or periodo["estado"] == "cerrado":
            errores.append(f"El período {per} está cerrado: ya no recibe evaluaciones.")
        if evaluado is None:
            errores.append("Selecciona el colaborador evaluado.")
        if form["relacion_id"] not in nombres_rel:
            errores.append("Selecciona la relación con el evaluado.")
        if evaluado and form["relacion_id"] == "auto":
            form["evaluador"] = evaluado["nombre"]  # la autoevaluación siempre la firma la misma persona
        if evaluado and form["relacion_id"] == "colab" and not evaluado["es_lider"]:
            errores.append(f"{evaluado['nombre']} no tiene personal a cargo: no puede recibir evaluación de colaboradores.")
        if not form["evaluador"]:
            errores.append("Escribe el nombre de quien evalúa.")

        # Competencias que aplican: liderazgo solo para quien tiene personal a cargo
        aplican = [c for c in competencias if not c["solo_lideres"] or (evaluado and evaluado["es_lider"])]
        faltan = [c["nombre"] for c in aplican if form["puntajes"].get(c["id"]) not in (1, 2, 3, 4, 5)]
        if evaluado and faltan:
            errores.append("Falta calificar: " + ", ".join(faltan) + ".")

        if not errores:
            # Si este evaluador ya había evaluado a la persona en el período, se reemplaza
            previa = db.execute(
                """SELECT id FROM evaluaciones
                   WHERE empleado_id = ? AND periodo_id = ? AND relacion_id = ? AND evaluador = ?""",
                (evaluado["id"], per, form["relacion_id"], form["evaluador"])).fetchone()
            if previa:
                eval_id = previa["id"]
                db.execute("UPDATE evaluaciones SET fortalezas = ?, mejoras = ?, fecha = date('now') WHERE id = ?",
                           (form["fortalezas"], form["mejoras"], eval_id))
                db.execute("DELETE FROM puntajes WHERE evaluacion_id = ?", (eval_id,))
            else:
                cur = db.execute(
                    """INSERT INTO evaluaciones (empleado_id, periodo_id, relacion_id, evaluador, fortalezas, mejoras)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (evaluado["id"], per, form["relacion_id"], form["evaluador"], form["fortalezas"], form["mejoras"]))
                eval_id = cur.lastrowid
            db.executemany("INSERT INTO puntajes (evaluacion_id, competencia_id, valor) VALUES (?, ?, ?)",
                           [(eval_id, c["id"], form["puntajes"][c["id"]]) for c in aplican])
            db.commit()
            flash(f"Evaluación {'actualizada' if previa else 'guardada'}: {evaluado['nombre']} "
                  f"({nombres_rel[form['relacion_id']].lower()}).")
            return redirect(url_for("evaluar"))
        for e in errores:
            flash(e, "error")

    # Últimas evaluaciones: Gestión Humana ve todas; los demás, solo las que hicieron
    sql = """SELECT v.id, v.evaluador, v.fecha, e.nombre AS evaluado, r.nombre AS relacion
             FROM evaluaciones v JOIN empleados e ON e.id = v.empleado_id JOIN relaciones r ON r.id = v.relacion_id
             WHERE v.periodo_id = ?"""
    params = [per]
    if yo:
        sql += " AND v.evaluador = ?"
        params.append(yo["nombre"])
    recientes = db.execute(sql + " ORDER BY v.id DESC LIMIT 8", params).fetchall()

    return render_template("evaluar.html", empleados=empleados, relaciones=relaciones,
                           competencias=competencias, form=form, periodo=periodo,
                           pendientes=evaluaciones_pendientes(db, per, yo), recientes=recientes,
                           relacion_de=relacion_de, nombres_rel=nombres_rel)


@app.post("/evaluaciones/<int:eval_id>/eliminar")
def evaluaciones_eliminar(eval_id):
    db = database.get_db()
    v = db.execute("SELECT * FROM evaluaciones WHERE id = ?", (eval_id,)).fetchone()
    if v is None:
        abort(404)
    # Gestión Humana puede eliminar cualquiera; los demás, solo las suyas y en un período abierto
    if not perm.es_gh() and (v["evaluador"] != g.usuario["nombre"] or not periodo_abierto(db, v["periodo_id"])):
        abort(403)
    db.execute("DELETE FROM evaluaciones WHERE id = ?", (eval_id,))  # los puntajes se borran en cascada
    db.commit()
    flash("Evaluación eliminada.")
    return redirect(url_for("evaluar"))


# ---------------------------------------------------------------------
# Resultados 360°
# ---------------------------------------------------------------------
def empleados_visibles(db):
    """Colaboradores que el usuario puede consultar, con el nombre de su jefe."""
    filas = db.execute(
        """SELECT e.*, j.nombre AS jefe FROM empleados e LEFT JOIN empleados j ON j.id = e.jefe_id
           WHERE e.activo = 1 ORDER BY e.nombre""").fetchall()
    ids = perm.ids_visibles(db)
    return filas if ids is None else [e for e in filas if e["id"] in ids]


def empleado_seleccionado(empleados):
    """Toma el colaborador de la dirección (?empleado=ID) o el último consultado."""
    emp_id = request.args.get("empleado", type=int) or session.get("empleado")
    propio = g.usuario["empleado_id"]
    emp = next((e for e in empleados if e["id"] == emp_id), None) or \
        next((e for e in empleados if e["id"] == propio), None) or (empleados[0] if empleados else None)
    if emp:
        session["empleado"] = emp["id"]
    return emp


@app.route("/resultados")
def resultados():
    db = database.get_db()
    empleados = empleados_visibles(db)
    emp = empleado_seleccionado(empleados)
    if emp is None:
        flash("Aún no hay colaboradores para consultar.", "error")
        return redirect(url_for("metodologia"))
    per = periodo_actual()
    r = calculos.resultado_empleado(db, emp, per)
    periodo = db.execute("SELECT * FROM periodos WHERE id = ?", (per,)).fetchone()
    # Objetivo que se está editando (?editar=ID) o formulario vacío
    editar_id = request.args.get("editar", type=int)
    obj_form = next((o for o in r["objetivos"] if o["id"] == editar_id), None) or \
        session.pop("obj_form", None) or {"sentido": "mayor"}
    return render_template("resultados.html", empleados=empleados, emp=emp, r=r,
                           periodo=periodo, obj_form=obj_form, puede_editar=perm.puede_gestionar(db, emp["id"]))


# ---------------------------------------------------------------------
# Objetivos del período (APO): Gestión Humana o el jefe directo
# ---------------------------------------------------------------------
@app.post("/objetivos/guardar")
def objetivos_guardar():
    """Crea un objetivo nuevo o actualiza uno existente (si viene 'id')."""
    db = database.get_db()
    per = periodo_actual()
    f = request.form
    emp_id = f.get("empleado_id", type=int)
    perm.exigir_gestion(db, emp_id)
    obj_id = f.get("id", type=int)
    volver = redirect(url_for("resultados", empleado=emp_id) + "#objetivos")

    datos = {
        "descripcion": f.get("descripcion", "").strip(),
        "unidad": f.get("unidad", "").strip(),
        "meta": f.get("meta", type=float),
        "resultado": f.get("resultado", type=float),   # None si se deja vacío
        "peso": f.get("peso", type=float),
        "sentido": f.get("sentido", "mayor"),
    }
    errores = []
    if not periodo_abierto(db, per):
        errores.append(f"El período {per} está cerrado: sus objetivos ya no se pueden modificar.")
    if db.execute("SELECT 1 FROM empleados WHERE id = ?", (emp_id,)).fetchone() is None:
        errores.append("Colaborador no válido.")
    if not datos["descripcion"]:
        errores.append("Escribe el objetivo o indicador.")
    if datos["meta"] is None or datos["meta"] <= 0:
        errores.append("La meta debe ser un número mayor que cero.")
    if datos["resultado"] is not None and datos["resultado"] < 0:
        errores.append("El resultado no puede ser negativo.")
    if datos["peso"] is None or not 0 < datos["peso"] <= 100:
        errores.append("El peso debe estar entre 1 y 100 %.")
    if datos["sentido"] not in ("mayor", "menor"):
        errores.append("Elige el sentido del indicador.")

    # Los pesos de todos los objetivos del período no pueden pasar de 100 %
    if datos["peso"]:
        otros = db.execute(
            "SELECT COALESCE(SUM(peso), 0) FROM objetivos WHERE empleado_id = ? AND periodo_id = ? AND id IS NOT ?",
            (emp_id, per, obj_id)).fetchone()[0]
        if otros + datos["peso"] > 100:
            errores.append(f"Con este objetivo los pesos sumarían {otros + datos['peso']:.0f} %. "
                           f"El máximo es 100 % (quedan {100 - otros:.0f} % disponibles).")

    if errores:
        for e in errores:
            flash(e, "error")
        session["obj_form"] = {**datos, "id": obj_id}   # para no perder lo escrito
        return volver

    if obj_id:
        db.execute(
            """UPDATE objetivos SET descripcion = :descripcion, unidad = :unidad, meta = :meta,
                      resultado = :resultado, peso = :peso, sentido = :sentido
               WHERE id = :id AND empleado_id = :emp""", {**datos, "id": obj_id, "emp": emp_id})
        flash("Objetivo actualizado.")
    else:
        db.execute(
            """INSERT INTO objetivos (empleado_id, periodo_id, descripcion, unidad, meta, resultado, peso, sentido)
               VALUES (:emp, :per, :descripcion, :unidad, :meta, :resultado, :peso, :sentido)""",
            {**datos, "emp": emp_id, "per": per})
        flash("Objetivo agregado.")
    db.commit()
    return volver


@app.post("/objetivos/<int:obj_id>/eliminar")
def objetivos_eliminar(obj_id):
    db = database.get_db()
    fila = db.execute("SELECT empleado_id, periodo_id FROM objetivos WHERE id = ?", (obj_id,)).fetchone()
    if fila is None:
        abort(404)
    perm.exigir_gestion(db, fila["empleado_id"])
    if not periodo_abierto(db, fila["periodo_id"]):
        flash("El período está cerrado: sus objetivos ya no se pueden modificar.", "error")
    else:
        db.execute("DELETE FROM objetivos WHERE id = ?", (obj_id,))
        db.commit()
        flash("Objetivo eliminado.")
    return redirect(url_for("resultados", empleado=fila["empleado_id"]) + "#objetivos")


# ---------------------------------------------------------------------
# Planes de desarrollo (modelo SECI) y retroalimentación
# ---------------------------------------------------------------------
@app.route("/planes")
def planes():
    db = database.get_db()
    per = periodo_actual()
    empleados = empleados_visibles(db)
    emp = empleado_seleccionado(empleados)
    if emp is None:
        flash("Aún no hay colaboradores para consultar.", "error")
        return redirect(url_for("metodologia"))

    r = calculos.resultado_empleado(db, emp, per)
    acciones = db.execute(
        """SELECT a.*, c.nombre AS competencia FROM acciones_desarrollo a
           JOIN competencias c ON c.id = a.competencia_id
           WHERE a.empleado_id = ? AND a.periodo_id = ?
           ORDER BY CASE a.estado WHEN 'Pendiente' THEN 0 WHEN 'En curso' THEN 1 ELSE 2 END, a.fecha_limite""",
        (emp["id"], per)).fetchall()
    retro = db.execute("SELECT * FROM retroalimentaciones WHERE empleado_id = ? AND periodo_id = ?",
                       (emp["id"], per)).fetchone()

    # Seguimiento: solo colaboradores con plan, dentro de lo que el usuario puede ver
    seguimiento = db.execute(
        """SELECT e.id, e.nombre, e.area,
                  COUNT(a.id) AS total,
                  SUM(a.estado = 'Cumplida') AS cumplidas,
                  SUM(a.estado <> 'Cumplida' AND a.fecha_limite < date('now')) AS vencidas,
                  EXISTS(SELECT 1 FROM retroalimentaciones r WHERE r.empleado_id = e.id AND r.periodo_id = ?) AS con_retro
           FROM empleados e JOIN acciones_desarrollo a ON a.empleado_id = e.id AND a.periodo_id = ?
           WHERE e.activo = 1
           GROUP BY e.id ORDER BY e.nombre""", (per, per)).fetchall()
    visibles = {e["id"] for e in empleados}
    seguimiento = [s for s in seguimiento if s["id"] in visibles]

    hoy = date.today().isoformat()
    inicio, fin = rango_retroalimentacion(db, per)
    return render_template(
        "planes.html", empleados=empleados, emp=emp, r=r, acciones=acciones, retro=retro,
        seguimiento=seguimiento, total_activos=len(empleados), modos=calculos.MODOS_SECI,
        estados=calculos.ESTADOS_ACCION, hoy=hoy, fecha_sugerida=(date.today() + timedelta(days=45)).isoformat(),
        retro_min=inicio, retro_max=fin, puede_editar=perm.puede_gestionar(db, emp["id"]))


def rango_retroalimentacion(db, per):
    """La reunión se registra después de hacerla: entre el inicio del período y hoy (sin pasar del fin del período)."""
    p = db.execute("SELECT fecha_inicio, fecha_fin FROM periodos WHERE id = ?", (per,)).fetchone()
    hoy = date.today().isoformat()
    if p is None:
        return hoy, hoy
    return p["fecha_inicio"], min(p["fecha_fin"], hoy)


@app.post("/planes/sugerir")
def planes_sugerir():
    """Agrega al plan las acciones SECI sugeridas para cada competencia por debajo de 3,5."""
    db = database.get_db()
    per = periodo_actual()
    emp = db.execute(
        """SELECT e.*, j.nombre AS jefe FROM empleados e LEFT JOIN empleados j ON j.id = e.jefe_id
           WHERE e.id = ?""", (request.form.get("empleado_id", type=int),)).fetchone()
    if emp is None:
        abort(404)
    perm.exigir_gestion(db, emp["id"])
    r = calculos.resultado_empleado(db, emp, per)
    existentes = {a["accion"] for a in db.execute(
        "SELECT accion FROM acciones_desarrollo WHERE empleado_id = ? AND periodo_id = ?", (emp["id"], per))}
    fecha = (date.today() + timedelta(days=60)).isoformat()
    nuevas = 0
    for comp in r["mejoras"]:
        for modo, accion in calculos.SUGERENCIAS.get(comp["id"], []):
            if accion in existentes:
                continue
            # Las acciones de formación (I) las coordina Gestión Humana; las demás, el jefe inmediato
            responsable = "Gestión Humana" if modo == "I" else (emp["jefe"] or "Gestión Humana")
            db.execute(
                """INSERT INTO acciones_desarrollo (empleado_id, periodo_id, competencia_id, accion, modo_seci,
                                                   responsable, fecha_limite) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (emp["id"], per, comp["id"], accion, modo, responsable, fecha))
            nuevas += 1
    db.commit()
    flash(f"Se agregaron {nuevas} acciones sugeridas al plan." if nuevas
          else "Las acciones sugeridas ya estaban en el plan.", "" if nuevas else "error")
    return redirect(url_for("planes", empleado=emp["id"]))


@app.post("/acciones/guardar")
def acciones_guardar():
    db = database.get_db()
    f = request.form
    emp_id = f.get("empleado_id", type=int)
    perm.exigir_gestion(db, emp_id)
    datos = (emp_id, periodo_actual(), f.get("competencia_id"), f.get("accion", "").strip(),
             f.get("modo_seci"), f.get("responsable", "").strip(), f.get("fecha_limite") or None)
    errores = []
    if not datos[3]:
        errores.append("Describe la acción de desarrollo.")
    if datos[4] not in calculos.MODOS_SECI:
        errores.append("Elige el modo de conocimiento (SECI).")
    if db.execute("SELECT 1 FROM competencias WHERE id = ?", (datos[2],)).fetchone() is None:
        errores.append("Elige la competencia.")
    if not datos[6]:
        errores.append("Elige la fecha límite de la acción.")
    elif datos[6] < date.today().isoformat():
        errores.append("La fecha límite no puede estar en el pasado: una acción nueva debe tener un plazo por cumplir.")
    if errores:
        for e in errores:
            flash(e, "error")
    else:
        db.execute(
            """INSERT INTO acciones_desarrollo (empleado_id, periodo_id, competencia_id, accion, modo_seci,
                                               responsable, fecha_limite) VALUES (?, ?, ?, ?, ?, ?, ?)""", datos)
        db.commit()
        flash("Acción agregada al plan.")
    return redirect(url_for("planes", empleado=emp_id) + "#acciones")


@app.post("/acciones/<int:accion_id>/estado")
def acciones_estado(accion_id):
    db = database.get_db()
    estado = request.form.get("estado")
    fila = db.execute("SELECT empleado_id FROM acciones_desarrollo WHERE id = ?", (accion_id,)).fetchone()
    if fila is None or estado not in calculos.ESTADOS_ACCION:
        abort(400)
    perm.exigir_gestion(db, fila["empleado_id"])
    db.execute("UPDATE acciones_desarrollo SET estado = ? WHERE id = ?", (estado, accion_id))
    db.commit()
    flash(f"Estado actualizado: {estado}.")
    return redirect(url_for("planes", empleado=fila["empleado_id"]) + "#acciones")


@app.post("/acciones/<int:accion_id>/eliminar")
def acciones_eliminar(accion_id):
    db = database.get_db()
    fila = db.execute("SELECT empleado_id FROM acciones_desarrollo WHERE id = ?", (accion_id,)).fetchone()
    if fila is None:
        abort(404)
    perm.exigir_gestion(db, fila["empleado_id"])
    db.execute("DELETE FROM acciones_desarrollo WHERE id = ?", (accion_id,))
    db.commit()
    flash("Acción eliminada del plan.")
    return redirect(url_for("planes", empleado=fila["empleado_id"]) + "#acciones")


@app.post("/retroalimentacion/guardar")
def retroalimentacion_guardar():
    db = database.get_db()
    f = request.form
    emp_id = f.get("empleado_id", type=int)
    perm.exigir_gestion(db, emp_id)
    fecha = f.get("fecha")
    inicio, fin = rango_retroalimentacion(db, periodo_actual())
    if not fecha:
        flash("Escribe la fecha de la reunión de retroalimentación.", "error")
        return redirect(url_for("planes", empleado=emp_id) + "#retro")
    if fecha > date.today().isoformat():
        flash("La reunión aún no ha ocurrido: regístrala el día que se haga, no antes.", "error")
        return redirect(url_for("planes", empleado=emp_id) + "#retro")
    if not inicio <= fecha <= fin:
        flash(f"La fecha debe estar dentro del período {periodo_actual()} (entre {inicio} y {fin}).", "error")
        return redirect(url_for("planes", empleado=emp_id) + "#retro")
    # Una reunión por colaborador y período: si ya existe, se actualiza
    db.execute(
        """INSERT INTO retroalimentaciones (empleado_id, periodo_id, fecha, acuerdos, compromiso)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT (empleado_id, periodo_id)
           DO UPDATE SET fecha = excluded.fecha, acuerdos = excluded.acuerdos, compromiso = excluded.compromiso""",
        (emp_id, periodo_actual(), fecha, f.get("acuerdos", "").strip(), f.get("compromiso", "").strip()))
    db.commit()
    flash("Retroalimentación guardada.")
    return redirect(url_for("planes", empleado=emp_id) + "#retro")


@app.route("/metodologia")
def metodologia():
    db = database.get_db()
    competencias = db.execute("SELECT * FROM competencias ORDER BY orden").fetchall()
    niveles = {}
    for fila in db.execute("SELECT * FROM niveles_competencia"):
        niveles.setdefault(fila["competencia_id"], {})[fila["nivel"]] = fila["descripcion"]
    relaciones = db.execute("SELECT * FROM relaciones ORDER BY peso DESC").fetchall()
    return render_template("metodologia.html", competencias=competencias, niveles=niveles, relaciones=relaciones)


@app.errorhandler(403)
def prohibido(_e):
    flash("No tienes permiso para hacer eso.", "error")
    return redirect(url_for("inicio"))


if __name__ == "__main__":
    app.run(debug=True)
