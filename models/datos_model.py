import json
import os

import pyodbc
from dotenv import load_dotenv

load_dotenv()


def obtener_conexion():
    """Abre una conexión a SQL Server usando la configuración local."""
    servidor = os.getenv("DB_SERVER", "localhost")
    base_datos = os.getenv("DB_NAME", "DatosAbiertosDB")
    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    autenticacion_windows = os.getenv("DB_TRUSTED", "yes").lower() == "yes"

    if autenticacion_windows:
        cadena = (
            f"DRIVER={{{driver}}};SERVER={servidor};DATABASE={base_datos};"
            "Trusted_Connection=yes;TrustServerCertificate=yes;"
        )
    else:
        usuario = os.getenv("DB_USER", "")
        clave = os.getenv("DB_PASSWORD", "")
        cadena = (
            f"DRIVER={{{driver}}};SERVER={servidor};DATABASE={base_datos};"
            f"UID={usuario};PWD={clave};TrustServerCertificate=yes;"
        )

    return pyodbc.connect(cadena)


def _texto(valor):
    """Convierte valores de la API a texto sin producir 'None'."""
    return None if valor is None else str(valor)


def _identificador(registro):
    """Crea una clave estable usando código municipal y entidad."""
    identificador = registro.get("id") or registro.get("codigo")
    if identificador:
        return str(identificador)

    codigo = registro.get("codigo_municipio", "")
    entidad = registro.get("entidad", "")
    if codigo or entidad:
        return f"{codigo}|{entidad}".strip("|")
    return None


def guardar_registros(registros):
    """Inserta únicamente registros que todavía no existen."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    insertados = 0

    try:
        for registro in registros:
            identificador = _identificador(registro)
            if not identificador:
                continue

            cursor.execute(
                """
                IF NOT EXISTS (
                    SELECT 1 FROM RegistrosAPI WHERE id_api = ?
                )
                INSERT INTO RegistrosAPI (
                    id_api, codigo_municipio, nombre_municipio,
                    nombre_departamento, entidad, tipo_entidad,
                    poblacion, cantidad_usuarios, cantidad_contenido,
                    cantidad_comentarios, json_original
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                identificador,
                identificador,
                _texto(registro.get("codigo_municipio")),
                _texto(registro.get("nombre_municipio")),
                _texto(registro.get("nombre_departament")),
                _texto(registro.get("entidad")),
                _texto(registro.get("tipo_entidad")),
                _texto(registro.get("poblacion")),
                _texto(registro.get("cantidad_usuarios")),
                _texto(registro.get("cantidad_contenido")),
                _texto(registro.get("cantidad_comentarios")),
                json.dumps(registro, ensure_ascii=False),
            )
            if cursor.rowcount > 0:
                insertados += 1

        conexion.commit()
        return insertados
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()


def consultar_registros(filtro=""):
    """Consulta los datos guardados; el filtro busca municipio o entidad."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        consulta = """
            SELECT TOP 100 id_api, codigo_municipio, nombre_municipio,
                   nombre_departamento, entidad, tipo_entidad, poblacion,
                   cantidad_usuarios, cantidad_contenido, cantidad_comentarios
            FROM RegistrosAPI
        """
        if filtro:
            patron = f"%{filtro}%"
            cursor.execute(
                consulta
                + """
                WHERE nombre_municipio LIKE ?
                   OR nombre_departamento LIKE ?
                   OR entidad LIKE ?
                   OR tipo_entidad LIKE ?
                ORDER BY id DESC
                """,
                patron, patron, patron, patron,
            )
        else:
            cursor.execute(consulta + " ORDER BY id DESC")

        columnas = [columna[0] for columna in cursor.description]
        return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    finally:
        cursor.close()
        conexion.close()


def obtener_estadisticas():
    """Devuelve indicadores simples para el panel principal."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS total,
                   COUNT(DISTINCT nombre_departamento) AS departamentos,
                   COUNT(DISTINCT nombre_municipio) AS municipios
            FROM RegistrosAPI
            """
        )
        fila = cursor.fetchone()
        return {
            "total": fila[0] or 0,
            "departamentos": fila[1] or 0,
            "municipios": fila[2] or 0,
        }
    finally:
        cursor.close()
        conexion.close()
