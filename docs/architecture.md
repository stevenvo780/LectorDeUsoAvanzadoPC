# Arquitectura del Visualizador de Recursos

## Objetivo
Crear una aplicación de escritorio para Linux que replique la experiencia del **Mission Center** de Windows 11, aportando vistas detalladas de uso de recursos del sistema y extendiendo la funcionalidad con métricas de IO y PCIe.

## Panorama de Funcionalidades
- Vista general (Dashboard) con tarjetas para CPU, GPU, Memoria, Almacenamiento, Red, Batería y sensores.
- Apartado de procesos con métricas por aplicación, agrupación y orden dinámico.
- Estadísticas históricas mediante gráficos en tiempo real y registros recientes.
- Monitoreo de tareas en segundo plano y aplicaciones iniciadas recientemente.
- Panel de rendimiento por categoría replicando las vistas del Mission Center.
- Vistas adicionales para cargas de **IO** (lectura/escritura) y **PCIe** (ancho de banda, latencia si está disponible).

## Pila Tecnológica
- **Lenguaje:** Python 3.11+
- **UI:** PySide6 (Qt for Python) con estilo similar a Fluent.
- **Gráficas:** PySide6 Charts / PyQtGraph según disponibilidad.
- **Sistema:** psutil, pyudev, pynvml (opcional para GPU NVIDIA), py3nvml.
- **Sensores:** `psutil.sensors_*`, `pySMART` (opcional), `lm-sensors` vía bindings.

## Arquitectura por Capas
```
mission_center_clone/
├── app.py                # arranque Qt, composición principal
├── core/
│   ├── config.py         # rutas y constantes
│   ├── theme.py          # estilos y recursos
│   └── updater.py        # scheduler de actualizaciones
├── data/
│   ├── __init__.py
│   ├── cpu.py            # load, frecuencia, topología
│   ├── memory.py         # RAM, swap
│   ├── gpu.py            # métricas, fallback integrado/os
│   ├── disk.py           # IO, almacenamiento, SMART
│   ├── network.py        # throughput, latencia
│   ├── pcie.py           # topología PCIe y uso (lspci/pyudev)
│   └── processes.py      # scraper de procesos y apps
├── models/
│   ├── resource_snapshot.py
│   └── process_info.py
├── ui/
│   ├── main_window.py    # navegación lateral + stack
│   ├── dashboard.py
│   ├── processes.py
│   ├── performance/
│   │   ├── __init__.py
│   │   ├── cpu_view.py
│   │   ├── memory_view.py
│   │   ├── gpu_view.py
│   │   ├── disk_view.py
│   │   ├── network_view.py
│   │   ├── io_view.py
│   │   └── pcie_view.py
│   └── widgets/          # componentes reutilizables (cards, charts)
└── resources/
    ├── qml/              # (opcional) QML para Fluent look
    └── icons/
```

## Flujo General
1. `app.py` inicializa Qt, carga el tema y lanza `MainWindow`.
2. `MainWindow` gestiona la navegación tipo Mission Center (panel lateral + contenido).
3. Cada vista solicita instantáneas a `core.updater` que orquesta la recolección periódica mediante tareas asincrónicas.
4. Los módulos en `data/` encapsulan accesos a APIs del sistema (psutil, lecturas de /proc, nvml, etc.).
5. Las vistas transforman `ResourceSnapshot` en widgets con gráficas y tablas.
6. Se cachea histórico reciente en memoria para gráficas de 60s/30min.

## Estrategia de Métricas IO y PCIe
- IO: combinar `psutil.disk_io_counters(perdisk=True)` y métricas de procesos (`process.io_counters()`).
- PCIe: usar `pyudev` para mapear dispositivos PCI, consultar velocidad (current/max link speed) y ancho de banda; medir actividad a través de contadores específicos cuando estén disponibles (``/sys/bus/pci/devices/*/``).

## Extensibilidad
- Capa de configuración para habilitar/deshabilitar módulos.
- Sistema de plugins para detectar hardware adicional (GPU AMD/Intel, FPGA, dispositivos de almacenamiento).
- Abstracciones para exportar métricas (Prometheus/OpenTelemetry) si se desea.

## Limitaciones Iniciales
- Algunas métricas dependen de utilidades externas (`lm-sensors`, `nvml`, `smartctl`).
- Obtención de datos PCIe profundos varía según kernel/driver.
- Se entrega implementación base; afinamiento estético y de rendimiento requerirá trabajo adicional.

