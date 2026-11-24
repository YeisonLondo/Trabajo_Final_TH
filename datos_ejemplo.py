"""Catálogos del modelo de evaluación y datos de ejemplo (ficticios).

Los catálogos (competencias, escala BARS, pesos 360° y períodos) son parte
del modelo y siempre se cargan. Los colaboradores, evaluaciones, objetivos y
planes son ficticios y solo sirven para probar y presentar el sistema.
"""
import random

# ---------------------------------------------------------------------
# Catálogos del modelo
# ---------------------------------------------------------------------
COMPETENCIAS = [
    # (id, nombre, descripción, solo_lideres, [conducta nivel 1..5])
    ("res", "Orientación a resultados",
     "Cumple metas de producción, calidad y entrega en los tiempos acordados.", 0,
     ["No alcanza las metas y requiere supervisión constante.",
      "Alcanza parcialmente las metas; necesita recordatorios.",
      "Cumple las metas acordadas de forma consistente.",
      "Supera las metas con frecuencia y optimiza recursos.",
      "Supera las metas de forma sostenida y eleva el resultado del equipo."]),
    ("cal", "Calidad y mejora continua",
     "Aplica los estándares de calidad y propone mejoras al proceso.", 0,
     ["Genera reprocesos frecuentes; no sigue los estándares.",
      "Sigue los estándares con errores ocasionales.",
      "Trabaja sin defectos y cumple los estándares.",
      "Detecta fallas a tiempo y propone mejoras.",
      "Lidera mejoras (kaizen) con resultados medibles."]),
    ("seg", "Seguridad y autocuidado",
     "Cumple las normas de SST, usa EPP y reporta condiciones inseguras.", 0,
     ["Incumple normas de seguridad o no usa EPP.",
      "Cumple las normas solo bajo supervisión.",
      "Cumple las normas y usa EPP de forma permanente.",
      "Reporta actos y condiciones inseguras.",
      "Promueve la cultura de autocuidado en su equipo."]),
    ("equ", "Trabajo en equipo",
     "Colabora con compañeros y otras áreas para lograr objetivos comunes.", 0,
     ["Trabaja aislado o genera conflictos.",
      "Colabora solo cuando se le pide.",
      "Colabora de forma activa con su equipo.",
      "Apoya a otras áreas y facilita acuerdos.",
      "Integra equipos y es referente de cooperación."]),
    ("con", "Gestión del conocimiento",
     "Comparte lo que sabe, documenta buenas prácticas y aprende de otros (Nonaka y Takeuchi).", 0,
     ["No comparte su experiencia ni documenta.",
      "Comparte conocimiento solo si se lo piden.",
      "Explica su trabajo y participa en capacitaciones.",
      "Documenta prácticas (lecciones de un punto) y enseña a otros.",
      "Es mentor; convierte su experiencia en estándares del área."]),
    ("ada", "Adaptabilidad e innovación",
     "Se ajusta a cambios de modelo, tecnología o proceso y aporta ideas.", 0,
     ["Se resiste a los cambios.",
      "Acepta los cambios con dificultad.",
      "Se adapta a los cambios del proceso.",
      "Aprende rápido y propone ideas nuevas.",
      "Impulsa el cambio y la innovación en su área."]),
    ("lid", "Liderazgo de equipos",
     "Orienta, retroalimenta y desarrolla a su equipo (solo cargos con personal a cargo).", 1,
     ["No orienta ni retroalimenta a su equipo.",
      "Da instrucciones, pero poca retroalimentación.",
      "Orienta y retroalimenta a su equipo con regularidad.",
      "Desarrolla a su equipo y delega con criterio.",
      "Forma líderes y logra alto compromiso del equipo."]),
]

RELACIONES = [
    ("auto", "Autoevaluación", 0.15),
    ("jefe", "Jefe inmediato", 0.40),
    ("par", "Par o compañero", 0.25),
    ("colab", "Colaborador a cargo", 0.20),
]

