import os
nombre_carpeta = 'prueba2'
ruta= ruta = r'C:\Users\emaur\OneDrive\Desktop\edwin'
rutacompleta=os.path.join(ruta,nombre_carpeta)
if not os.path.exists(rutacompleta):
   os.mkdir(rutacompleta)
   print('carpeta creada')
else:
   print('ya existe la carpeta')