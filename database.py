"""Conexión a la base de datos SQLite y comandos para crearla.

Uso desde la terminal (con el venv activo):
    flask --app app init-db     -> crea la base vacía (catálogos incluidos)
    flask --app app seed-db     -> crea la base y carga los datos de ejemplo
"""
import sqlite3
from pathlib import Path

import click
from flask import current_app, g

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "compas360.db"


def get_db():
    """Devuelve la conexión de la petición actual (se abre una sola vez)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row            # filas accesibles por nombre: fila["nombre"]
        g.db.execute("PRAGMA foreign_keys = ON")  # SQLite no valida llaves foráneas si no se activa
    return g.db


def close_db(e=None):
    """Cierra la conexión al terminar cada petición."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crea las tablas desde schema.sql y carga los catálogos del modelo."""
    from datos_ejemplo import cargar_catalogos

    db = get_db()
    with open(BASE_DIR / "schema.sql", encoding="utf-8") as f:
        db.executescript(f.read())
    cargar_catalogos(db)
    # Usuario administrador de Gestión Humana para el primer ingreso (debe cambiar la contraseña)
    from permisos import CLAVE_INICIAL, cifrar
    db.execute("INSERT INTO usuarios (usuario, clave_hash, rol, debe_cambiar) VALUES ('admin', ?, 'gh', 1)",
               (cifrar(CLAVE_INICIAL),))
    db.commit()


@click.command("init-db")
def init_db_command():
    """Crea la base de datos vacía (borra la anterior)."""
    init_db()
    click.echo("Base de datos creada: compas360.db")
    click.echo("Ingreso inicial -> usuario: admin  contraseña: Mabe2026*")


@click.command("seed-db")
def seed_db_command():
    """Crea la base de datos y carga colaboradores y evaluaciones de ejemplo."""
    from datos_ejemplo import cargar_datos_ejemplo

    init_db()
    resumen = cargar_datos_ejemplo(get_db())
    click.echo("Base de datos creada con datos de ejemplo:")
    for tabla, total in resumen.items():
        click.echo(f"  {tabla}: {total}")


def init_app(app):
    """Registra la base de datos en la aplicación Flask."""
    app.config.setdefault("DATABASE", str(DB_PATH))
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)