PERIODOS = [
    ("2026-I", "2026-01-01", "2026-06-30", "cerrado"),
    ("2026-II", "2026-07-01", "2026-12-31", "abierto"),
]


def cargar_catalogos(db):
    for orden, (cid, nombre, desc, solo_lid, niveles) in enumerate(COMPETENCIAS, start=1):
        db.execute("INSERT INTO competencias VALUES (?, ?, ?, ?, ?)",
                   (cid, nombre, desc, solo_lid, orden))
        for nivel, conducta in enumerate(niveles, start=1):
            db.execute("INSERT INTO niveles_competencia VALUES (?, ?, ?)", (cid, nivel, conducta))
    db.executemany("INSERT INTO relaciones VALUES (?, ?, ?)", RELACIONES)
    db.executemany("INSERT INTO periodos VALUES (?, ?, ?, ?)", PERIODOS)


# ---------------------------------------------------------------------
# Datos de ejemplo (personas ficticias)
# ---------------------------------------------------------------------
# código, nombre, cargo, área, nivel, es_líder, código del jefe, ingreso,
# perfil = nivel "real" de cada competencia (res, cal, seg, equ, con, ada, lid)
EMPLEADOS = [
    ("e01", "Carolina Ospina Ríos", "Jefe de Producción", "Producción", "NT 3", 1, None, "2012-03-05", [4.5, 4.2, 4.4, 4.0, 3.4, 4.2, 4.1]),
    ("e02", "Andrés Felipe Giraldo", "Supervisor de ensamble", "Producción", "NT 4", 1, "e01", "2016-07-18", [4.1, 3.9, 4.2, 3.6, 2.9, 3.8, 3.2]),
    ("e03", "Luisa Fernanda Arango", "Operaria de ensamble", "Producción", "NT 7", 0, "e02", "2019-02-11", [4.6, 4.5, 4.7, 4.4, 4.0, 4.2]),
    ("e04", "Jhon Fredy Marín", "Operario de ensamble", "Producción", "NT 7", 0, "e02", "2023-09-04", [2.9, 2.6, 2.3, 3.3, 2.3, 3.0]),
    ("e05", "Diana Marcela Henao", "Operaria de espumado", "Producción", "NT 7", 0, "e02", "2021-05-24", [4.0, 4.1, 3.9, 4.3, 3.2, 3.7]),
    ("e06", "Mauricio Valencia Cardona", "Coordinador de mantenimiento", "Mantenimiento", "NT 4", 1, "e01", "2014-10-01", [4.2, 4.0, 4.5, 3.8, 3.9, 4.0, 3.7]),
    ("e07", "Sebastián Cardona López", "Técnico de mantenimiento", "Mantenimiento", "NT 6", 0, "e06", "2020-01-20", [3.9, 3.7, 4.3, 3.5, 2.7, 4.4]),
    ("e08", "Ricardo Salazar Mejía", "Coordinador de calidad", "Calidad", "NT 4", 1, "e01", "2013-06-10", [4.3, 4.7, 4.2, 3.7, 4.1, 3.9, 3.9]),
    ("e09", "Paula Andrea Gómez", "Inspectora de calidad", "Calidad", "NT 6", 0, "e08", "2018-08-13", [4.2, 4.6, 4.1, 4.0, 3.8, 3.6]),
    ("e10", "Felipe Castaño Arias", "Coordinador de logística", "Logística", "NT 4", 1, None, "2015-04-27", [3.8, 3.6, 3.9, 4.2, 3.5, 3.9, 3.6]),
    ("e11", "Natalia Ríos Quintero", "Analista de logística", "Logística", "NT 5", 0, "e10", "2022-02-14", [3.2, 3.3, 3.5, 3.8, 2.8, 3.0]),
    ("e12", "Juliana Zuluaga Henao", "Jefe de Gestión Humana", "Gestión Humana", "NT 3", 1, None, "2011-09-12", [4.3, 4.0, 4.2, 4.5, 4.4, 4.1, 4.4]),
    ("e13", "Valentina Restrepo Gil", "Analista de Gestión Humana", "Gestión Humana", "NT 5", 0, "e12", "2021-11-02", [4.0, 3.9, 4.0, 4.4, 4.2, 4.0]),
    ("e14", "Camilo Loaiza Duque", "Ingeniero de procesos", "Ingeniería", "NT 5", 0, "e01", "2020-06-08", [4.4, 4.3, 4.0, 3.4, 3.0, 4.6]),
]

