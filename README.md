# Mission Center Clone para Linux

Aplicación de monitoreo de recursos inspirada en el Mission Center de Windows 11. Proporciona panel general, vista de procesos y secciones de rendimiento para CPU, memoria, GPU, almacenamiento, red, IO y enlaces PCIe, añadiendo métricas adicionales específicas para Linux.

## Características
- **Panel general** con tarjetas en tiempo real para los recursos clave del sistema.
- **Gestor de procesos** con ordenamiento por consumo y métricas de IO por proceso.
- **Pestañas de rendimiento** por categoría, replicando la navegación del Mission Center.
- **Monitoreo IO** agregado por segundo (lecturas/escrituras y operaciones).
- **Mapa PCIe** con velocidad/anchura del enlace actual y máxima cuando el kernel lo expone.
- Arquitectura modular para ampliar proveedores de datos o reemplazar la interfaz.

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
