# script_sql_logging_documentado.py
# Versión anotada del script que conecta a SQL Server, crea tablas,
# inserta datos manualmente o desde archivo y genera logs detallados.

import pyodbc                      # Librería para conectar a SQL Server mediante ODBC
import pandas as pd                 # Librería para manipular datos y leer archivos (CSV/Excel/JSON)
import datetime                     # Módulo para trabajar con fechas y horas
import os                           # Módulo para operaciones del sistema de archivos
import traceback                    # Módulo para obtener trazas de errores (tracebacks)
import csv                          # Módulo para escribir archivos CSV


# --------------------------
# Helpers para logging
# --------------------------

def ensure_dir(path):
    # Crea el directorio si no existe (evita errores al guardar logs)
    if not os.path.exists(path):
        # Si la ruta no existe, la creamos recursivamente
        os.makedirs(path)


def timestamp_str():
    # Retorna un string con la fecha y hora actual en formato compacto para nombres de archivo
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def write_text_log(path, text):
    # Escribe un archivo de texto en 'path' con el contenido 'text'
    # Abre el archivo en modo escritura con codificación UTF-8
    with open(path, "w", encoding="utf-8") as f:
        # Escribe todo el texto de una sola vez
        f.write(text)


def write_csv(path, fieldnames, rows):
    # Escribe una lista de diccionarios 'rows' a un archivo CSV
    # 'fieldnames' es la lista de columnas (encabezados) que se escribirán
    with open(path, "w", encoding="utf-8", newline="") as f:
        # Crea un writer que maneja diccionarios y escribe encabezado
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for r in rows:
            # Escribe cada fila/diccionario al CSV. Si faltan claves, quedan en blanco.
            writer.writerow(r)


# ==============================
# FUNCIÓN: Conectar a SQL Server
# ==============================

def conectar_sqlserver():
    """
    Solicita credenciales al usuario y establece conexión a SQL Server.
    Retorna la conexión (pyodbc.Connection) o None si falla.
    """
    # Mensaje informativo para el usuario
    print("\n--- INGRESE LOS DATOS DE CONEXIÓN A SQL SERVER ---")
    # Solicita el nombre o instacia del servidor (ej: DESKTOP-BU654JC\SQLEXPRESS)
    servidor = input("Servidor: ").strip()
    # Solicita usuario con permisos para conectar (puede ser SQL auth)
    usuario = input("Usuario: ").strip()
    # Solicita la contraseña correspondinte
    contraseña = input("Contraseña: ").strip()

    try:
        # Intenta crear la conexión ODBC con las credenciales ingresadas
        conexion = pyodbc.connect(
            f'DRIVER={{SQL Server}};SERVER={servidor};UID={usuario};PWD={contraseña}',
            timeout=5
        )
        # Si no ocurre excepción, la conexión se considera establecida
        print("✅ Conexión establecida.")
        return conexion
    except Exception as e:
        # Si falla, muestra error y retorna None para permitir reintentar desde el menu
        print(f"❌ Error de conexión: {str(e)}")
        return None


# ==============================
# FUNCIÓN: Validar base de datos
# ==============================

def validar_base_datos(cursor):
    """
    Pide un nombre de base de datos y verifica que exista en el servidor.
    Cambia el contexto a esa base de datos con 'USE [nombre]'.
    """
    while True:
        # Pregunta por el nombre de la base de datos
        nombre_bd = input("\nNombre de la base de datos: ").strip()
        # Ejecuta una consulta parametrizada para evitar inyecciones
        cursor.execute("SELECT name FROM sys.databases WHERE name = ?", nombre_bd)
        # Si se encuentra un registro (fetchone != None), la BD existe
        if cursor.fetchone():
            # Cambia el contexto a la base seleccionada
            cursor.execute(f"USE [{nombre_bd}]")
            return nombre_bd
        else:
            # Sino, informa al usuario y vuelve a pedir
            print("❌ La base de datos no existe. Intente nuevamente.")


# ==============================
# FUNCIÓN: Validar tabla
# ==============================

def validar_tabla(cursor):
    """
    Pide el nombre de una tabla y verifica que exista en la base de datos actual.
    """
    while True:
        # Pregunta por el nombre de la tabla
        nombre_tabla = input("Nombre de la tabla: ").strip()
        # Consulta sys.tables para verificar existencia (consulta parametrizada)
        cursor.execute("SELECT name FROM sys.tables WHERE name = ?", nombre_tabla)
        if cursor.fetchone():
            # Si existe, retorna el nombre
            return nombre_tabla
        else:
            # Sino, solicita verificar el nombre
            print("❌ La tabla no existe. Verifique el nombre.")


