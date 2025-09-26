# Mission Center Web

Monitor avanzado estilo Mission Center de Windows, reconstruido como aplicación web pura sobre Python + psutil. Ofrece paneles en tiempo real, históricos deslizantes y vistas detalladas para CPU, memoria, GPU, almacenamiento, red, procesos, sensores y sistema.

## 🚀 Inicio rápido

### Instalación
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Lanzamiento Recomendado (Con Permisos Completos)
```bash
./launch-privileged.sh
```

### Lanzamiento Alternativo
```bash
python -m mission_center.web.server
# O directamente: python main.py
```

La consola mostrará la URL local (por defecto `http://127.0.0.1:8080`). Abre esa dirección en el navegador para acceder al tablero.

## 🔐 Sistema de Permisos

Mission Center incluye detección automática de permisos y lanzamiento inteligente:

- **🔓 Acceso completo**: Con privilegios de root (recomendado)
- **🟢 Acceso bueno**: 80%+ de métricas disponibles
- **🟡 Acceso parcial**: Funcionalidad básica garantizada
- **🔒 Acceso limitado**: Sin sensores/temperaturas

El indicador de permisos aparece en tiempo real en la interfaz web. Para acceso completo al hardware, usa `./launch-privileged.sh` que solicita permisos automáticamente vía PolicyKit o sudo.

Ver [docs/permissions.md](docs/permissions.md) para detalles completos.

## ✨ Características principales

- **Panel general** con tarjetas para CPU, memoria, discos y red, junto a gráficos históricos.
- **Rendimiento**: tarjetas individuales por núcleo con mini-gráficas embebidas y resumen de GPU.
- **Analítica**: gráfico multiserie para todos los núcleos y series independientes de lectura/escritura de discos.
- **Procesos**: tabla dinámica top-N por CPU con memoria y usuario.
- **Sensores**: temperaturas agrupadas, RPM de ventiladores y estado de alimentación (batería y fuentes).
- **Ficha del sistema**: datos de hardware, firmware y uptime más la tabla completa de enlaces PCIe.
- **Históricos deslizantes** para CPU, memoria, IO, red, temperatura y ventiladores.

Todos los datos provienen de los colectores existentes (`mission_center.data`), compartidos con la versión de escritorio original.

## 🧱 Arquitectura

```
mission_center/
  core/               # Configuración, temas y utilidades de actualización
  data/               # Colectores basados en psutil y utilidades opcionales
  models/             # Dataclasses con la forma de las instantáneas
  web/
    collector.py      # Hilo de adquisición y almacenamiento de históricos
    server.py         # Servidor HTTP con endpoints REST + assets estáticos
    templates/
      index.html      # Shell de la SPA
    static/
      css/styles.css  # Tema Fluent dark
      js/app.js       # Orquestador principal de la interfaz (Chart.js, navegación)
      js/api.js       # Cliente ligero para `/api/current` y `/api/history`
      js/utils.js     # Conversión de unidades y utilidades de formato reutilizables
requirements.txt      # Solo psutil (dependencias opcionales documentadas en el código)
```

El servidor se basa en `http.server` y expone:
- `/` → HTML principal.
- `/static/*` → assets.
- `/api/current` → snapshot actual completo.
- `/api/history` → históricos en ventanas configurables.

## 🛠️ Configuración

- Python **3.10+**.
- Dependencias del sistema para sensores opcionales (`lm-sensors`, `smartmontools`, drivers NVML, etc.).
- Dependencias Python opcionales para ampliar métricas:
  ```bash
  pip install pynvml pyudev
  ```
- El servidor web expone controles de seguridad básicos configurables en `mission_center/core/config.py`:
  - **CORS** con lista blanca de orígenes (`SECURITY.allowed_origins`).
  - **Autenticación HTTP Basic** opcional (usuario y contraseña).
  - **Rate limiting** simple por IP (ventana y número máximo de solicitudes).
  Ajusta estos valores antes de desplegar en redes compartidas.

## 📐 Diseño UI

- Tema oscuro inspirado en Fluent/Windows 11.
- Navegación lateral con secciones conmutables (`Resumen`, `Rendimiento`, `Analítica`, `Procesos`, `Sensores`, `Sistema`).
- Tarjetas con valores destacados, etiquetas secundarias y mini-charts por núcleo.
- Chart.js 4 para las series temporales y visualizaciones agregadas.

## ✅ Validación

El proyecto incluye un modo de recogida continua; al cerrar el servidor, el hilo de adquisición se detiene limpiamente. Ejecuta:

```bash
python -m compileall mission_center
```

para validar la sintaxis de los módulos.

> ℹ️ Los chequeos de permisos del sistema ahora se ejecutan de forma diferida en segundo plano y se cachean durante varios minutos, reduciendo la latencia de arranque. El muestreo de procesos también se limita a un intervalo mínimo de 2 s para evitar carga innecesaria en hosts con cientos de procesos.

## 📄 Nota histórica

La UI basada en PySide6 se retiró en favor de la versión web. Se eliminaron los módulos Qt y los recursos asociados; los colectores y modelos viven ahora en `mission_center.data` y `mission_center.models`, por lo que las dependencias de PySide ya no son necesarias.
