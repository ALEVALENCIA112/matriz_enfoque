# Matriz de Enfoque 🎯

Aplicación multiplataforma de alta productividad diseñada en **Python** utilizando **Tkinter** para la suite de escritorio y **Flet (Flutter engine)** para la versión móvil Android (APK), con arquitectura **Local-First** y **Sincronización Asíncrona Híbrida** con Firebase Realtime Database.

---

## 🏗️ Arquitectura del Sistema
- **Local-First & Resiliencia en Red Corporativa**: La aplicación opera al 100% de manera local con latencia de 0 ms. En redes empresariales (con firewalls, proxies o inspección SSL), la aplicación nunca se congela y almacena los cambios en el JSON local. Al detectar red libre o datos móviles, sincroniza automáticamente en segundo plano.
- `main.py`: Punto de entrada para la versión de Escritorio (Windows PC).
- `main_mobile.py`: Punto de entrada para la versión Móvil (Android APK / Flet).
- `core/`: Entidades de dominio, transiciones de estado BuJo/Kanban, Pomodoro Inverso y casos de uso.
- `infrastructure/`: Almacenamiento local atómico y sincronizador híbrido con Firebase.
- `controllers/`: Controlador central MVC reactivo.
- `views/`: Interfaz gráfica de escritorio modularizada (Tkinter).
- `views_mobile/`: Interfaz gráfica táctil y adaptativa para móvil (Flet).
- `assets/`: Recursos estáticos (íconos `.ico` y `.png`).

---

## 🛠️ Instrucciones de Compilación (PowerShell)

### 🖥️ 1. Compilación para Escritorio (Windows `.exe`)
Para compilar un ejecutable portable independiente:

```powershell
py -m PyInstaller --noconfirm --onedir --windowed --name="Matriz de Enfoque" --icon="assets/app_icon.ico" --add-data "assets;assets" main.py
```

El ejecutable resultante se encontrará en la carpeta `dist/Matriz de Enfoque/Matriz de Enfoque.exe`.

---

### 📱 2. Compilación para Móvil (Android `.apk`)
Para generar el archivo `.apk` instalable en Android mediante Flet:

```powershell
flet build apk --module-name main_mobile
```

*Nota: Requiere tener configurado Android SDK / Java JDK en el entorno para la compilación nativa.*

---

## 📋 Registro de Versiones
- **1.0.0**: Lanzamiento inicial de versiones `.exe` y `.apk`.
- **1.0.1**: Corrección de conectividad con Firebase y mejoras de creación.
- **1.0.2**: Manejo de sincronía y estados.
- **1.0.3**: Agregado botón de limpieza en APK y pie de versión.
- **1.0.4**:
  - **Sincronización Asíncrona No Bloqueante**: Eliminación de congelamientos de la UI en redes corporativas con firewall/SSL.
  - **Arquitectura Local-First Robusta**: Métodos atómicos de persistencia y cola de operaciones pendientes.
  - **Resolución de Rutas Multiplataforma**: Almacenamiento seguro en Android y Windows.
  - **Mejoras Visuales y Táctiles**: Redimensionamiento adaptativo en escritorio, soporte de tecla Enter para añadir tareas y compatibilidad con Flet moderno.

---
Creado y Desarrollado por **Alejandro Valencia**