# ==============================
# FUNCIÓN: Crear nueva tabla
# ==============================

def crear_tabla(cursor):
    """
    Crea una nueva tabla solicitando nombre y campos al usuario.
    Agrega automáticamente el campo 'Bi_controlorigen'.
    """
    # Valida y establece la base de datos en la que se creará la tabla
    nombre_bd = validar_base_datos(cursor)

    # Pide el nombre y verifica que no exista ya
    while True:
        nombre_tabla = input("Nombre de la nueva tabla: ").strip()
        cursor.execute("SELECT name FROM sys.tables WHERE name = ?", nombre_tabla)
        if cursor.fetchone():
            # Si la tabla ya existe, pide otro nombre
            print("⚠️ La tabla ya existe. Ingrese un nuevo nombre.")
        else:
            break

    # Solicita la cantidad de campos que tendrá la tabla
    while True:
        try:
            cantidad = int(input("Cantidad de campos: ").strip())
            if cantidad < 1:
                # Si ingresa un número menor que 1, solicita nuevamente
                print("Debe ingresar al menos un campo.")
                continue
            break
        except ValueError:
            # Si la entrada no es un entero, informa y repite
            print("Entrada inválida. Ingrese un número entero.")

    # Recolecta nombre y tipo de cada campo solicitado
    campos = []
    for i in range(1, cantidad + 1):
        print(f"\n--- Campo {i} ---")
        nombre = input("Nombre del campo: ").strip()
        tipo = input("Tipo de dato (ej. INT, VARCHAR(100), DATETIME): ").strip()
        campos.append((nombre, tipo))

    # Agrega campo extra para control de origen
    campos.append(("Bi_controlorigen", "VARCHAR(100)"))

    # Construye la sentencia CREATE TABLE de forma segura (aqui concatenamos nombres,
    # por eso se asume que el usuario provee nombres correctos; en producción conviene sanitizar)
    sentencia = f"CREATE TABLE [{nombre_tabla}] (\n"
    for nombre, tipo in campos:
        # Para cada par (nombre,tipo) agrega una línea al DDL
        sentencia += f"    [{nombre}] {tipo},\n"
    # Remueve la coma final sobrante y cierra la definición
    sentencia = sentencia.rstrip(",\n") + "\n);"

    try:
        # Ejecuta la sentencia DDL creada
        cursor.execute(sentencia)
        # Confirma la transacción para que la tabla quede persistida
        cursor.connection.commit()
        print("\n✅ TABLA CREADA EXITOSAMENTE")
        print(f"Base de datos: {nombre_bd}")
        print(f"Tabla: {nombre_tabla}")
    except Exception as e:
        # Si hay error, lo muestra y no detiene el programa
        print(f"❌ Error al crear la tabla: {str(e)}")


# ==============================
# FUNCIÓN: Carga manual (con logs)
# ==============================

