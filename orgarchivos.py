import os
import shutil

# Definimos las extensiones de los tipos de archivos que vamos a organizar
extensiones_fotos = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
extensiones_audio = ['.mp3', '.wav', '.flac', '.aac', '.m4a']
extensiones_excel = ['.xls', '.xlsx', '.xlsm', '.csv']
extensiones_word = ['.doc', '.docx', '.rtf', '.odt']
extensiones_powerbi = ['.pbix']
extenciones_pdf=['.pdf']
extensiones_otros = []

def organizar_archivos(carpeta_origen):
    """
    Organiza los archivos dentro de una carpeta en subcarpetas basadas en su tipo de archivo.
    """
    
    # Lista con las subcarpetas donde se organizarán los archivos
    carpetas = ['fotos', 'audio', 'excel', 'word', 'powerbi','pdf','otros']
    
    # Crear las subcarpetas si no existen
    for carpeta in carpetas:
        ruta_carpeta = os.path.join(carpeta_origen, carpeta)
        if not os.path.exists(ruta_carpeta):
            os.makedirs(ruta_carpeta)  # Crear subcarpetas si no existen
    
    # Recorremos todos los archivos de la carpeta de origen
    for archivo in os.listdir(carpeta_origen):
        ruta_archivo = os.path.join(carpeta_origen, archivo)
        
        # Si el objeto es una carpeta, lo ignoramos
        if os.path.isdir(ruta_archivo):
            continue
        
        # Extraemos la extensión del archivo
        nombre, extension = os.path.splitext(archivo)
        extension = extension.lower()  # Convertir la extensión a minúsculas para asegurar la comparación
        
        # Definir la ruta de destino según la extensión
        if extension in extensiones_fotos:
            destino = os.path.join(carpeta_origen, 'fotos', archivo)
        elif extension in extensiones_audio:
            destino = os.path.join(carpeta_origen, 'audio', archivo)
        elif extension in extensiones_excel:
            destino = os.path.join(carpeta_origen, 'excel', archivo)
        elif extension in extensiones_word:
            destino = os.path.join(carpeta_origen, 'word', archivo)
        elif extension in extensiones_powerbi:
            destino = os.path.join(carpeta_origen, 'powerbi', archivo)
        else:
            destino = os.path.join(carpeta_origen, 'otros', archivo)
        
        # Mover el archivo a la subcarpeta correspondiente
        shutil.move(ruta_archivo, destino)
        print(f"Moviendo {archivo} a {destino}")

# Ruta de la carpeta de origen que deseas organizar
carpeta_origen = r"C:\Users\emaur\OneDrive\Desktop\monica"  # Cambia esta ruta si es necesario

# Ejecutamos la función para organizar los archivos
organizar_archivos(carpeta_origen)
