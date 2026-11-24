"""Reglas de cálculo de Compás 360.

Aquí está toda la lógica del modelo de evaluación, separada de las páginas:
- Ponderación 360°: cada fuente (auto, jefe, pares, equipo) pesa según la tabla `relaciones`.
  Si falta una fuente, su peso se reparte entre las demás.
- Puntaje final = 60 % competencias + 40 % objetivos (APO).
- Clasificación, fortalezas, oportunidades de mejora y brechas de percepción.
"""

PESO_COMPETENCIAS = 0.60
PESO_OBJETIVOS = 0.40
TOPE_CUMPLIMIENTO = 1.20      # un objetivo puede sumar hasta 120 %
UMBRAL_FORTALEZA = 4.0
UMBRAL_MEJORA = 3.5
UMBRAL_BRECHA = 1.0

CLASES = [
    # (puntaje mínimo, nombre, código de color en el CSS)
    (90, "Sobresaliente", "s"),
    (75, "Cumple", "c"),
    (60, "En desarrollo", "d"),
    (0, "Requiere mejora", "r"),
]


# Modelo SECI de Nonaka y Takeuchi: cómo se convierte el conocimiento
MODOS_SECI = {
    "S": ("Socialización", "De tácito a tácito: aprender observando y practicando junto a otra persona."),
    "E": ("Externalización", "De tácito a explícito: poner por escrito la experiencia propia."),
    "C": ("Combinación", "De explícito a explícito: integrar documentos en estándares y manuales."),
    "I": ("Internalización", "De explícito a tácito: estudiar y practicar hasta volverlo hábito."),
}

# Acciones sugeridas para cada competencia débil: (modo SECI, acción)
SUGERENCIAS = {
    "res": [("S", "Acompañamiento semanal con el jefe para revisar las metas del turno y las causas de incumplimiento"),
            ("I", "Tablero visual personal de indicadores con seguimiento diario")],
    "cal": [("E", "Documentar en una lección de un punto (LUP) los defectos más frecuentes de su estación"),
            ("I", "Curso de herramientas de calidad (5 porqués, Ishikawa) aplicado a su puesto")],
    "seg": [("S", "Acompañamiento en el puesto con un referente de SST durante dos semanas"),
            ("I", "Reentrenamiento en uso de EPP y análisis de riesgos con verificación práctica")],
    "equ": [("S", "Participar en un círculo de mejora con personas de otras áreas"),
            ("I", "Taller de comunicación asertiva y resolución de conflictos")],
    "con": [("E", "Escribir dos lecciones de un punto sobre su experiencia en el puesto"),
            ("C", "Actualizar el estándar de trabajo del área junto con Ingeniería")],
    "ada": [("S", "Rotación planeada a una estación o proceso nuevo con tutor"),
            ("C", "Revisar con Ingeniería los cambios de modelo y su documentación")],
    "lid": [("S", "Mentoría con un líder de alto desempeño (una sesión quincenal)"),
            ("I", "Programa de formación en liderazgo y retroalimentación efectiva")],
}
ESTADOS_ACCION = ["Pendiente", "En curso", "Cumplida"]


def clasificar(puntaje):
    """Devuelve {'nombre', 'k'} según el puntaje final (0 a 100)."""
    if puntaje is None:
        return None
    for minimo, nombre, k in CLASES:
        if puntaje >= minimo:
            return {"nombre": nombre, "k": k}


def cumplimiento(meta, resultado, sentido):
    """Cumplimiento de un objetivo como fracción (1.0 = 100 %), con tope de 120 %.

    'mayor': más es mejor (unidades producidas) -> resultado / meta
    'menor': menos es mejor (defectos, tiempos)  -> meta / resultado
    """
    if resultado is None or not meta or meta <= 0:
        return None
    if sentido == "menor":
        valor = TOPE_CUMPLIMIENTO if resultado <= 0 else meta / resultado
    else:
        valor = resultado / meta
    return min(valor, TOPE_CUMPLIMIENTO)


def promedio(valores):
    valores = [v for v in valores if v is not None]
    return sum(valores) / len(valores) if valores else None


