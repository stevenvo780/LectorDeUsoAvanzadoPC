# Mission Center Web

Monitor avanzado estilo Mission Center de Windows, reconstruido como aplicación web pura sobre Python + psutil. Ofrece paneles en tiempo real, históricos deslizantes y vistas detalladas para CPU, memoria, GPU, almacenamiento, red, procesos, sensores y sistema.

## 🚀 Inicio rápido

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m mission_center.web.server
```

La consola mostrará la URL local (por defecto `http://127.0.0.1:8080`). Abre esa dirección en el navegador para acceder al tablero.

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
      js/app.js       # Lógica de la interfaz (Chart.js, navegación, renders)
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

## 📄 Nota histórica

La UI basada en PySide6 se retiró en favor de la versión web. Se eliminaron los módulos Qt y los recursos asociados; los colectores y modelos viven ahora en `mission_center.data` y `mission_center.models`, por lo que las dependencias de PySide ya no son necesarias.