# Tendencia de la autoevaluación (+ = se califica más alto que los demás)
SESGO_AUTO = {"e04": 1.1, "e09": -0.8, "e02": 0.5, "e07": 0.6}
# Evaluaciones que faltan, para mostrar procesos pendientes
FALTANTES = {"e11": ["jefe"], "e13": ["auto"]}

COMENTARIOS = {
    ("e04", "jefe"): ("Puntual y con buena disposición para aprender.",
                      "Usar el EPP completo durante todo el turno y reducir los defectos en el ensamble de puertas."),
    ("e04", "auto"): ("Cumplo con mi trabajo y ayudo a mis compañeros.", ""),
    ("e03", "jefe"): ("Referente de calidad en la línea; enseña a los nuevos.", "Puede liderar un círculo de mejora."),
    ("e02", "colab"): ("Siempre está pendiente de la seguridad del equipo.", "Nos gustaría más retroalimentación sobre cómo vamos."),
    ("e07", "jefe"): ("Resuelve rápido las fallas eléctricas.", "Documentar las reparaciones para que otros técnicos aprendan."),
    ("e14", "par"): ("Propone mejoras con datos.", "Involucrar más a los operarios en los proyectos."),
}

# Objetivos por tipo de cargo: (descripción, unidad, meta, sentido, peso)
OBJETIVOS = {
    "prod": [("Unidades ensambladas por turno", "unidades", 420, "mayor", 40),
             ("Defectos atribuibles a la estación", "PPM", 800, "menor", 35),
             ("Cumplimiento de 5S en la estación", "%", 90, "mayor", 25)],
    "prod_lider": [("Cumplimiento del plan de producción", "%", 98, "mayor", 40),
                   ("Refrigeradores producidos por día (promedio)", "unidades", 3800, "mayor", 30),
                   ("Accidentes con incapacidad en el período", "casos", 1, "menor", 30)],
    "Mantenimiento": [("Disponibilidad de equipos", "%", 95, "mayor", 50),
                      ("Tiempo medio de reparación (MTTR)", "horas", 2, "menor", 30),
                      ("Cumplimiento del plan preventivo", "%", 95, "mayor", 20)],
    "Calidad": [("Inspecciones realizadas a tiempo", "%", 98, "mayor", 40),
                ("Reclamos de clientes por mes", "reclamos", 10, "menor", 35),
                ("Auditorías de proceso cerradas", "%", 90, "mayor", 25)],
    "Logística": [("Despachos a tiempo y completos (OTIF)", "%", 95, "mayor", 50),
                  ("Exactitud de inventario", "%", 98, "mayor", 50)],
    "Ingeniería": [("Proyectos de mejora implementados", "proyectos", 4, "mayor", 50),
                   ("Ahorro generado", "millones COP", 120, "mayor", 50)],
    "Gestión Humana": [("Cumplimiento del plan de capacitación", "%", 90, "mayor", 40),
                       ("Rotación voluntaria", "%", 6, "menor", 30),
                       ("Evaluaciones de desempeño cerradas a tiempo", "%", 95, "mayor", 30)],
}

