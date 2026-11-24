-- =====================================================================
-- Compás 360 · Sistema de evaluación del desempeño
-- Esquema de la base de datos (SQLite)
-- Propuesta académica para mabe Colombia S.A.S., planta Manizales
-- =====================================================================

-- Se borran las tablas en orden inverso para poder recrear la base desde cero
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS retroalimentaciones;
DROP TABLE IF EXISTS acciones_desarrollo;
DROP TABLE IF EXISTS objetivos;
DROP TABLE IF EXISTS puntajes;
DROP TABLE IF EXISTS evaluaciones;
DROP TABLE IF EXISTS periodos;
DROP TABLE IF EXISTS relaciones;
DROP TABLE IF EXISTS niveles_competencia;
DROP TABLE IF EXISTS competencias;
DROP TABLE IF EXISTS empleados;

-- ---------------------------------------------------------------------
-- 1. Colaboradores de la planta
-- ---------------------------------------------------------------------
CREATE TABLE empleados (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT    NOT NULL,
    cargo         TEXT    NOT NULL,
    area          TEXT    NOT NULL,              -- Producción, Calidad, Mantenimiento...
    nivel         TEXT    NOT NULL,              -- Nivel de talento: NT 2 a NT 7
    jefe_id       INTEGER REFERENCES empleados(id) ON DELETE SET NULL,
    es_lider      INTEGER NOT NULL DEFAULT 0 CHECK (es_lider IN (0, 1)),  -- 1 = tiene personal a cargo
    fecha_ingreso TEXT,                          -- formato AAAA-MM-DD
    activo        INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

-- ---------------------------------------------------------------------
-- 2. Catálogo de competencias del modelo
-- ---------------------------------------------------------------------
CREATE TABLE competencias (
    id           TEXT    PRIMARY KEY,            -- código corto: 'res', 'cal', 'seg'...
    nombre       TEXT    NOT NULL,
    descripcion  TEXT    NOT NULL,
    solo_lideres INTEGER NOT NULL DEFAULT 0 CHECK (solo_lideres IN (0, 1)),
    orden        INTEGER NOT NULL
);

-- 3. Escala BARS: una conducta observable por cada nivel (1 a 5) de cada competencia
CREATE TABLE niveles_competencia (
    competencia_id TEXT    NOT NULL REFERENCES competencias(id) ON DELETE CASCADE,
    nivel          INTEGER NOT NULL CHECK (nivel BETWEEN 1 AND 5),
    descripcion    TEXT    NOT NULL,
    PRIMARY KEY (competencia_id, nivel)
);

-- 4. Fuentes de la evaluación 360° y su peso en el resultado
CREATE TABLE relaciones (
    id     TEXT PRIMARY KEY,                     -- 'auto', 'jefe', 'par', 'colab'
    nombre TEXT NOT NULL,
    peso   REAL NOT NULL CHECK (peso > 0 AND peso <= 1)
);

-- 5. Períodos de evaluación (semestrales)
CREATE TABLE periodos (
    id           TEXT PRIMARY KEY,               -- '2026-I', '2026-II'
    fecha_inicio TEXT NOT NULL,
    fecha_fin    TEXT NOT NULL,
    estado       TEXT NOT NULL DEFAULT 'abierto' CHECK (estado IN ('abierto', 'cerrado'))
);

-- ---------------------------------------------------------------------
-- 6. Evaluaciones 360°: una fila por cada persona que evalúa a otra
-- ---------------------------------------------------------------------
CREATE TABLE evaluaciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL REFERENCES empleados(id) ON DELETE CASCADE,  -- evaluado
    periodo_id  TEXT    NOT NULL REFERENCES periodos(id),
    relacion_id TEXT    NOT NULL REFERENCES relaciones(id),
    evaluador   TEXT    NOT NULL,                -- nombre de quien evalúa
    fortalezas  TEXT,
    mejoras     TEXT,
    fecha       TEXT    NOT NULL DEFAULT (date('now')),
    -- una persona evalúa a otra una sola vez por período y relación
    UNIQUE (empleado_id, periodo_id, relacion_id, evaluador)
);

-- 7. Calificación (1 a 5) de cada competencia dentro de una evaluación
CREATE TABLE puntajes (
    evaluacion_id  INTEGER NOT NULL REFERENCES evaluaciones(id) ON DELETE CASCADE,
    competencia_id TEXT    NOT NULL REFERENCES competencias(id),
    valor          INTEGER NOT NULL CHECK (valor BETWEEN 1 AND 5),
    PRIMARY KEY (evaluacion_id, competencia_id)
);

-- ---------------------------------------------------------------------
-- 8. Objetivos del período (Administración por Objetivos, APO)
-- ---------------------------------------------------------------------
CREATE TABLE objetivos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL REFERENCES empleados(id) ON DELETE CASCADE,
    periodo_id  TEXT    NOT NULL REFERENCES periodos(id),
    descripcion TEXT    NOT NULL,
    unidad      TEXT,
    meta        REAL    NOT NULL CHECK (meta > 0),
    resultado   REAL,                            -- NULL mientras no se haya medido
    peso        REAL    NOT NULL CHECK (peso > 0 AND peso <= 100),
    sentido     TEXT    NOT NULL DEFAULT 'mayor' CHECK (sentido IN ('mayor', 'menor'))
);

-- ---------------------------------------------------------------------
-- 9. Plan de desarrollo individual (modelo SECI de Nonaka y Takeuchi)
-- ---------------------------------------------------------------------
CREATE TABLE acciones_desarrollo (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id    INTEGER NOT NULL REFERENCES empleados(id) ON DELETE CASCADE,
    periodo_id     TEXT    NOT NULL REFERENCES periodos(id),
    competencia_id TEXT    NOT NULL REFERENCES competencias(id),
    accion         TEXT    NOT NULL,
    modo_seci      TEXT    NOT NULL CHECK (modo_seci IN ('S', 'E', 'C', 'I')),
    responsable    TEXT,
    fecha_limite   TEXT,
    estado         TEXT    NOT NULL DEFAULT 'Pendiente'
                   CHECK (estado IN ('Pendiente', 'En curso', 'Cumplida'))
);

-- 10. Reunión de retroalimentación entre jefe y colaborador (una por período)
CREATE TABLE retroalimentaciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL REFERENCES empleados(id) ON DELETE CASCADE,
    periodo_id  TEXT    NOT NULL REFERENCES periodos(id),
    fecha       TEXT    NOT NULL,
    acuerdos    TEXT,
    compromiso  TEXT,
    UNIQUE (empleado_id, periodo_id)
);

-- ---------------------------------------------------------------------
-- 11. Usuarios del sistema (inicio de sesión y roles)
-- ---------------------------------------------------------------------
CREATE TABLE usuarios (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario      TEXT    NOT NULL UNIQUE,
    clave_hash   TEXT    NOT NULL,              -- nunca se guarda la contraseña, solo su hash
    rol          TEXT    NOT NULL CHECK (rol IN ('gh', 'jefe', 'colaborador')),
    empleado_id  INTEGER UNIQUE REFERENCES empleados(id) ON DELETE CASCADE,
    debe_cambiar INTEGER NOT NULL DEFAULT 1 CHECK (debe_cambiar IN (0, 1)),  -- cambiar clave al ingresar
    activo       INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);
