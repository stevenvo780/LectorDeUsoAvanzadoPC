# Mission Center Clone - Monitor de Sistema

Monitor avanzado estilo Mission Center de Windows, construido en PySide6 con cobertura total de sensores de hardware y paneles en tiempo real.

## 🚀 Ejecución rápida
```bash
python -m mission_center_clone.app
```
> Para entornos sin pantalla física: `QT_QPA_PLATFORM=offscreen python scripts/smoke.py`

## ✨ Qué incluye ahora
- **🔥 CPU**: uso instantáneo, núcleos individuales, frecuencias y promedios de carga.
- **💾 Memoria**: RAM + swap con métricas agregadas y gráficas históricas.
- **💽 Almacenamiento**: lecturas/escrituras por dispositivo, montajes y espacio disponible.
- **🌐 Red**: interfaces activas, throughput en tiempo real y autodetección de IPs.
- **📊 Procesos**: tabla ordenable por CPU/RAM con IO y comando completo.
- **🎮 GPU / PCIe**: métricas NVML opcionales, enlaces PCIe actuales y máximos.
- **🌡️ Sensores**: temperaturas agrupadas por origen, ventiladores, batería, fuentes de poder.
- **🖥️ Sistema**: ficha completa (OS, kernel, BIOS, placa base, chasis, virtualización, GPUs).
- **📈 Históricos**: gráficos rolling window para CPU, GPU, IO, temperatura y ventiladores.

## 🎯 Interfaz tipo Mission Center
- Barra lateral con secciones: Panel, Procesos, Rendimiento, Sensores y Sistema.
- Tarjetas compactas con estado resumido y mensajes claros cuando faltan datos.
- Tabs de rendimiento por recurso con gráficos en vivo (Qt Charts).
- Vistas especializadas para sensores con tablas dinámicas y gráficas de máximos/promedios.
- Tema oscuro inspirado en Fluent Design; estilizable desde `core/theme.py`.

## 📦 **Requisitos**
```bash
pip install -r requirements.txt
```

## 📁 **Estructura**
```
mission_center_clone/         # Paquete Python con colectores
mission_center_advanced.py    # Legacy: servidor web/SPA opcional
requirements.txt              # Dependencias mínimas
docs/                         # Documentación técnica
```

## 🔧 Arquitectura
- **Qt Widgets**: UI nativa en PySide6 (sin servidor web).
- **Coordinador**: `DataUpdateCoordinator` orquesta los proveedores en intervalos independientes.
- **Modelo de datos**: dataclasses inmutables para snapshots (CPU, sensores, sistema, etc.).
- **Colectores**: psutil como base, opcionales `pynvml`/`pyudev` para GPU/PCIe.

## 🌐 **Acceso**
Una vez ejecutado, accede a **http://localhost:8081** para ver la interfaz completa estilo Windows con monitoreo en tiempo real del sistema.

## Características
- **Panel general** con 11 tarjetas (CPU, memoria, GPU, discos, red, IO, PCIe, temperatura, ventiladores, batería, energía, sistema).
- **Gestor de procesos** con ordenamiento por consumo y métricas de IO por proceso.
- **Pestañas de rendimiento** por categoría, replicando la navegación del Mission Center.
- **Vista de sensores** con tabs para temperaturas, ventiladores y energía (batería/fuentes).
- **Ficha del sistema** con BIOS, fabricante, chasis, uptime, virtualización y GPUs.
- Arquitectura modular para ampliar proveedores o sustituir la UI sin cambiar colectores.

## Requisitos
- Python 3.10+ (probado en 3.10/3.11).
- Dependencias de sistema para Qt (Linux):
  - libxcb, libxkbcommon, libxcb-cursor0 (o xcb-cursor0), libxrender, libxcomposite, libxi, libx11-xcb, etc. En Debian/Ubuntu:
    ```bash
    sudo apt-get update
    sudo apt-get install -y libxkbcommon-x11-0 libxrender1 libxcomposite1 libxi6 libxcb-cursor0
    ```
- Dependencias Python (pip):
  ```bash
  pip install -r requirements.txt
  ```
- Dependencias opcionales para métricas extendidas:
  ```bash
  pip install pynvml pyudev
  ```
- Acceso a `/sys` y utilidades como `lm-sensors`, `smartmontools` y drivers NVML mejoran la cobertura de datos.

## Ejecución
1. Crear y activar un entorno virtual (opcional pero recomendado).
2. Instalar dependencias.
3. Ejecutar la aplicación (requiere entorno gráfico disponible):
   ```bash
   python -m mission_center_clone.app
   ```

### Modo headless (pruebas rápidas)
- Smoke test de imports/creación de UI (offscreen):
  ```bash
  QT_QPA_PLATFORM=offscreen python scripts/smoke.py
  ```
- Loop de 3s del event loop (offscreen):
  ```bash
  QT_QPA_PLATFORM=offscreen python scripts/run_headless.py
  ```

## Estructura
- `mission_center_clone/app.py`: punto de entrada Qt.
- `mission_center_clone/core/`: configuración, tema y coordinador de actualizaciones.
- `mission_center_clone/data/`: proveedores de datos (CPU, GPU, IO, PCIe, procesos, etc.).
- `mission_center_clone/models/`: dataclasses con las instantáneas de recursos.
- `mission_center_clone/ui/`: componentes Qt que replican el flujo del Mission Center.
- `docs/architecture.md`: detalle de alcance, arquitectura y limitaciones.

## Próximos pasos sugeridos
- Integrar gráficas en tiempo real (Qt Charts o PyQtGraph).
- Añadir agrupación de procesos por aplicación/paquete.
- Implementar «App health» y tareas en segundo plano como en Mission Center.
- Persistir histórico para comparar periodos largos y exportar datos.
- Adaptar estilos a Fluent Design con QML o temas personalizados.

> Nota: algunas métricas dependen de soporte del hardware y del kernel. El código maneja faltantes mostrando mensajes informativos en la UI.