# Planes de desarrollo: código empleado -> (acciones, retroalimentación)
PLANES = {
    "e04": ([("seg", "Acompañamiento en el puesto con un referente de SST durante dos semanas", "S", "Andrés Felipe Giraldo", "2026-12-05", "En curso"),
             ("seg", "Reentrenamiento en uso de EPP y análisis de riesgos con verificación práctica", "I", "Gestión Humana", "2026-12-15", "Pendiente"),
             ("con", "Escribir dos lecciones de un punto sobre su experiencia en el puesto", "E", "Jhon Fredy Marín", "2027-01-30", "Pendiente"),
             ("cal", "Curso de herramientas de calidad (5 porqués, Ishikawa) aplicado a su puesto", "I", "Ricardo Salazar Mejía", "2026-11-28", "Cumplida")],
            ("2026-11-12",
             "Se revisaron los resultados 360. Jhon reconoce dificultades con el uso del EPP en la línea de puertas; se acuerda acompañamiento en el puesto y seguimiento quincenal con el supervisor.",
             "Usar el EPP completo durante todo el turno y documentar dos lecciones de un punto antes de enero.")),
    "e02": ([("lid", "Mentoría con un líder de alto desempeño (una sesión quincenal)", "S", "Carolina Ospina Ríos", "2027-02-15", "En curso"),
             ("con", "Actualizar el estándar de trabajo del área junto con Ingeniería", "C", "Camilo Loaiza Duque", "2027-01-20", "Pendiente")],
            None),
    "e07": ([("con", "Registrar en la bitácora digital las reparaciones críticas con causa raíz y solución", "E", "Mauricio Valencia Cardona", "2026-12-20", "Cumplida"),
             ("equ", "Participar en un círculo de mejora con personas de otras áreas", "S", "Mauricio Valencia Cardona", "2027-01-31", "En curso")],
            ("2026-11-14",
             "Se reconoce su capacidad técnica; el reto es compartir lo que sabe con el resto del equipo.",
             "Documentar las reparaciones críticas y acompañar a un técnico nuevo.")),
}

# Usuario de cada colaborador de ejemplo (inicial del nombre + primer apellido)
USUARIOS = {
    "e01": "cospina", "e02": "agiraldo", "e03": "larango", "e04": "jmarin", "e05": "dhenao",
    "e06": "mvalencia", "e07": "scardona", "e08": "rsalazar", "e09": "pgomez", "e10": "fcastano",
    "e11": "nrios", "e12": "jzuluaga", "e13": "vrestrepo", "e14": "cloaiza",
}

COMP_IDS = [c[0] for c in COMPETENCIAS]