def carga_manual(cursor):
    """
    Inserta datos manualmente en una tabla existente y genera logs:
      - resumen (txt)
      - CSV con filas insertadas (si las hay)
      - CSV con errores (si ocurrieron)
    """
    # Pide y valida base de datos y tabla
    nombre_bd = validar_base_datos(cursor)
    nombre_tabla = validar_tabla(cursor)

    # Obtiene esquema de la tabla (columnas y tipos)
    try:
        cursor.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM [{nombre_bd}].INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ?
        """, nombre_tabla)
        esquema = cursor.fetchall()                  # Lista de tuplas (COLUMN_NAME, DATA_TYPE)
        columnas = [col[0] for col in esquema]       # Extrae nombres de columnas
        tipos = {col[0]: col[1] for col in esquema}  # Diccionario {columna: tipo}
    except Exception as e:
        # Si falla obtener el esquema, muestra error y retorna
        print(f"❌ Error al obtener esquema de la tabla: {str(e)}")
        return

    # --- Preparar archivos de log ---
    logs_dir = os.path.join(os.getcwd(), "logs")   # Carpeta ./logs en el directorio actual
    ensure_dir(logs_dir)                            # Se asegura de que exista
    ts = timestamp_str()                            # Timestamp para nombres únicos
    summary_path = os.path.join(logs_dir, f"log_manual_{nombre_tabla}_{ts}_summary.txt")
    inserted_csv = os.path.join(logs_dir, f"log_manual_{nombre_tabla}_{ts}_inserted.csv")
    errors_csv = os.path.join(logs_dir, f"log_manual_{nombre_tabla}_{ts}_errors.csv")

    filas_insertadas = 0         # Contador de filas insertadas con éxito
    errores = []                 # Lista para almacenar información de errores
    filas_insertadas_data = []   # Lista de diccionarios con datos de filas insertadas

    attempt_counter = 0          # Contador de intentos (filas procesadas manualmente)

    # Bucle principal para ingresar filas manualmente
    while True:
        attempt_counter += 1
        print("\n--- INGRESO DE DATOS PARA UNA NUEVA FILA ---")
        fila = []                            # Lista de valores en el orden de columnas
        fila_dict_for_log = {}               # Diccionario para registrar la fila en CSV
        for col in columnas:
            # Si la columna es 'Bi_ejecucion', se rellena automáticamente
            if col.lower() == "bi_ejecucion":
                tipo_sql = tipos[col].lower()
                if tipo_sql in ["datetime", "smalldatetime", "datetime2", "date"]:
                    # Para tipos fecha/hora, guardamos un objeto datetime
                    valor_ejecucion = datetime.datetime.now()
                else:
                    # Para otros tipos, guardamos un string con fecha y texto
                    valor_ejecucion = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Python"
                fila.append(valor_ejecucion)
                fila_dict_for_log[col] = str(valor_ejecucion)
            else:
                # Para el resto de columnas, solicitamos entrada al usuario
                while True:
                    entrada = input(f"{col} ({tipos[col]}): ").strip()
                    tipo_sql = tipos[col].lower()
                    try:
                        # Validaciones básicas por tipo SQL
                        if tipo_sql in ["int", "bigint", "smallint", "tinyint"]:
                            valor = int(entrada)
                        elif tipo_sql in ["float", "real", "decimal", "numeric", "money", "smallmoney"]:
                            valor = float(entrada)
                        elif tipo_sql in ["bit"]:
                            if entrada.lower() in ["1", "true", "sí", "si"]:
                                valor = 1
                            elif entrada.lower() in ["0", "false", "no"]:
                                valor = 0
                            else:
                                # Si no es un valor valido para bit, lanzamos error de validacion
                                raise ValueError("Debe ingresar 1/0 o true/false")
                        elif tipo_sql in ["date", "datetime", "smalldatetime", "datetime2"]:
                            # Se espera formato YYYY-MM-DD; si quieres más formatos, hay que parsearlos
                            valor = datetime.datetime.strptime(entrada, "%Y-%m-%d")
                        else:
                            # Para tipos de texto y demás, se deja tal cual
                            valor = entrada
                        fila.append(valor)
                        fila_dict_for_log[col] = str(valor)
                        break  # si la validación pasa, salimos del while de ingreso del campo
                    except Exception as ex:
                        # Si hay error de conversión/validación, pedimos reintentar ese campo
                        print(f"⚠️ Formato inválido para '{col}' ({tipos[col]}). Intente nuevamente.")
        # Intentar insertar la fila construida en la tabla
        try:
            placeholders = ", ".join("?" for _ in columnas)  # Cadena del tipo '?, ?, ?, ...'
            sentencia = f"INSERT INTO [{nombre_tabla}] VALUES ({placeholders})"
            cursor.execute(sentencia, fila)                     # Ejecuta la inserción parametrizada
            cursor.connection.commit()                          # Confirma la inserción en la base de datos
            filas_insertadas += 1
            filas_insertadas_data.append(fila_dict_for_log.copy())
            print("✅ Fila insertada exitosamente.")
        except Exception as e:
            # Si hay error al insertar, guardamos detalle y seguimos (no se detiene el loop)
            tb = traceback.format_exc()
            errores.append({
                "attempt": attempt_counter,
                "error": str(e),
                "traceback": tb,
                **{k: v for k, v in fila_dict_for_log.items()}
            })
            print(f"❌ Error al insertar fila: {str(e)}")

        # Pregunta si desea seguir agregando filas
        continuar = input("¿Desea ingresar otra fila? (s/n): ").strip().lower()
        if continuar != "s":
            break

    # --- Escribir logs al finalizar la carga manual ---
    summary_lines = []
    summary_lines.append(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append(f"Base de datos: {nombre_bd}")
    summary_lines.append(f"Tabla: {nombre_tabla}")
    summary_lines.append(f"Intentos totales: {attempt_counter}")
    summary_lines.append(f"Filas insertadas correctamente: {filas_insertadas}")
    summary_lines.append(f"Filas con error: {len(errores)}")
    summary_text = "\n".join(summary_lines)

    # Escribe el resumen en un archivo txt
    write_text_log(summary_path, summary_text)

    # Si hubieron filas insertadas, las volcamos a un CSV para referencia
    if filas_insertadas_data:
        fieldnames = columnas  # Orden de columnas como en la tabla
        rows_for_csv = []
        for r in filas_insertadas_data:
            # Rellena cada fila con todas las keys esperadas (si falta alguna, queda vacía)
            row = {k: r.get(k, "") for k in fieldnames}
            rows_for_csv.append(row)
        write_csv(inserted_csv, fieldnames, rows_for_csv)

    # Si ocurrieron errores, escribimos un CSV con detalle (attempt,error,traceback + columnas)
    if errores:
        fieldnames = ["attempt", "error", "traceback"] + columnas
        rows_err = []
        for err in errores:
            # Asegura que cada registro tenga todas las keys del encabezado
            row = {k: err.get(k, "") for k in fieldnames}
            rows_err.append(row)
        write_csv(errors_csv, fieldnames, rows_err)

    # Mensaje final con ubicación de los logs generados
    print(f"\n📁 Logs guardados en: {os.path.abspath(logs_dir)}")
    print(f" - Resumen: {os.path.basename(summary_path)}")
    if filas_insertadas_data:
        print(f" - Filas insertadas: {os.path.basename(inserted_csv)}")
    if errores:
        print(f" - Errores: {os.path.basename(errors_csv)}")


# ==============================
# FUNCIÓN: Carga por archivo (con logs)
# ==============================

def carga_por_archivo(cursor):
    """
    Inserta datos en una tabla desde un archivo Excel, CSV, TXT o JSON.
    Genera:
      - summary txt con totales
      - CSV con filas que NO se cargaron y motivo
    """
    # Validar BD y tabla
    nombre_bd = validar_base_datos(cursor)
    nombre_tabla = validar_tabla(cursor)

    # Solicita ruta y nombre del archivo
    ruta = input("Ruta del archivo: ").strip()
    archivo = input("Nombre del archivo (incluya extensión): ").strip()
    path = os.path.join(ruta, archivo)  # Construye la ruta completa

    # Leer archivo con pandas según extensión
    try:
        if archivo.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(path)
        elif archivo.lower().endswith(".csv"):
            df = pd.read_csv(path, encoding="utf-8")
        elif archivo.lower().endswith(".txt"):
            df = pd.read_csv(path, sep="\t", encoding="utf-8")
        elif archivo.lower().endswith(".json"):
            df = pd.read_json(path)
        else:
            # Si no es un formato soportado, informa y retorna
            print("❌ Formato de archivo no soportado.")
            return
    except Exception as e:
        # Si falla la lectura del archivo, muestra error y retorna
        print(f"❌ Error al cargar archivo: {str(e)}")
        return

    # Obtener columnas de la tabla SQL (TOP 0 para no traer datos)
    try:
        cursor.execute(f"SELECT TOP 0 * FROM [{nombre_tabla}]")
        columnas_sql = [col[0] for col in cursor.description]  # Nombres de columnas desde cursor
    except Exception as e:
        print(f"❌ Error al obtener columnas: {str(e)}")
        return

    # Filtramos Bi_ejecucion porque lo va a poner la BD con GETDATE()
    columnas_sql_sin_ejecucion = [col for col in columnas_sql if col.lower() != "bi_ejecucion"]
    columnas_archivo = df.columns.tolist()  # Columnas que trae el archivo

    # Verificamos si hay columnas faltantes o sobrantes
    columnas_faltantes = [col for col in columnas_sql_sin_ejecucion if col not in columnas_archivo]
    columnas_sobrantes = [col for col in columnas_archivo if col not in columnas_sql_sin_ejecucion]

    if columnas_faltantes or columnas_sobrantes:
        # Si no hay correspondencia exacta, mostramos detalle y pedimos corregir
        print("\n❌ Las columnas del archivo no coinciden con la tabla.")
        if columnas_faltantes:
            print("Faltan en el archivo:")
            for col in columnas_faltantes:
                print(f"  - {col}")
        if columnas_sobrantes:
            print("No existen en la tabla:")
            for col in columnas_sobrantes:
                print(f"  - {col}")
        print("Corrija el archivo y vuelva a intentar.")
        return

    # --- Preparar logs para carga por archivo ---
    logs_dir = os.path.join(os.getcwd(), "logs")
    ensure_dir(logs_dir)
    ts = timestamp_str()
    summary_path = os.path.join(logs_dir, f"log_file_{nombre_tabla}_{ts}_summary.txt")
    errors_csv = os.path.join(logs_dir, f"log_file_{nombre_tabla}_{ts}_errors.csv")

    filas_procesadas = 0
    filas_cargadas = 0
    errores = []  # Lista de diccionarios con detalle de filas que no se cargaron

    # Recorre cada fila del DataFrame para insertarla
    for idx, fila in df.iterrows():
        filas_procesadas += 1
        row_num = idx + 1  # Número humano de fila (empieza en 1)
        try:
            valores = []
            # Validación: no permitir NaN en campos requeridos (según regla original)
            for col in columnas_sql_sin_ejecucion:
                val = fila[col]
                if pd.isna(val):
                    # Si hay un valor nulo, provocamos un error para registrarlo
                    raise ValueError(f"Campo '{col}' en blanco (fila {row_num})")
                # Append del valor tal cual. Si necesitas conversiones, deben implementarse.
                valores.append(val)
            # Construye la sentencia INSERT y usa GETDATE() para Bi_ejecucion
            placeholders = ", ".join("?" for _ in columnas_sql_sin_ejecucion)
            columnas_insert = ", ".join(columnas_sql_sin_ejecucion) + ", Bi_ejecucion"
            sentencia = f"INSERT INTO [{nombre_tabla}] ({columnas_insert}) VALUES ({placeholders}, GETDATE())"
            cursor.execute(sentencia, valores)
            cursor.connection.commit()  # Confirma cada fila correcta
            filas_cargadas += 1
        except Exception as e:
            # Si hay error, guardamos traza y datos de la fila para el CSV de errores
            tb = traceback.format_exc()
            row_data = {col: ("" if pd.isna(fila[col]) else str(fila[col])) for col in columnas_sql_sin_ejecucion}
            errores.append({
                "row": row_num,
                "error": str(e),
                "traceback": tb,
                **row_data
            })

    # --- Escribir resumen y errores ---
    summary_lines = []
    summary_lines.append(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append(f"Base de datos: {nombre_bd}")
    summary_lines.append(f"Tabla: {nombre_tabla}")
    summary_lines.append(f"Archivo procesado: {archivo}")
    summary_lines.append(f"Filas procesadas: {filas_procesadas}")
    summary_lines.append(f"Filas cargadas correctamente: {filas_cargadas}")
    summary_lines.append(f"Filas con error: {len(errores)}")
    summary_text = "\n".join(summary_lines)
    # Guarda el resumen en un txt
    write_text_log(summary_path, summary_text)

    # Si hay errores, crea CSV con columnas: row,error,traceback + columnas del archivo
    if errores:
        fieldnames = ["row", "error", "traceback"] + columnas_sql_sin_ejecucion
        rows_err = []
        for e in errores:
            row = {k: e.get(k, "") for k in fieldnames}
            rows_err.append(row)
        write_csv(errors_csv, fieldnames, rows_err)

    # Mensajes finales informativos
    print(f"\n✅ Carga finalizada. Resumen guardado en: {os.path.abspath(summary_path)}")
    if errores:
        print(f"⚠️ Hubo errores - ver: {os.path.abspath(errors_csv)}")
    else:
        print("✅ Todas las filas se cargaron correctamente.")


# ==============================
# MENÚ PRINCIPAL
# ==============================

def menu_principal():
    # Intenta conectar hasta que haya una conexión válida
    conexion = None
    while not conexion:
        conexion = conectar_sqlserver()
    cursor = conexion.cursor()

    # Bucle del menu que permite repetir acciones sin reiniciar el script
    while True:
        print("\n=== MENÚ PRINCIPAL ===")
        print("1. Crear nueva tabla")
        print("2. Cargar datos a tabla existente")
        print("3. Salir")
        opcion = input("Seleccione una opción: ").strip()

        if opcion == "1":
            crear_tabla(cursor)
        elif opcion == "2":
            print("\n¿Desea hacer carga manual o por archivo?")
            print("1. Manual")
            print("2. Por archivo")
            tipo_carga = input("Seleccione una opción: ").strip()
            if tipo_carga == "1":
                carga_manual(cursor)
            elif tipo_carga == "2":
                carga_por_archivo(cursor)
            else:
                print("⚠️ Opción inválida.")
        elif opcion == "3":
            print("👋 Saliendo del programa...")
            break
        else:
            print("⚠️ Opción inválida.")


# ==============================
# EJECUCIÓN PRINCIPAL
# ==============================

if __name__ == "__main__":
    # Punto de entrada cuando se ejecuta el script directamente
    menu_principal()
