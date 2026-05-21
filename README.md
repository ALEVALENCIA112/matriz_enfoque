# Matriz de Enfoque 🎯

Aplicación multiplataforma moderna desarrollada en **Python** utilizando el framework **Flet**, diseñada para optimizar la gestión del tiempo y organización de tareas mediante un enfoque de productividad estructurado.

## 📦 Arquitectura del Proyecto
- `main.py`: Lógica y diseño para la versión de Escritorio (PC).
- `main_mobile.py`: Optimizaciones reactivas para la versión Móvil (Android).
- `assets/`: Recursos estáticos (imágenes, fuentes, íconos).

## 🛠️ Instrucciones de Compilación (PowerShell)

### 🖥️ Versión de Escritorio (Windows PC)
```powershell
`$pythonDir = (py -c "import sys, os; print(os.path.dirname(sys.executable))"); & "`$pythonDir\Scripts\pyinstaller.exe" --noconfirm --onedir --windowed --paths="`$pythonDir" --add-data "assets;assets" main.py


### 🖥️ Versión Movil (Android apk)
py -c "import os, sys; print(os.path.dirname(sys.executable))" > temp_path.txt && set /p PY_DIR=<temp_path.txt && del temp_path.txt && call "%PY_DIR%\Scripts\flet.exe" build apk --module-name main_mobile


py -m PyInstaller --noconfirm --onedir --windowed --name="Matriz de Enfoque" --icon="assets/app_icon.ico" --add-data "assets;assets" main.py



Se presentaron varios escenarios ya que al desarrollar la app de manera personal, las rutas de onedrive personal causaban conflictos

Se resolvió de modo que:
El archivo apk se creó aparte debido a conflictos con las rutas de onedrive

Mientras que al ocupar la PC del trabajo/oficina, los problemas fueron de certificados SSL por bloqueadores de la red empresarial

Se resolvió de la siguiente manera:
Nos desconectamos de la red empresarial y gracias a las caracteristicas de la PC pudimos usar datos moviles


Creado y Desarrollado Por Alejandro Valencia

Versión
1.0.0 Lanzamiento de App .exe y .apk
1.0.1 Corrección de conectividad con firebase y mejora de creacion