def cargar_datos_ejemplo(db, periodo="2026-II"):
    """Inserta los datos ficticios y devuelve cuántas filas quedaron por tabla."""
    rnd = random.Random(11)  # semilla fija: siempre se generan los mismos datos
    ids = {}                 # código 'e01' -> id real en la base
    perfiles = {}

    # 1. Colaboradores (primero sin jefe; luego se asigna el jefe con su id real)
    for cod, nombre, cargo, area, nivel, lider, _jefe, ingreso, perfil in EMPLEADOS:
        cur = db.execute(
            "INSERT INTO empleados (nombre, cargo, area, nivel, es_lider, fecha_ingreso) VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, cargo, area, nivel, lider, ingreso))
        ids[cod] = cur.lastrowid
        perfiles[cod] = perfil
    for cod, *_resto in EMPLEADOS:
        jefe = _resto[5]
        if jefe:
            db.execute("UPDATE empleados SET jefe_id = ? WHERE id = ?", (ids[jefe], ids[cod]))

    info = {e[0]: e for e in EMPLEADOS}

    def evaluar(cod, relacion, evaluador, sesgo):
        fort, mej = COMENTARIOS.get((cod, relacion), ("", ""))
        cur = db.execute(
            "INSERT INTO evaluaciones (empleado_id, periodo_id, relacion_id, evaluador, fortalezas, mejoras, fecha) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ids[cod], periodo, relacion, evaluador, fort, mej, f"2026-11-0{rnd.randint(1, 9)}"))
        for comp, base in zip(COMP_IDS, perfiles[cod]):
            valor = round(base + sesgo + (rnd.random() - 0.5) * 0.8)
            db.execute("INSERT INTO puntajes VALUES (?, ?, ?)",
                       (cur.lastrowid, comp, max(1, min(5, valor))))

    # 2. Evaluaciones 360°
    for cod, nombre, _c, area, _n, lider, jefe, _i, _p in EMPLEADOS:
        faltan = FALTANTES.get(cod, [])
        if "auto" not in faltan:
            evaluar(cod, "auto", nombre, SESGO_AUTO.get(cod, 0.3))
        if "jefe" not in faltan:
            evaluar(cod, "jefe", info[jefe][1] if jefe else "Gerente de planta", 0)
        # un par: mismo área y mismo tipo de cargo; si no hay, otro del mismo tipo
        candidatos = [e for e in EMPLEADOS if e[0] != cod and e[5] == lider and e[0] != jefe]
        par = next((e for e in candidatos if e[3] == area), None) or \
            next((e for e in candidatos if e[6] != cod), None)
        if par:
            evaluar(cod, "par", par[1], 0.1)
        # hasta dos colaboradores a cargo evalúan a su líder
        for sub in [e for e in EMPLEADOS if e[6] == cod][:2]:
            evaluar(cod, "colab", sub[1], -0.1)

    # 3. Objetivos del período con resultados coherentes con el perfil
    enteros = {"unidades", "casos", "reclamos", "proyectos", "PPM"}
    for cod, _no, _c, area, _n, lider, _j, _i, perfil in EMPLEADOS:
        tipo = ("prod_lider" if lider else "prod") if area == "Producción" else area
        factor = 0.84 + (perfil[0] - 3) * 0.12
        for desc, unidad, meta, sentido, peso in OBJETIVOS[tipo]:
            x = factor + (rnd.random() - 0.5) * 0.12
            real = meta / x if sentido == "menor" else meta * x
            if unidad == "%" and sentido == "mayor":
                real = min(100, real)
            real = round(real) if unidad in enteros or meta >= 50 else round(real, 1)
            db.execute(
                "INSERT INTO objetivos (empleado_id, periodo_id, descripcion, unidad, meta, resultado, peso, sentido) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (ids[cod], periodo, desc, unidad, meta, real, peso, sentido))

    # 4. Planes de desarrollo y retroalimentación
    for cod, (acciones, retro) in PLANES.items():
        for comp, accion, modo, resp, fecha, estado in acciones:
            db.execute(
                "INSERT INTO acciones_desarrollo (empleado_id, periodo_id, competencia_id, accion, modo_seci, "
                "responsable, fecha_limite, estado) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (ids[cod], periodo, comp, accion, modo, resp, fecha, estado))
        if retro:
            db.execute(
                "INSERT INTO retroalimentaciones (empleado_id, periodo_id, fecha, acuerdos, compromiso) "
                "VALUES (?, ?, ?, ?, ?)", (ids[cod], periodo, *retro))

    # 5. Usuarios: uno por colaborador, con la contraseña inicial (en la demo no se obliga a cambiarla)
    from permisos import cifrar, rol_sugerido, CLAVE_INICIAL
    clave = cifrar(CLAVE_INICIAL)
    for cod, usuario in USUARIOS.items():
        e = db.execute("SELECT * FROM empleados WHERE id = ?", (ids[cod],)).fetchone()
        db.execute("INSERT INTO usuarios (usuario, clave_hash, rol, empleado_id, debe_cambiar) VALUES (?, ?, ?, ?, 0)",
                   (usuario, clave, rol_sugerido(e), e["id"]))

    db.commit()
    tablas = ["empleados", "evaluaciones", "puntajes", "objetivos", "acciones_desarrollo", "retroalimentaciones",
              "usuarios"]
    return {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tablas}
