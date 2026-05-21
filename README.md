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



El archivo apk se creó aparte debido a conflictos con las rutas de onedrive



Creado y Desarrollado Por Alejandro Valencia

Versión
1.0.0