def resultado_empleado(db, empleado, periodo):
    """Calcula el resultado completo de un colaborador en un período."""
    relaciones = {r["id"]: dict(r) for r in db.execute("SELECT * FROM relaciones")}
    competencias = [dict(c) for c in db.execute("SELECT * FROM competencias ORDER BY orden")
                    if not c["solo_lideres"] or empleado["es_lider"]]

    evaluaciones = [dict(v) for v in db.execute(
        "SELECT * FROM evaluaciones WHERE empleado_id = ? AND periodo_id = ? ORDER BY fecha",
        (empleado["id"], periodo))]
    puntajes = db.execute(
        """SELECT v.relacion_id, p.competencia_id, p.valor
           FROM puntajes p JOIN evaluaciones v ON v.id = p.evaluacion_id
           WHERE v.empleado_id = ? AND v.periodo_id = ?""", (empleado["id"], periodo)).fetchall()

    # Cuántas evaluaciones hay de cada fuente
    por_relacion = {r: 0 for r in relaciones}
    for v in evaluaciones:
        por_relacion[v["relacion_id"]] += 1

    # --- Competencias: promedio por fuente y promedio ponderado ---
    detalle = []
    for c in competencias:
        por_fuente = {}
        for r in relaciones:
            vals = [p["valor"] for p in puntajes if p["relacion_id"] == r and p["competencia_id"] == c["id"]]
            if vals:
                por_fuente[r] = promedio(vals)
        suma_pesos = sum(relaciones[r]["peso"] for r in por_fuente)
        ponderado = (sum(relaciones[r]["peso"] * v for r, v in por_fuente.items()) / suma_pesos
                     if suma_pesos else None)
        otros = promedio([v for r, v in por_fuente.items() if r != "auto"])
        detalle.append({**c, "fuentes": por_fuente, "ponderado": ponderado,
                        "auto": por_fuente.get("auto"), "otros": otros})

    comp_promedio = promedio([d["ponderado"] for d in detalle])
    comp_pct = comp_promedio / 5 * 100 if comp_promedio is not None else None

    # --- Objetivos (APO) ---
    objetivos = []
    suma_peso = suma_ponderada = 0
    for o in db.execute("SELECT * FROM objetivos WHERE empleado_id = ? AND periodo_id = ? ORDER BY id",
                        (empleado["id"], periodo)):
        o = dict(o)
        o["cumplimiento"] = cumplimiento(o["meta"], o["resultado"], o["sentido"])
        if o["cumplimiento"] is not None:
            suma_peso += o["peso"]
            suma_ponderada += o["peso"] * o["cumplimiento"]
        objetivos.append(o)
    obj_pct = suma_ponderada / suma_peso * 100 if suma_peso else None
    peso_total_objetivos = sum(o["peso"] for o in objetivos)

    # --- Puntaje final y clasificación ---
    if comp_pct is None:
        final = None
    elif obj_pct is None:
        final = comp_pct                                   # sin objetivos medidos, solo competencias
    else:
        final = PESO_COMPETENCIAS * comp_pct + PESO_OBJETIVOS * min(obj_pct, 100)

    # --- Lectura de resultados ---
    con_valor = [d for d in detalle if d["ponderado"] is not None]
    fortalezas = sorted([d for d in con_valor if d["ponderado"] >= UMBRAL_FORTALEZA],
                        key=lambda d: -d["ponderado"])
    mejoras = sorted([d for d in con_valor if d["ponderado"] < UMBRAL_MEJORA],
                     key=lambda d: d["ponderado"])
    brechas = [d for d in detalle if d["auto"] is not None and d["otros"] is not None
               and abs(d["auto"] - d["otros"]) >= UMBRAL_BRECHA]

    faltan = []
    if not por_relacion.get("auto"):
        faltan.append("la autoevaluación")
    if not por_relacion.get("jefe"):
        faltan.append("la evaluación del jefe inmediato")

    return {
        "evaluaciones": evaluaciones,
        "num_evaluaciones": len(evaluaciones),
        "por_relacion": por_relacion,
        "relaciones": relaciones,
        "competencias": detalle,
        "comp_promedio": comp_promedio,
        "comp_pct": comp_pct,
        "objetivos": objetivos,
        "obj_pct": obj_pct,
        "peso_total_objetivos": peso_total_objetivos,
        "final": final,
        "clase": clasificar(final),
        "completa": not faltan,
        "faltan": faltan,
        "fortalezas": fortalezas,
        "mejoras": mejoras,
        "brechas": brechas,
    }


def resumen_periodo(db, periodo, area=None, ids=None):
    """Indicadores de toda la planta, de un área o de un grupo de colaboradores (el equipo de un jefe)."""
    sql = "SELECT * FROM empleados WHERE activo = 1"
    params = []
    if area:
        sql += " AND area = ?"
        params.append(area)
    if ids is not None:
        ids = list(ids) or [0]
        sql += f" AND id IN ({','.join('?' * len(ids))})"
        params += ids
    empleados = db.execute(sql + " ORDER BY nombre", params).fetchall()

    filas = [{"emp": e, "r": resultado_empleado(db, e, periodo)} for e in empleados]
    evaluados = [f for f in filas if f["r"]["final"] is not None]

    # Distribución por clasificación
    distribucion = [{"nombre": n, "k": k, "total": sum(1 for f in evaluados if f["r"]["clase"]["k"] == k)}
                    for _m, n, k in CLASES]

    # Promedio por área
    areas = {}
    for f in evaluados:
        areas.setdefault(f["emp"]["area"], []).append(f["r"]["final"])
    por_area = sorted(({"area": a, "promedio": promedio(v), "total": len(v)} for a, v in areas.items()),
                      key=lambda x: -x["promedio"])

    # Promedio por competencia (de menor a mayor: las primeras son necesidades de formación)
    comps = {}
    for f in evaluados:
        for c in f["r"]["competencias"]:
            if c["ponderado"] is not None:
                comps.setdefault(c["id"], {"nombre": c["nombre"], "valores": []})["valores"].append(c["ponderado"])
    por_competencia = sorted(({"id": k, "nombre": v["nombre"], "promedio": promedio(v["valores"])}
                              for k, v in comps.items()), key=lambda x: x["promedio"])

    # Puntos para la matriz competencias × objetivos
    matriz = [{"id": f["emp"]["id"], "nombre": f["emp"]["nombre"],
               "iniciales": "".join(p[0] for p in f["emp"]["nombre"].split()[:2]).upper(),
               "x": f["r"]["comp_pct"], "y": min(f["r"]["obj_pct"], 120), "k": f["r"]["clase"]["k"]}
              for f in evaluados if f["r"]["obj_pct"] is not None]

    ordenados = sorted(evaluados, key=lambda f: f["r"]["final"])
    return {
        "total": len(filas),
        "evaluados": len(evaluados),
        "completas": sum(1 for f in filas if f["r"]["completa"]),
        "pendientes": len(filas) - sum(1 for f in filas if f["r"]["completa"]),
        "promedio": promedio([f["r"]["final"] for f in evaluados]),
        "distribucion": distribucion,
        "por_area": por_area,
        "por_competencia": por_competencia,
        "matriz": matriz,
        "atencion": [f for f in ordenados if f["r"]["final"] < 75],          # En desarrollo o Requiere mejora
        "destacados": list(reversed(ordenados))[:5],
    }
