# Arquitectura de la versión web

## Objetivo
Servir el tablero Mission Center directamente en el navegador, manteniendo los colectores de datos originales pero eliminando la dependencia de PySide/Qt.

## Componentes principales

```
mission_center/
├── core/             # Configuración, temas y utilidades comunes
│   ├── config.py
│   ├── theme.py
│   └── updater.py
├── data/             # Colectores psutil / hw opcional
├── models/           # Dataclasses con snapshots serializables
└── web/
    ├── collector.py  # Hilo de adquisición + ventanas deslizantes
    ├── server.py     # Servidor HTTP (http.server + endpoints JSON)
    ├── templates/
    │   └── index.html
    └── static/
        ├── css/styles.css
        └── js/app.js
```

### Flujo de datos
1. `DataCollector` inicia un hilo que consulta los proveedores cada segundo.
2. Para cada snapshot se normaliza a `dict` utilizando `dataclasses.asdict`.
3. Se almacenan históricas cortas (60 muestras) y medias (5 min) según el tipo de métrica.
4. El servidor expone:
   - `GET /api/current` → snapshot instantáneo.
   - `GET /api/history` → históricos agregados para gráficas.
5. La SPA (Chart.js + vanilla JS) consume ambos endpoints en intervalos de 1 s.
6. El UI renderiza tarjetas, tablas y gráficos (CPU, memoria, IO, sensores, etc.).

### APIs y formato
- **CPU:** `usage_percent`, `per_core[]`, `frequency_current_mhz`, `load_average`, `interrupts`.
- **Memoria:** `percent`, `total_bytes`, `swap_percent`, `swap_used_bytes`.
- **Discos/IO:** `devices[]` con lecturas/escrituras por segundo; histórico de MB/s.
- **Red:** `interfaces[]` con throughput instantáneo.
- **Procesos:** lista ordenada por CPU (`ProcessSnapshot.processes`).
- **Sensores:** grupos de temperatura, lecturas de ventiladores, batería y fuentes de energía.
- **Sistema:** información de hardware, BIOS, uptime y enlaces PCIe.

## Stack tecnológico

- **Backend:** Python 3.10+, `http.server.ThreadedHTTPServer`, `psutil`.
- **Frontend:** HTML estático + Chart.js 4, sin framework.
- **Serialización:** `dataclasses.asdict` + utilidades propias para listas anidadas.
- **Históricos:** `collections.deque` con tamaño configurable (`HISTORY` compartido).

## Consideraciones de implementación

- El colector es reiniciable (`start/stop`) para tests y scripts.
- Los endpoints añaden cabecera `Access-Control-Allow-Origin: *` para facilitar integraciones.
- Las gráficas se actualizan en modo "none" (sin animación) para mantener 60 FPS.
- `Chart.js` se carga vía CDN; no requiere build toolchain.
- Los scripts en `scripts/` permiten smoke tests y ejecuciones temporales del servidor.

## Futuras mejoras

- Añadir exportación WebSocket para reducir llamadas periódicas.
- Empaquetar como imagen Docker/OCI.
- Mejorar temas (claro/oscuro) y soporte PWA.
- Integrar autenticación básica para despliegues remotos.

