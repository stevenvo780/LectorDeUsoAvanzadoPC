import { fetchDashboardData } from "./api.js";
import { formatBytes, formatNumber, formatFrequency, formatDuration } from "./utils.js";

const charts = {};
const miniCharts = new Map();
const coresHistory = new Map();
let currentSection = "overview";
const CORE_HISTORY_LENGTH = 60;

const NAV_ITEMS = Array.from(document.querySelectorAll(".nav-item"));

const STATUS_ELEMENTS = {
    pill: () => document.querySelectorAll('[data-status="pill"], #status-pill'),
    text: () => document.querySelectorAll('[data-status="text"], #status-text'),
    indicator: () => document.querySelectorAll('[data-status="indicator"], #status-indicator'),
    lastUpdate: () => document.querySelectorAll('[data-status="last-update"], #last-update'),
    uptime: () => document.querySelectorAll('[data-status="uptime"], #uptime-value'),
    host: () => document.querySelectorAll('[data-status="host"], #host-name'),
    os: () => document.querySelectorAll('[data-status="os"], #os-name'),
    permissions: () => document.querySelectorAll('[data-status="permissions"], #permissions-indicator'),
};

const SNAPSHOT_ELEMENTS = {
    cpuUsage: () => document.querySelectorAll('[data-snapshot="cpu-usage"]'),
    cpuFrequency: () => document.querySelectorAll('[data-snapshot="cpu-frequency"]'),
    memoryUsage: () => document.querySelectorAll('[data-snapshot="memory-usage"]'),
    swapUsage: () => document.querySelectorAll('[data-snapshot="swap-usage"]'),
    diskIO: () => document.querySelectorAll('[data-snapshot="disk-io"]'),
    netIO: () => document.querySelectorAll('[data-snapshot="net-io"]'),
};

function updateElements(collection, callback) {
    if (!collection) return;
    Array.from(collection).forEach((node) => {
        try {
            callback(node);
        } catch (error) {
            console.warn("Dashboard element update error", error);
        }
    });
}

function updateSnapshot(name, value) {
    const nodes = SNAPSHOT_ELEMENTS[name]?.();
    if (!nodes) return;
    updateElements(nodes, (node) => {
        node.textContent = value;
    });
}

function updateMetric(metricId, value) {
    const nodes = document.querySelectorAll(`[data-metric="${metricId}"]`);
    if (!nodes.length) return;
    updateElements(nodes, (node) => {
        node.textContent = value;
    });
}

function initNavigation() {
    NAV_ITEMS.forEach((item) => {
        item.addEventListener("click", () => {
            NAV_ITEMS.forEach((nav) => nav.classList.remove("active"));
            item.classList.add("active");
            const target = item.dataset.section;
            showSection(target);
        });
    });
}

function showSection(section) {
    document
        .querySelectorAll("main > section")
        .forEach((panel) => panel.classList.add("hidden"));
    const target = document.getElementById(section);
    if (target) {
        target.classList.remove("hidden");
        currentSection = section;
    }
}

function createLineChart(canvasId, options = {}) {
    try {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`Canvas element ${canvasId} not found`);
            return null;
        }
        
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            return null;
        }
        
        const baseConfig = {
            type: "line",
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { mode: "index", intersect: false },
                plugins: { legend: { labels: { color: "#e2e8f0" } } },
                scales: {
                    x: { display: false, ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
                    y: { beginAtZero: true, ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
                },
                elements: { point: { radius: 0 } },
            },
            data: { labels: Array(60).fill(""), datasets: [] },
        };
        
        const ctx = canvas.getContext("2d");
        if (!ctx) {
            console.error(`Cannot get 2D context for ${canvasId}`);
            return null;
        }
        
        return new Chart(ctx, Chart.helpers.merge(baseConfig, options));
    } catch (error) {
        console.error(`Error creating chart ${canvasId}:`, error);
        return null;
    }
}

function setConnectionState(isConnected, customMessage = null) {
    const pills = STATUS_ELEMENTS.pill();
    const texts = STATUS_ELEMENTS.text();
    if (!pills.length || !texts.length) return;

    const reconnecting = !isConnected && (!customMessage || !customMessage.includes("perdida"));
    const baseMessage = isConnected ? "Conectado ✅" : customMessage || "Error de conexión ❌";
    const reconnectMessage = reconnecting ? "Reconectando... 🔄" : baseMessage;

    updateElements(pills, (pill) => {
        pill.classList.remove("online", "offline", "reconnecting");
        if (isConnected) {
            pill.classList.add("online");
            pill.setAttribute("aria-label", "Conexión establecida");
        } else {
            pill.classList.add("offline");
            pill.setAttribute("aria-label", reconnecting ? "Reconectando" : (customMessage || "Conexión caída"));
            if (reconnecting) {
                pill.classList.add("reconnecting");
            }
        }
    });

    updateElements(texts, (node) => {
        node.textContent = reconnectMessage;
    });
}

function updateStatusMeta(current) {
    const lastUpdates = STATUS_ELEMENTS.lastUpdate();
    if (lastUpdates.length) {
        const value = new Date().toLocaleTimeString();
        updateElements(lastUpdates, (node) => {
            node.textContent = value;
        });
    }

    const system = current?.system || {};

    const uptime = STATUS_ELEMENTS.uptime();
    if (uptime.length) {
        const value = system.uptime_seconds != null ? formatDuration(system.uptime_seconds) : "--";
        updateElements(uptime, (node) => {
            node.textContent = value;
        });
    }

    const hostNodes = STATUS_ELEMENTS.host();
    if (hostNodes.length) {
        updateElements(hostNodes, (node) => {
            node.textContent = system.hostname || "--";
        });
    }

    const osNodes = STATUS_ELEMENTS.os();
    if (osNodes.length) {
        const summaryParts = [];
        const osLabel = [system.os_name, system.os_version].filter(Boolean).join(" ");
        if (osLabel) summaryParts.push(osLabel);
        if (system.architecture) summaryParts.push(system.architecture);
        const summary = summaryParts.join(" · ");
        const virt = system.virtualization ? ` (${system.virtualization})` : "";
        const value = summary ? `${summary}${virt}` : "--";
        updateElements(osNodes, (node) => {
            node.textContent = value;
        });
    }
    
    updatePermissionsIndicator(current?.permissions);
}

function updatePermissionsIndicator(permissions) {
    const indicators = STATUS_ELEMENTS.permissions();
    if (!permissions || !indicators.length) return;
    
    const level = permissions.permission_level || "limited";
    const accessPercentage = permissions.access_percentage || 0;
    

    updateElements(indicators, (node) => {
        node.classList.remove("perm-full", "perm-good", "perm-partial", "perm-limited", "perm-container_good", "perm-container_limited");
        node.classList.add(`perm-${level}`);
    });
    

    const icons = {
        full: "🔓",
        good: "🟢", 
        partial: "🟡",
        limited: "🔒",
        container_good: "🐳",
        container_limited: "📦"
    };
    
    const labels = {
        full: "Acceso completo",
        good: "Acceso bueno", 
        partial: "Acceso parcial",
        limited: "Acceso limitado",
        container_good: "Contenedor",
        container_limited: "Contenedor limitado"
    };
    
    const icon = icons[level] || "❓";
    const label = labels[level] || "Desconocido";
    
    const title = permissions.warnings?.length > 0 
        ? `Permisos: ${label}\n\nAdvertencias:\n${permissions.warnings.join('\n')}`
        : `Permisos: ${label} - ${accessPercentage}% de rutas del sistema accesibles`;

    updateElements(indicators, (node) => {
        node.textContent = `${icon} ${label} (${accessPercentage}%)`;
        node.title = title;
    });
}

function initCharts() {
    try {
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            return;
        }
        
        charts.cpu = createLineChart("cpuChart", {
            data: {
                datasets: [
                    {
                        label: "Uso CPU %",
                        data: Array(60).fill(0),
                        borderColor: "#22d3ee",
                        backgroundColor: "rgba(34, 211, 238, 0.18)",
                        fill: true,
                    },
                ],
            },
        });

    charts.memory = createLineChart("memoryChart", {
        data: {
            datasets: [
                {
                    label: "RAM %",
                    data: Array(60).fill(0),
                    borderColor: "#22c55e",
                    backgroundColor: "rgba(34, 197, 94, 0.18)",
                    fill: true,
                },
                {
                    label: "Swap %",
                    data: Array(60).fill(0),
                    borderColor: "#f97316",
                    backgroundColor: "rgba(249, 115, 22, 0.12)",
                    fill: true,
                },
            ],
        },
    });

    charts.disk = createLineChart("diskChart", {
        data: {
            datasets: [
                {
                    label: "Lectura MB/s",
                    data: Array(60).fill(0),
                    borderColor: "#22c55e",
                    backgroundColor: "rgba(34,197,94,0.18)",
                    fill: true,
                },
                {
                    label: "Escritura MB/s",
                    data: Array(60).fill(0),
                    borderColor: "#ef4444",
                    backgroundColor: "rgba(239,68,68,0.18)",
                    fill: true,
                },
            ],
        },
    });

    charts.network = createLineChart("networkChart", {
        data: {
            datasets: [
                {
                    label: "Subida MB/s",
                    data: Array(60).fill(0),
                    borderColor: "#a855f7",
                    backgroundColor: "rgba(168,85,247,0.18)",
                    fill: true,
                },
                {
                    label: "Bajada MB/s",
                    data: Array(60).fill(0),
                    borderColor: "#ec4899",
                    backgroundColor: "rgba(236,72,153,0.18)",
                    fill: true,
                },
            ],
        },
    });

    charts.gpu = createLineChart("gpuChart", {
        data: {
            datasets: [
                {
                    label: "Uso GPU %",
                    data: Array(60).fill(0),
                    borderColor: "#38bdf8",
                    backgroundColor: "rgba(56,189,248,0.18)",
                    fill: true,
                },
            ],
        },
    });

    charts.diskRead = createLineChart("diskReadChart", {
        data: {
            datasets: [
                {
                    label: "Lectura total MB/s",
                    data: Array(60).fill(0),
                    borderColor: "#22c55e",
                    backgroundColor: "rgba(34,197,94,0.18)",
                    fill: true,
                },
            ],
        },
    });

    charts.diskWrite = createLineChart("diskWriteChart", {
        data: {
            datasets: [
                {
                    label: "Escritura total MB/s",
                    data: Array(60).fill(0),
                    borderColor: "#ef4444",
                    backgroundColor: "rgba(239,68,68,0.18)",
                    fill: true,
                },
            ],
        },
    });

    charts.temp = createLineChart("tempChart", {
        data: {
            datasets: [
                {
                    label: "Temperatura máx",
                    data: Array(60).fill(0),
                    borderColor: "#fbbf24",
                    backgroundColor: "rgba(251,191,36,0.18)",
                    fill: true,
                },
                {
                    label: "Temperatura promedio",
                    data: Array(60).fill(0),
                    borderColor: "#f97316",
                    backgroundColor: "rgba(249,115,22,0.12)",
                    fill: true,
                },
            ],
        },
    });

    charts.fans = createLineChart("fanChart", {
        data: {
            datasets: [
                {
                    label: "RPM máx",
                    data: Array(60).fill(0),
                    borderColor: "#38bdf8",
                    backgroundColor: "rgba(56,189,248,0.18)",
                    fill: true,
                },
                {
                    label: "RPM promedio",
                    data: Array(60).fill(0),
                    borderColor: "#22d3ee",
                    backgroundColor: "rgba(34,211,238,0.12)",
                    fill: true,
                },
            ],
        },
    });
    } catch (error) {
        console.error('Error initializing charts:', error);
    }
}

function updateOverview(data) {
    const { cpu, memory, disk, io, network, gpu } = data;

    const cpuUsage = cpu?.usage_percent != null ? `${cpu.usage_percent.toFixed(1)}%` : "--";
    const cpuFreq = formatFrequency(cpu?.frequency_current_mhz);
    updateMetric("cpu-usage", cpuUsage);
    updateMetric("cpu-freq", cpuFreq);
    updateMetric("cpu-cores", formatNumber(cpu?.logical_cores));
    updateMetric("cpu-physical", formatNumber(cpu?.physical_cores));
    updateSnapshot("cpuUsage", cpuUsage);
    updateSnapshot("cpuFrequency", cpuFreq);

    const memoryUsage = memory?.percent != null ? `${memory.percent.toFixed(1)}%` : "--";
    const memoryTotal = formatBytes(memory?.total_bytes);
    const swapUsage = memory?.swap_percent != null ? `${memory.swap_percent.toFixed(1)}%` : "--";
    const swapTotal = formatBytes(memory?.swap_total_bytes);
    updateMetric("mem-usage", memoryUsage);
    updateMetric("mem-total", memoryTotal);
    updateMetric("swap-usage", swapUsage);
    updateMetric("swap-total", swapTotal);
    const memorySnapshot = memory ? `${memoryUsage} de ${memoryTotal}` : "--";
    const swapSnapshot = memory ? `${swapUsage} de ${swapTotal}` : "--";
    updateSnapshot("memoryUsage", memorySnapshot);
    updateSnapshot("swapUsage", swapSnapshot);

    if (disk && io) {
        const totalRead = disk.devices?.reduce((sum, dev) => sum + (dev.read_bytes_per_sec || 0), 0) || 0;
        const totalWrite = disk.devices?.reduce((sum, dev) => sum + (dev.write_bytes_per_sec || 0), 0) || 0;
        const ioTotal = io.read_bytes_per_sec + io.write_bytes_per_sec;
        updateMetric("disk-read", `${formatBytes(totalRead)}/s`);
        updateMetric("disk-write", `${formatBytes(totalWrite)}/s`);
        updateMetric("disk-count", formatNumber(disk.devices?.length ?? 0));
        updateMetric("io-total", `${formatBytes(ioTotal)} /s`);
        updateSnapshot("diskIO", `${formatBytes(totalRead)}/s ↑ · ${formatBytes(totalWrite)}/s ↓`);
    } else {
        updateMetric("disk-read", "--");
        updateMetric("disk-write", "--");
        updateMetric("disk-count", "--");
        updateMetric("io-total", "--");
    }

    if (network) {
        const totalSent = network.interfaces?.reduce((sum, iface) => sum + (iface.sent_bytes_per_sec || 0), 0) || 0;
        const totalRecv = network.interfaces?.reduce((sum, iface) => sum + (iface.recv_bytes_per_sec || 0), 0) || 0;
        updateMetric("net-sent", `${formatBytes(totalSent)}/s`);
        updateMetric("net-recv", `${formatBytes(totalRecv)}/s`);
        updateMetric(
            "net-interfaces",
            formatNumber(network.interfaces?.filter((iface) => iface.is_up).length ?? 0),
        );
        updateSnapshot("netIO", `${formatBytes(totalSent)}/s ↑ · ${formatBytes(totalRecv)}/s ↓`);
    } else {
        updateMetric("net-sent", "--");
        updateMetric("net-recv", "--");
        updateMetric("net-interfaces", "--");
    }

    const gpuList = Array.isArray(gpu) ? gpu : [];
    updateMetric("gpu-count", formatNumber(gpuList.length));

    if (gpuList.length) {
        const totalUsage = gpuList.reduce((sum, card) => sum + (card.utilization_percent || 0), 0);
        const avgUsage = totalUsage / gpuList.length;
        const totalMemory = gpuList.reduce((sum, card) => sum + (card.memory_total_bytes || 0), 0);
        const usedMemory = gpuList.reduce((sum, card) => sum + (card.memory_used_bytes || 0), 0);
        const maxTemp = gpuList.reduce(
            (max, card) => (card.temperature_celsius != null ? Math.max(max, card.temperature_celsius) : max),
            Number.NEGATIVE_INFINITY,
        );
        const avgClock = (() => {
            const clocks = gpuList
                .map((card) => card?.extra?.graphics_clock_mhz)
                .filter((value) => typeof value === "number" && !Number.isNaN(value));
            if (!clocks.length) return null;
            return clocks.reduce((sum, value) => sum + value, 0) / clocks.length;
        })();

        updateMetric("gpu-usage", `${avgUsage.toFixed(1)}%`);
        if (totalMemory > 0) {
            updateMetric("gpu-memory", `${formatBytes(usedMemory)} / ${formatBytes(totalMemory)}`);
        } else {
            updateMetric("gpu-memory", usedMemory ? formatBytes(usedMemory) : "--");
        }
        updateMetric("gpu-temp", maxTemp > Number.NEGATIVE_INFINITY ? `${maxTemp.toFixed(1)} °C` : "--");
        updateMetric("gpu-clock", avgClock != null ? `${avgClock.toFixed(0)} MHz` : "--");
    } else {
        updateMetric("gpu-usage", "--");
        updateMetric("gpu-memory", "--");
        updateMetric("gpu-temp", "--");
        updateMetric("gpu-clock", "--");
    }
}

function ensureMiniChart(coreId, label) {
    if (miniCharts.has(coreId)) {
        return miniCharts.get(coreId);
    }
    const canvas = document.getElementById(`core-mini-${coreId}`);
    if (!canvas) return null;
    const chart = new Chart(canvas.getContext("2d"), {
        type: "line",
        data: {
            labels: Array(CORE_HISTORY_LENGTH).fill(""),
            datasets: [
                {
                    label,
                    data: Array(CORE_HISTORY_LENGTH).fill(0),
                    borderColor: `hsl(${(coreId * 360) / 32}, 70%, 60%)`,
                    backgroundColor: `hsla(${(coreId * 360) / 32}, 70%, 60%, 0.18)`,
                    fill: true,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: {
                x: { display: false },
                y: { display: false, min: 0, max: 100 },
            },
            elements: { point: { radius: 0 } },
        },
    });
    miniCharts.set(coreId, chart);
    return chart;
}

function updateCoreGrid(cpu) {
    const cores = cpu?.per_core || [];
    const grid = document.getElementById("cpu-cores-grid");
    

    miniCharts.forEach(chart => chart.destroy());
    miniCharts.clear();
    grid.innerHTML = "";
    
    cores.forEach((core) => {
        const card = document.createElement("div");
        card.className = "core-item";
        const usageText = `${core.usage_percent.toFixed(1)}%`;
        const frequencyText = core.frequency_mhz != null ? formatFrequency(core.frequency_mhz) : "--";
        card.innerHTML = `
            <div class="core-header">
                <span>Núcleo ${core.core_id}</span>
            </div>
            <div class="core-chart">
                <canvas class="core-mini-chart" id="core-mini-${core.core_id}" width="220" height="120"></canvas>
            </div>
            <div class="core-footer">
                <div class="core-footer-block">
                    <span class="core-footer-label">Uso</span>
                    <span class="core-footer-value">${usageText}</span>
                </div>
                <div class="core-footer-block">
                    <span class="core-footer-label">Frecuencia</span>
                    <span class="core-footer-value">${frequencyText}</span>
                </div>
            </div>
        `;
        grid.appendChild(card);
        const history = coresHistory.get(core.core_id) ?? Array(CORE_HISTORY_LENGTH).fill(core.usage_percent);
        if (history.length >= CORE_HISTORY_LENGTH) {
            history.shift();
        }
        history.push(core.usage_percent);
        coresHistory.set(core.core_id, history);
        const chart = ensureMiniChart(core.core_id, `Núcleo ${core.core_id}`);
        if (chart) {
            chart.data.datasets[0].data = [...history];
            chart.update("none");
        }
    });
}

function updatePerformance(data) {
    const { cpu, gpu } = data;
    if (cpu) {
        updateCoreGrid(cpu);
    }
    if (gpu?.length && charts.gpu) {
        const total = gpu.reduce((sum, card) => sum + (card.utilization_percent || 0), 0);
        charts.gpu.data.datasets[0].data.shift();
        charts.gpu.data.datasets[0].data.push(total / gpu.length);
        charts.gpu.update("none");
    }
}

function updateProcesses(data) {
    const container = document.getElementById("processes-list");
    container.innerHTML = "";
    const processes = data.processes?.processes || [];
    processes.slice(0, 20).forEach((proc) => {
        const row = document.createElement("div");
        row.className = "table-row";
        row.innerHTML = `
            <div>${proc.pid}</div>
            <div title="${proc.command_line?.join(" ") ?? ""}">${proc.name}</div>
            <div>${proc.cpu_percent?.toFixed(1) ?? "0.0"}%</div>
            <div>${formatBytes(proc.memory_bytes)}</div>
            <div>${proc.username ?? "--"}</div>
        `;
        container.appendChild(row);
    });
}

function updateSensorTables(data) {
    const tempTable = document.getElementById("temp-table");
    const fanTable = document.getElementById("fan-table");
    const powerTable = document.getElementById("power-table");
    const batteryInfo = document.getElementById("battery-info");

    tempTable.innerHTML = `
        <thead><tr><th>Fuente</th><th>Etiqueta</th><th>Actual</th><th>Alta</th><th>Crítica</th></tr></thead>
        <tbody></tbody>
    `;
    const tempBody = tempTable.querySelector("tbody");
    const tempGroups = data.temperature?.groups || [];
    tempGroups.forEach((group) => {
        group.readings.forEach((reading) => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${reading.source}</td>
                <td>${reading.label ?? "--"}</td>
                <td class="numeric">${reading.current_celsius?.toFixed(1) ?? "--"} °C</td>
                <td class="numeric">${reading.high_celsius?.toFixed(1) ?? "--"} °C</td>
                <td class="numeric">${reading.critical_celsius?.toFixed(1) ?? "--"} °C</td>
            `;
            tempBody.appendChild(row);
        });
    });

    fanTable.innerHTML = `
        <thead><tr><th>Fuente</th><th>Etiqueta</th><th>RPM</th></tr></thead>
        <tbody></tbody>
    `;
    const fanBody = fanTable.querySelector("tbody");
    const fanReadings = data.fans?.readings || [];
    fanReadings.forEach((reading) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${reading.source}</td>
            <td>${reading.label ?? "--"}</td>
            <td class="numeric">${reading.speed_rpm?.toFixed(0) ?? "--"}</td>
        `;
        fanBody.appendChild(row);
    });

    batteryInfo.innerHTML = "";
    const battery = data.battery || {};
    const entries = [
        ["Carga", battery.percent != null ? `${battery.percent.toFixed(0)}%` : "--"],
        ["Restante", battery.secs_left != null ? formatDuration(battery.secs_left) : "--"],
        ["Estado", battery.power_plugged != null ? (battery.power_plugged ? "Enchufada" : "Descargando") : "--"],
        ["Ciclos", battery.cycle_count != null ? battery.cycle_count : "--"],
        ["Temp", battery.temperature_celsius != null ? `${battery.temperature_celsius.toFixed(1)} °C` : "--"],
    ];
    entries.forEach(([label, value]) => {
        const dt = document.createElement("dt");
        dt.textContent = label;
        const dd = document.createElement("dd");
        dd.textContent = value;
        batteryInfo.append(dt, dd);
    });

    powerTable.innerHTML = `
        <thead><tr><th>Fuente</th><th>Estado</th><th>Online</th><th>Voltaje</th><th>Corriente</th><th>Potencia</th><th>Capacidad</th><th>Temp</th></tr></thead>
        <tbody></tbody>
    `;
    const powerBody = powerTable.querySelector("tbody");
    const powerSources = data.power?.sources || [];
    powerSources.forEach((source) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${source.name}</td>
            <td>${source.status ?? "--"}</td>
            <td>${source.is_online != null ? (source.is_online ? "Sí" : "No") : "--"}</td>
            <td class="numeric">${source.voltage_volts != null ? source.voltage_volts.toFixed(2) + " V" : "--"}</td>
            <td class="numeric">${source.current_amperes != null ? source.current_amperes.toFixed(2) + " A" : "--"}</td>
            <td class="numeric">${source.power_watts != null ? source.power_watts.toFixed(2) + " W" : "--"}</td>
            <td class="numeric">${source.capacity_percent != null ? source.capacity_percent.toFixed(1) + "%" : "--"}</td>
            <td class="numeric">${source.temperature_celsius != null ? source.temperature_celsius.toFixed(1) + " °C" : "--"}</td>
        `;
        powerBody.appendChild(row);
    });
}

function updateSystemInfo(data) {
    const systemGrid = document.getElementById("system-info");
    systemGrid.innerHTML = "";
    const system = data.system || {};
    const sections = [
        {
            title: "Hardware",
            fields: [
                ["Modelo", system.system_model],
                ["Fabricante", system.system_manufacturer],
                ["CPU", system.cpu_model],
                ["Arquitectura", system.architecture],
                ["Memoria", system.total_memory_bytes ? formatBytes(system.total_memory_bytes) : "--"],
            ],
        },
        {
            title: "Sistema",
            fields: [
                ["OS", [system.os_name, system.os_version].filter(Boolean).join(" ")],
                ["Kernel", system.kernel_version],
                ["Arranque", system.boot_time ? new Date(system.boot_time * 1000).toLocaleString() : "--"],
                ["Uptime", system.uptime_seconds != null ? formatDuration(system.uptime_seconds) : "--"],
            ],
        },
        {
            title: "Firmware",
            fields: [
                ["BIOS", [system.bios_vendor, system.bios_version].filter(Boolean).join(" ")],
                ["Fecha BIOS", system.bios_date],
                ["Motherboard", system.motherboard],
                ["Virtualización", system.virtualization ?? "--"],
            ],
        },
    ];

    sections.forEach((section) => {
        const card = document.createElement("div");
        card.className = "system-card";
        card.innerHTML = `<h4>${section.title}</h4>`;
        const dl = document.createElement("dl");
        section.fields.forEach(([label, value]) => {
            const dt = document.createElement("dt");
            dt.textContent = label;
            const dd = document.createElement("dd");
            dd.textContent = value || "--";
            dl.append(dt, dd);
        });
        card.appendChild(dl);
        systemGrid.appendChild(card);
    });

    const pcieTable = document.getElementById("pcie-table");
    pcieTable.innerHTML = `
        <thead><tr><th>Dirección</th><th>Dispositivo</th><th>Velocidad</th><th>Ancho</th><th>Vel máx</th><th>Ancho máx</th></tr></thead>
        <tbody></tbody>
    `;
    const tbody = pcieTable.querySelector("tbody");
    const devices = data.pcie?.devices || [];
    devices.forEach((device) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${device.address}</td>
            <td>${[device.vendor, device.device].filter(Boolean).join(" ")}</td>
            <td class="numeric">${device.link_speed_gtps ? device.link_speed_gtps.toFixed(2) + " GT/s" : "--"}</td>
            <td class="numeric">${device.link_width ?? "--"}</td>
            <td class="numeric">${device.max_link_speed_gtps ? device.max_link_speed_gtps.toFixed(2) + " GT/s" : "--"}</td>
            <td class="numeric">${device.max_link_width ?? "--"}</td>
        `;
        tbody.appendChild(row);
    });
}

let updateLoopRetryCount = 0;
let updateLoopRunning = false;
const MAX_RETRY_COUNT = 5;
const RETRY_DELAYS = [1000, 2000, 5000, 10000, 15000];

async function updateLoop() {
    if (updateLoopRunning) return; // Prevent concurrent updates
    updateLoopRunning = true;
    
    try {
        const [current, history] = await fetchDashboardData();
        
        // Reset retry count on successful fetch
        updateLoopRetryCount = 0;
        setConnectionState(true);
        
        // Only update if we have valid data
        if (current) {
            updateStatusMeta(current);
            updateOverview(current);
            updatePerformance(current);
            updateProcesses(current);
            updateSensorTables(current);
            updateSystemInfo(current);
            
            if (current.gpu) updateGPUGrid(current.gpu);
            if (current.io) updateIODevicesGrid(current.io);
        }
        
        if (history) {
            updateHistoryCharts(history);
        }
        
    } catch (error) {
        console.error("Update loop error:", error);
        setConnectionState(false);
        
        // Implement exponential backoff for retries
        updateLoopRetryCount = Math.min(updateLoopRetryCount + 1, MAX_RETRY_COUNT);
        const retryDelay = RETRY_DELAYS[updateLoopRetryCount - 1] || RETRY_DELAYS[RETRY_DELAYS.length - 1];
        
        console.warn(`Retry ${updateLoopRetryCount}/${MAX_RETRY_COUNT} in ${retryDelay}ms`);
        
        // Schedule retry with backoff delay
        setTimeout(() => {
            if (updateLoopRetryCount < MAX_RETRY_COUNT) {
                updateLoop();
            } else {
                console.error("Max retries reached. Stopping updates.");
                setConnectionState(false, "Conexión perdida - Refresca la página");
            }
        }, retryDelay);
    } finally {
        updateLoopRunning = false;
    }
}

function updateHistoryCharts(history) {
    if (!history) return;
    if (charts.cpu && history.cpu) {
        charts.cpu.data.datasets[0].data = history.cpu.map((entry) => entry.usage ?? 0);
        charts.cpu.update("none");
    }
    if (charts.memory && history.memory) {
        charts.memory.data.datasets[0].data = history.memory.map((entry) => entry.usage ?? 0);
        charts.memory.data.datasets[1].data = history.memory.map((entry) => entry.swap_usage ?? 0);
        charts.memory.update("none");
    }
    if (charts.disk && history.disk) {
        charts.disk.data.datasets[0].data = history.disk.map((entry) => (entry.read || 0) / 1024 / 1024);
        charts.disk.data.datasets[1].data = history.disk.map((entry) => (entry.write || 0) / 1024 / 1024);
        charts.disk.update("none");
    }
    if (charts.network && history.network) {
        charts.network.data.datasets[0].data = history.network.map((entry) => (entry.sent || 0) / 1024 / 1024);
        charts.network.data.datasets[1].data = history.network.map((entry) => (entry.recv || 0) / 1024 / 1024);
        charts.network.update("none");
    }
    if (charts.diskRead && history.disk) {
        charts.diskRead.data.datasets[0].data = history.disk.map((entry) => (entry.read || 0) / 1024 / 1024);
        charts.diskRead.update("none");
    }
    if (charts.diskWrite && history.disk) {
        charts.diskWrite.data.datasets[0].data = history.disk.map((entry) => (entry.write || 0) / 1024 / 1024);
        charts.diskWrite.update("none");
    }
    if (charts.temp && history.temperature) {
        const maxValues = history.temperature.map((entry) => {
            const temps = entry.readings?.map((reading) => reading.current ?? 0) ?? [];
            return temps.length ? Math.max(...temps) : 0;
        });
        const avgValues = history.temperature.map((entry) => {
            const temps = entry.readings?.map((reading) => reading.current ?? 0) ?? [];
            if (!temps.length) return 0;
            const sum = temps.reduce((acc, value) => acc + value, 0);
            return sum / temps.length;
        });
        charts.temp.data.datasets[0].data = maxValues;
        charts.temp.data.datasets[1].data = avgValues;
        charts.temp.update("none");
    }
    if (charts.fans && history.fans) {
        const maxValues = history.fans.map((entry) => {
            const values = entry.readings?.map((reading) => reading.speed ?? 0) ?? [];
            return values.length ? Math.max(...values) : 0;
        });
        const avgValues = history.fans.map((entry) => {
            const values = entry.readings?.map((reading) => reading.speed ?? 0) ?? [];
            if (!values.length) return 0;
            const sum = values.reduce((acc, value) => acc + value, 0);
            return sum / values.length;
        });
        charts.fans.data.datasets[0].data = maxValues;
        charts.fans.data.datasets[1].data = avgValues;
        charts.fans.update("none");
    }
}

const gpuCharts = new Map();
const gpuHistory = new Map();

function updateGPUGrid(gpu) {
    const gpus = gpu || [];
    const grid = document.getElementById("gpu-cards-grid");
    
    if (gpus.length === 0) {
        if (!grid.querySelector('.no-gpus-message')) {
            grid.innerHTML = '<div class="no-gpus-message" style="text-align: center; color: var(--text-secondary); padding: 40px;">No hay GPUs detectadas</div>';
        }
        return;
    }


    const existingCards = grid.querySelectorAll('.gpu-card');
    if (existingCards.length !== gpus.length) {

        gpuCharts.forEach(chart => chart.destroy());
        gpuCharts.clear();
        grid.innerHTML = "";
        
        gpus.forEach((gpuData, index) => {
            const card = createGPUCard(gpuData, index);
            grid.appendChild(card);
        });
    } else {

        gpus.forEach((gpuData, index) => {
            updateGPUCardData(existingCards[index], gpuData, index);
        });
    }
}

function createGPUCard(gpuData, index) {
    const card = document.createElement("div");
    card.className = "gpu-card";
    card.setAttribute('data-gpu-index', index);
    
    const memoryUsedGB = (gpuData.memory_used_bytes / (1024 * 1024 * 1024)).toFixed(1);
    const memoryTotalGB = (gpuData.memory_total_bytes / (1024 * 1024 * 1024)).toFixed(1);
    
    card.innerHTML = `
        <div class="gpu-header">
            <h4 class="gpu-title">${gpuData.name}</h4>
            <span class="gpu-vendor">${gpuData.vendor}</span>
        </div>
        <div class="gpu-metrics">
            <div class="gpu-metric">
                <span class="gpu-metric-label">Uso GPU</span>
                <span class="gpu-metric-value gpu-utilization-value">${gpuData.utilization_percent.toFixed(1)}%</span>
            </div>
            <div class="gpu-metric">
                <span class="gpu-metric-label">Temperatura</span>
                <span class="gpu-metric-value gpu-temperature-value">${gpuData.temperature_celsius.toFixed(0)}°C</span>
            </div>
            <div class="gpu-metric">
                <span class="gpu-metric-label">Memoria</span>
                <span class="gpu-metric-value gpu-memory-value">${memoryUsedGB}GB / ${memoryTotalGB}GB</span>
            </div>
            <div class="gpu-metric">
                <span class="gpu-metric-label">Clock GPU</span>
                <span class="gpu-metric-value gpu-clock-value">${gpuData.extra?.graphics_clock_mhz?.toFixed(0) || '--'} MHz</span>
            </div>
        </div>
        <div class="gpu-chart">
            <canvas class="gpu-mini-chart" id="gpu-chart-${index}" width="300" height="120"></canvas>
        </div>
    `;
    

    if (!gpuHistory.has(index)) {
        gpuHistory.set(index, Array(60).fill(gpuData.utilization_percent));
    }
    
    return card;
}

function updateGPUCardData(card, gpuData, index) {

    const utilizationEl = card.querySelector('.gpu-utilization-value');
    const temperatureEl = card.querySelector('.gpu-temperature-value');
    const memoryEl = card.querySelector('.gpu-memory-value');
    const clockEl = card.querySelector('.gpu-clock-value');
    
    if (utilizationEl) utilizationEl.textContent = `${gpuData.utilization_percent.toFixed(1)}%`;
    if (temperatureEl) temperatureEl.textContent = `${gpuData.temperature_celsius.toFixed(0)}°C`;
    
    if (memoryEl) {
        const memoryUsedGB = (gpuData.memory_used_bytes / (1024 * 1024 * 1024)).toFixed(1);
        const memoryTotalGB = (gpuData.memory_total_bytes / (1024 * 1024 * 1024)).toFixed(1);
        memoryEl.textContent = `${memoryUsedGB}GB / ${memoryTotalGB}GB`;
    }
    
    if (clockEl) {
        clockEl.textContent = `${gpuData.extra?.graphics_clock_mhz?.toFixed(0) || '--'} MHz`;
    }
    

    if (!gpuHistory.has(index)) {
        gpuHistory.set(index, Array(60).fill(gpuData.utilization_percent));
    }
    
    const history = gpuHistory.get(index);
    if (history.length >= 60) {
        history.shift();
    }
    history.push(gpuData.utilization_percent);
    

    const existingChart = gpuCharts.get(index);
    if (existingChart) {

        existingChart.data.datasets[0].data = [...history];
        existingChart.update('none');
    } else {

        const canvas = document.getElementById(`gpu-chart-${index}`);
        if (canvas) {
            const ctx = canvas.getContext('2d');
            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array(60).fill(''),
                    datasets: [{
                        label: `GPU ${index} Usage`,
                        data: [...history],
                        borderColor: index === 0 ? '#22d3ee' : '#0078d4',
                        backgroundColor: index === 0 ? 'rgba(34, 211, 238, 0.1)' : 'rgba(0, 120, 212, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 0,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: false },
                        y: { display: false, min: 0, max: 100 }
                    },
                    elements: { point: { radius: 0 } },
                    animation: false
                }
            });
            gpuCharts.set(index, chart);
        }
    }
}

function getDeviceType(deviceName) {
    if (deviceName.startsWith('nvme')) return 'nvme';
    if (deviceName.startsWith('sd')) return 'ssd';
    if (deviceName.startsWith('hd')) return 'hdd';
    return 'other';
}


let stableIODevices = new Set();

function updateIODevicesGrid(io) {
    const grid = document.getElementById("io-devices-grid");
    
    if (!io?.per_device || Object.keys(io.per_device).length === 0) {
        if (!grid.querySelector('.no-io-message')) {
            grid.innerHTML = '<div class="no-io-message" style="text-align: center; color: var(--text-secondary); padding: 40px;">No hay dispositivos I/O detectados</div>';
        }
        return;
    }


    const allRelevantDevices = Object.entries(io.per_device)
        .filter(([name, stats]) => {
            return !name.startsWith('loop') && 
                   !name.startsWith('zram') && 
                   name.match(/^(nvme\d+n\d+|sd[a-z]|md\d+)$/);
        })
        .map(([name, stats]) => name);


    allRelevantDevices.forEach(deviceName => {
        stableIODevices.add(deviceName);
    });


    const devices = Array.from(stableIODevices)
        .slice(0, 12)
        .map(name => [name, io.per_device[name] || { 
            read_bytes_per_sec: 0, 
            write_bytes_per_sec: 0, 
            read_count_per_sec: 0, 
            write_count_per_sec: 0, 
            utilization_percent: 0 
        }]);

    const existingCards = grid.querySelectorAll('.io-device-card');
    

    if (existingCards.length !== devices.length) {
        grid.innerHTML = "";
        
        devices.forEach(([deviceName, stats]) => {
            const card = createIODeviceCard(deviceName, stats);
            grid.appendChild(card);
        });
    } else {

        devices.forEach(([deviceName, stats], index) => {
            if (existingCards[index]) {
                updateIODeviceCardData(existingCards[index], deviceName, stats);
            }
        });
    }
}

function createIODeviceCard(deviceName, stats) {
    const card = document.createElement("div");
    card.className = "io-device-card";
    card.setAttribute('data-device-name', deviceName);
    
    const deviceType = getDeviceType(deviceName);
    
    card.innerHTML = `
        <div class="io-device-header">
            <span class="io-device-name">${deviceName}</span>
            <span class="io-device-type ${deviceType}">${deviceType.toUpperCase()}</span>
        </div>
        <div class="io-device-stats">
            <div class="io-stat">
                <span class="io-stat-label">Lectura</span>
                <span class="io-stat-value io-read-value">--</span>
            </div>
            <div class="io-stat">
                <span class="io-stat-label">Escritura</span>
                <span class="io-stat-value io-write-value">--</span>
            </div>
            <div class="io-stat">
                <span class="io-stat-label">R-IOPS</span>
                <span class="io-stat-value io-read-iops">--</span>
            </div>
            <div class="io-stat">
                <span class="io-stat-label">W-IOPS</span>
                <span class="io-stat-value io-write-iops">--</span>
            </div>
        </div>
        <div class="io-utilization-bar">
            <div class="io-utilization-fill"></div>
        </div>
    `;
    

    updateIODeviceCardData(card, deviceName, stats);
    
    return card;
}

function updateIODeviceCardData(card, deviceName, stats) {
    const readRateEl = card.querySelector('.io-read-value');
    const writeRateEl = card.querySelector('.io-write-value');
    const readIopsEl = card.querySelector('.io-read-iops');
    const writeIopsEl = card.querySelector('.io-write-iops');
    const utilizationFillEl = card.querySelector('.io-utilization-fill');
    
    const readRate = formatBytes(stats.read_bytes_per_sec);
    const writeRate = formatBytes(stats.write_bytes_per_sec);
    const readOps = stats.read_count_per_sec?.toFixed(1) || '0.0';
    const writeOps = stats.write_count_per_sec?.toFixed(1) || '0.0';
    const utilization = Math.min(100, stats.utilization_percent || 0);
    
    if (readRateEl) readRateEl.textContent = `${readRate}/s`;
    if (writeRateEl) writeRateEl.textContent = `${writeRate}/s`;
    if (readIopsEl) readIopsEl.textContent = readOps;
    if (writeIopsEl) writeIopsEl.textContent = writeOps;
    if (utilizationFillEl) {
        utilizationFillEl.style.width = `${utilization}%`;
    }
}

// Interactive Dashboard System
const DASHBOARD_LAYOUT_KEY = 'mission-center-dashboard-layout';
const LEGACY_LAYOUT_KEYS = ['dashboard-layout'];
class InteractiveDashboard {
    constructor() {
        this.widgetsContainer = document.getElementById('widgets-container');
        this.widgetModal = document.getElementById('widget-selector-modal');
        this.selectedWidgetType = null;
        this.draggedWidget = null;
        this.isResizing = false;
        this.currentResizeWidget = null;
        this.placeholder = document.createElement('div');
        this.placeholder.className = 'widget-placeholder';
        this.placeholder.setAttribute('aria-hidden', 'true');
        this.lastResizeDimensions = null;

        // Widget templates
        this.widgetTemplates = {
            cpu: {
                icon: 'cpu',
                title: 'CPU',
                metrics: ['cpu-usage', 'cpu-freq', 'cpu-cores', 'cpu-physical'],
                chartId: 'cpuChart'
            },
            memory: {
                icon: 'memory-stick',
                title: 'Memoria',
                metrics: ['mem-usage', 'mem-total', 'swap-usage', 'swap-total'],
                chartId: 'memoryChart'
            },
            storage: {
                icon: 'hard-drive',
                title: 'Almacenamiento',
                metrics: ['disk-read', 'disk-write', 'disk-count', 'io-total'],
                chartId: 'diskChart'
            },
            network: {
                icon: 'network',
                title: 'Red',
                metrics: ['net-sent', 'net-recv', 'net-interfaces', 'gpu-count'],
                chartId: 'networkChart'
            },
            gpu: {
                icon: 'zap',
                title: 'GPU',
                metrics: ['gpu-usage', 'gpu-memory', 'gpu-temp', 'gpu-clock'],
                chartId: 'gpuChart'
            },
            processes: {
                icon: 'list',
                title: 'Procesos',
                metrics: ['process-count', 'cpu-processes', 'memory-processes'],
                chartId: 'processChart'
            },
            sensors: {
                icon: 'thermometer',
                title: 'Sensores',
                metrics: ['cpu-temp', 'gpu-temp', 'fan-speed', 'voltage'],
                chartId: 'sensorsChart'
            },
            'system-info': {
                icon: 'info',
                title: 'Sistema',
                metrics: ['uptime', 'boot-time', 'users', 'os-info'],
                chartId: null
            }
        };

        if (!this.widgetsContainer) {
            console.warn('InteractiveDashboard: widgets container not found');
            return;
        }

        this.initializeExistingWidgets();
        this.initEventListeners();
        this.loadLayoutFromStorage();
    }

    initializeExistingWidgets() {
        try {
            const widgets = this.widgetsContainer?.querySelectorAll('.widget') || [];
            widgets.forEach((widget) => {
                this.ensureWidgetStructure(widget);
                this.initWidget(widget);
                this.updateDatasetSizing(widget);
            });
        } catch (error) {
            console.error('Error initializing existing widgets:', error);
        }
    }

    ensureWidgetStructure(widget) {
        if (!widget) return;

        widget.classList.add('widget-base');

        if (!widget.dataset.canResize) {
            widget.dataset.canResize = 'true';
        }

        if (!widget.dataset.gridColumnSpan) {
            widget.dataset.gridColumnSpan = '1';
        }

        if (!widget.dataset.gridRowSpan) {
            widget.dataset.gridRowSpan = '1';
        }

        if (!widget.dataset.size) {
            if (widget.classList.contains('widget-large')) {
                widget.dataset.size = 'large';
            } else if (widget.classList.contains('widget-small')) {
                widget.dataset.size = 'small';
            } else {
                widget.dataset.size = 'medium';
            }
        }

        if (!widget.getAttribute('draggable')) {
            widget.setAttribute('draggable', 'true');
        }

        if (!widget.querySelector('.widget-controls [data-action="resize"]')) {
            const controls = widget.querySelector('.widget-controls');
            if (controls) {
                const resizeBtn = document.createElement('button');
                resizeBtn.className = 'widget-btn';
                resizeBtn.dataset.action = 'resize';
                resizeBtn.title = 'Redimensionar';
                resizeBtn.innerHTML = '<i data-lucide="maximize-2"></i>';
                controls.prepend(resizeBtn);
            }
        }

        if (!widget.querySelector('.resize-handles')) {
            const handles = document.createElement('div');
            handles.className = 'resize-handles';
            const handle = document.createElement('div');
            handle.className = 'resize-handle resize-se';
            handles.appendChild(handle);
            widget.appendChild(handles);
        }
    }

    applyWidgetLayoutState(widget, widgetData) {
        if (!widget || !widgetData) return;

        const sizes = ['small', 'medium', 'large'];
        widget.classList.remove('widget-small', 'widget-medium', 'widget-large');
        const size = sizes.includes(widgetData.size) ? widgetData.size : 'medium';
        widget.classList.add(`widget-${size}`);
        widget.dataset.size = size;

        const width = parseInt(widgetData.style?.width ?? '', 10);
        widget.style.width = !Number.isNaN(width) && width >= 280 && width <= 800 ? widgetData.style.width : '';

        const height = parseInt(widgetData.style?.height ?? '', 10);
        widget.style.height = !Number.isNaN(height) && height >= 180 && height <= 600 ? widgetData.style.height : '';

        const canResize = widgetData.canResize !== false;
        widget.dataset.canResize = canResize ? 'true' : 'false';

        const columnSpan = parseInt(widgetData.grid?.columnSpan ?? '', 10);
        if (Number.isInteger(columnSpan) && columnSpan > 0) {
            widget.dataset.gridColumnSpan = String(columnSpan);
        }

        const rowSpan = parseInt(widgetData.grid?.rowSpan ?? '', 10);
        if (Number.isInteger(rowSpan) && rowSpan > 0) {
            widget.dataset.gridRowSpan = String(rowSpan);
        }

        this.updateDatasetSizing(widget);
    }

    initEventListeners() {
        // Toolbar buttons
        document.getElementById('add-widget-btn')?.addEventListener('click', () => this.openWidgetModal());
        document.getElementById('layout-reset-btn')?.addEventListener('click', () => this.resetLayout());
        document.getElementById('dashboard-settings-btn')?.addEventListener('click', () => this.openSettings());

        // Modal events
        document.getElementById('close-widget-modal')?.addEventListener('click', () => this.closeWidgetModal());
        document.getElementById('cancel-widget-add')?.addEventListener('click', () => this.closeWidgetModal());
        document.getElementById('confirm-widget-add')?.addEventListener('click', () => this.addSelectedWidget());

        // Widget option selection
        document.querySelectorAll('.widget-option').forEach(option => {
            option.addEventListener('click', (e) => this.selectWidgetType(e));
        });

        // Delegate widget control actions as fallback for pre-rendered widgets
        this.widgetsContainer?.addEventListener('click', (event) => {
            const actionButton = event.target.closest('[data-action]');
            if (!actionButton || !this.widgetsContainer.contains(actionButton)) {
                return;
            }

            const widget = actionButton.closest('.widget');
            if (!widget) {
                return;
            }

            if (widget.dataset.controlsBound === 'true') {
                return;
            }

            const action = actionButton.dataset.action;
            if (!action) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            if (action === 'resize') {
                if (widget.dataset.canResize === 'false') {
                    return;
                }
                this.toggleWidgetSize(widget);
            } else if (action === 'remove') {
                this.removeWidget(widget);
            }
        });

        // Global drag and drop events
        document.addEventListener('dragstart', (e) => this.handleDragStart(e));
        document.addEventListener('dragover', (e) => this.handleDragOver(e));
        document.addEventListener('drop', (e) => this.handleDrop(e));
        document.addEventListener('dragend', (e) => this.handleDragEnd(e));

        // Global resize events
        document.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        document.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        document.addEventListener('mouseup', (e) => this.handleMouseUp(e));

        // Close modal on outside click
        this.widgetModal?.addEventListener('click', (e) => {
            if (e.target === this.widgetModal) {
                this.closeWidgetModal();
            }
        });
    }

    openWidgetModal() {
        this.widgetModal.style.display = 'flex';
        this.selectedWidgetType = null;
        this.updateAddButton();
        // Clear previous selections
        document.querySelectorAll('.widget-option').forEach(option => {
            option.classList.remove('selected');
        });
    }

    closeWidgetModal() {
        this.widgetModal.style.display = 'none';
    }

    selectWidgetType(e) {
        document.querySelectorAll('.widget-option').forEach(option => {
            option.classList.remove('selected');
        });
        
        e.currentTarget.classList.add('selected');
        this.selectedWidgetType = e.currentTarget.dataset.widgetType;
        this.updateAddButton();
    }

    updateAddButton() {
        const addButton = document.getElementById('confirm-widget-add');
        addButton.disabled = !this.selectedWidgetType;
    }

    addSelectedWidget() {
        if (!this.selectedWidgetType) return;

        const widgetId = `widget-${Date.now()}`;
        const template = this.widgetTemplates[this.selectedWidgetType];
        
        const widgetHtml = this.generateWidgetHtml(widgetId, this.selectedWidgetType, template);
        
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = widgetHtml;
        const newWidget = tempDiv.firstElementChild;
        
        this.widgetsContainer.appendChild(newWidget);
        this.initWidget(newWidget);
        this.updateDatasetSizing(newWidget);
        
        // Re-initialize any charts if needed
        if (template.chartId) {
            this.initWidgetChart(newWidget, template.chartId);
        }
        
        this.saveLayoutToStorage();
        this.closeWidgetModal();

        // Re-initialize Lucide icons for the new widget
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    generateWidgetHtml(widgetId, widgetType, template) {
        const metricsHtml = template.metrics.map(metricId => `
            <div class="metric">
                <div class="metric-label">${this.getMetricLabel(metricId)}</div>
                <div class="metric-value" data-metric="${metricId}">--</div>
            </div>
        `).join('');

        const chartHtml = template.chartId ? `
            <div class="chart-container">
                <canvas id="${template.chartId}"></canvas>
            </div>
        ` : '';

        return `
            <div class="widget widget-base widget-medium" data-widget-id="${widgetId}" data-widget-type="${widgetType}" data-can-resize="true" data-grid-column-span="1" data-grid-row-span="1" draggable="true">
                <div class="widget-header">
                    <h3><i data-lucide="${template.icon}"></i> ${template.title}</h3>
                    <div class="widget-controls">
                        <button class="widget-btn" data-action="resize" title="Redimensionar">
                            <i data-lucide="maximize-2"></i>
                        </button>
                        <button class="widget-btn" data-action="remove" title="Eliminar">
                            <i data-lucide="x"></i>
                        </button>
                    </div>
                </div>
                <div class="widget-content">
                    <div class="metric-grid">
                        ${metricsHtml}
                    </div>
                    ${chartHtml}
                </div>
                <div class="resize-handles">
                    <div class="resize-handle resize-se"></div>
                </div>
            </div>
        `;
    }

    getMetricLabel(metricId) {
        const labels = {
            'cpu-usage': 'Uso Total',
            'cpu-freq': 'Frecuencia',
            'cpu-cores': 'Núcleos Lógicos',
            'cpu-physical': 'Núcleos Físicos',
            'mem-usage': 'RAM usada',
            'mem-total': 'RAM total',
            'swap-usage': 'Swap usada',
            'swap-total': 'Swap total',
            'disk-read': 'Lectura',
            'disk-write': 'Escritura',
            'disk-count': 'Dispositivos',
            'io-total': 'E/S total',
            'net-sent': 'Subida',
            'net-recv': 'Bajada',
            'net-interfaces': 'Interfaces',
            'gpu-count': 'GPUs',
            'gpu-usage': 'Uso GPU',
            'gpu-memory': 'Memoria',
            'gpu-temp': 'Temperatura',
            'gpu-clock': 'Reloj gráfico'
        };
        return labels[metricId] || metricId;
    }

    initWidget(widget) {
        if (!widget || widget.dataset.controlsBound === 'true') {
            return;
        }

        this.ensureWidgetStructure(widget);

        const canResize = widget.dataset.canResize !== 'false';

        // Add remove functionality
        const removeBtn = widget.querySelector('[data-action="remove"]');
        removeBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removeWidget(widget);
        });

        // Add resize functionality
        const resizeBtn = widget.querySelector('[data-action="resize"]');
        if (resizeBtn) {
            if (canResize) {
                resizeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleWidgetSize(widget);
                });
            } else {
                resizeBtn.setAttribute('aria-disabled', 'true');
                resizeBtn.classList.add('disabled');
            }
        }

        widget.dataset.controlsBound = 'true';
        this.updateDatasetSizing(widget);
    }

    removeWidget(widget) {
        if (confirm('¿Estás seguro de que quieres eliminar este widget?')) {
            widget.remove();
            this.saveLayoutToStorage();
        }
    }

    toggleWidgetSize(widget) {
        try {
            const currentSize = widget.classList.contains('widget-large') ? 'large' : 
                              widget.classList.contains('widget-small') ? 'small' : 'medium';
            const previousSize = widget.dataset.size || currentSize;
            
            widget.classList.remove('widget-small', 'widget-medium', 'widget-large');
            
            switch (currentSize) {
                case 'small':
                    widget.classList.add('widget-medium');
                    break;
                case 'medium':
                    widget.classList.add('widget-large');
                    break;
                case 'large':
                    widget.classList.add('widget-small');
                    break;
            }
            
            // Clear any custom size styles when toggling predefined sizes
            widget.style.width = '';
            widget.style.height = '';

        this.updateDatasetSizing(widget, { previousSize });
            
            // Resize charts after size change
            setTimeout(() => {
                this.resizeWidgetCharts(widget);
            }, 100);
            
            this.saveLayoutToStorage();
            console.log('Widget size toggled to:', widget.classList.contains('widget-large') ? 'large' : 
                       widget.classList.contains('widget-small') ? 'small' : 'medium');
        } catch (error) {
            console.error('Error toggling widget size:', error);
        }
    }

    updateDatasetSizing(widget, options = {}) {
        try {
            if (!widget) return;

            const config = typeof options === 'boolean' ? { manual: options } : (options || {});
            const {
                manual = false,
                previousSize = null,
                dimensions = null,
                columnThreshold = 520,
                rowThreshold = 360
            } = config;

            widget.classList.add('widget-base');

            const canResize = widget.dataset.canResize !== 'false';
            let size = widget.classList.contains('widget-large') ? 'large' :
                widget.classList.contains('widget-small') ? 'small' : 'medium';

            const sizeDefaults = {
                small: { columns: 1, rows: 1 },
                medium: { columns: 1, rows: 1 },
                large: { columns: 2, rows: 2 }
            };
            let defaults = sizeDefaults[size] || sizeDefaults.medium;
            const sizeChanged = Boolean(previousSize && previousSize !== size);

            let columnSpan = parseInt(widget.dataset.gridColumnSpan || '', 10);
            let rowSpan = parseInt(widget.dataset.gridRowSpan || '', 10);

            if (manual && canResize) {
                const measuredWidth = dimensions?.width ?? widget.getBoundingClientRect().width;
                const measuredHeight = dimensions?.height ?? widget.getBoundingClientRect().height;

                columnSpan = measuredWidth >= columnThreshold ? 2 : 1;
                rowSpan = measuredHeight >= rowThreshold ? 2 : 1;

                size = columnSpan > 1 || rowSpan > 1 ? 'large' : (size === 'small' ? 'small' : 'medium');
                widget.classList.remove('widget-small', 'widget-medium', 'widget-large');
                widget.classList.add(`widget-${size}`);
                defaults = sizeDefaults[size] || sizeDefaults.medium;
            } else {
                if (!Number.isInteger(columnSpan) || columnSpan < 1 || sizeChanged) {
                    columnSpan = defaults.columns;
                }

                if (!Number.isInteger(rowSpan) || rowSpan < 1 || sizeChanged) {
                    rowSpan = defaults.rows;
                }
            }

            if (!canResize) {
                columnSpan = 1;
                rowSpan = 1;
            }

            widget.dataset.size = size;

            widget.dataset.gridColumnSpan = String(columnSpan);
            widget.dataset.gridRowSpan = String(rowSpan);

            widget.style.gridColumn = '';
            widget.style.gridRow = '';
            widget.style.gridColumnStart = 'auto';
            widget.style.gridColumnEnd = `span ${columnSpan}`;
            widget.style.gridRowStart = 'auto';
            widget.style.gridRowEnd = `span ${rowSpan}`;
        } catch (error) {
            console.error('Error updating dataset sizing:', error);
        }
    }

    // Drag and Drop functionality
    handleDragStart(e) {
        try {
            const widget = e.target.closest('.widget');
            if (!widget || widget.classList.contains('dragging')) {
                return;
            }

            if (e.target.closest('.widget-controls')) {
                return;
            }

            this.draggedWidget = widget;
            widget.classList.add('dragging');

            if (e.dataTransfer) {
                e.dataTransfer.effectAllowed = 'move';
                try {
                    e.dataTransfer.setData('text/plain', widget.dataset.widgetId || '');
                } catch (setDataError) {
                    e.dataTransfer.setData('text/plain', '');
                }

                if (typeof e.dataTransfer.setDragImage === 'function') {
                    const rect = widget.getBoundingClientRect();
                    e.dataTransfer.setDragImage(widget, rect.width / 2, rect.height / 2);
                }
            }

            this.placeholder.style.height = `${widget.offsetHeight}px`;
            this.placeholder.style.width = `${widget.offsetWidth}px`;

            ['widget-small', 'widget-medium', 'widget-large'].forEach((sizeClass) => {
                if (widget.classList.contains(sizeClass)) {
                    this.placeholder.classList.add(sizeClass);
                } else {
                    this.placeholder.classList.remove(sizeClass);
                }
            });

            if (!this.placeholder.parentElement) {
                widget.after(this.placeholder);
            }

            console.log('Drag started for widget:', widget.dataset.widgetType);
        } catch (error) {
            console.error('Error in handleDragStart:', error);
        }
    }

    handleDragOver(e) {
        try {
            if (!this.draggedWidget || !this.widgetsContainer) {
                return;
            }

            e.preventDefault();
            if (e.dataTransfer) {
                e.dataTransfer.dropEffect = 'move';
            }

            const afterElement = this.getDragAfterElement(e.clientY);
            if (!afterElement) {
                this.widgetsContainer.appendChild(this.placeholder);
            } else if (afterElement !== this.placeholder) {
                this.widgetsContainer.insertBefore(this.placeholder, afterElement);
            }
        } catch (error) {
            console.error('Error in handleDragOver:', error);
        }
    }

    handleDrop(e) {
        try {
            e.preventDefault();

            if (!this.draggedWidget || !this.widgetsContainer) {
                this.cleanupDrag();
                return;
            }

            if (this.placeholder.parentElement === this.widgetsContainer) {
                this.widgetsContainer.insertBefore(this.draggedWidget, this.placeholder);
            } else {
                this.widgetsContainer.appendChild(this.draggedWidget);
            }

            console.log('Widget reordered successfully');
            this.saveLayoutToStorage();
            this.cleanupDrag();
        } catch (error) {
            console.error('Error in handleDrop:', error);
            this.cleanupDrag();
        }
    }

    handleDragEnd() {
        if (this.draggedWidget) {
            console.log('Drag operation ended');
        }
        this.cleanupDrag();
    }

    getDragAfterElement(clientY) {
        if (!this.widgetsContainer) {
            return null;
        }

        const draggableElements = Array.from(
            this.widgetsContainer.querySelectorAll('.widget:not(.dragging)')
        );

        let closest = { offset: Number.NEGATIVE_INFINITY, element: null };

        draggableElements.forEach((child) => {
            const box = child.getBoundingClientRect();
            const offset = clientY - (box.top + box.height / 2);

            if (offset < 0 && offset > closest.offset) {
                closest = { offset, element: child };
            }
        });

        return closest.element;
    }

    cleanupDrag() {
        if (this.draggedWidget) {
            this.draggedWidget.classList.remove('dragging');
        }

        if (this.placeholder && this.placeholder.parentElement) {
            this.placeholder.parentElement.removeChild(this.placeholder);
        }

        this.placeholder.style.width = '';
        this.placeholder.style.height = '';
        this.placeholder.classList.remove('widget-small', 'widget-medium', 'widget-large');

        this.draggedWidget = null;
    }

    // Resize functionality
    handleMouseDown(e) {
        try {
            if (e.target.classList.contains('resize-handle')) {
                this.isResizing = true;
                this.currentResizeWidget = e.target.closest('.widget');
                
                if (!this.currentResizeWidget) {
                    this.isResizing = false;
                    return;
                }

                if (this.currentResizeWidget.dataset.canResize === 'false') {
                    this.isResizing = false;
                    this.currentResizeWidget = null;
                    return;
                }
                
                this.currentResizeWidget.classList.add('resizing');
                
                // Store initial position and size
                const rect = this.currentResizeWidget.getBoundingClientRect();
                this.resizeStartX = e.clientX;
                this.resizeStartY = e.clientY;
                this.resizeStartWidth = rect.width;
                this.resizeStartHeight = rect.height;
                
                e.preventDefault();
                e.stopPropagation();
                
                console.log('Resize started for widget:', this.currentResizeWidget.dataset.widgetType);
            }
        } catch (error) {
            console.error('Error in handleMouseDown:', error);
            this.isResizing = false;
        }
    }

    handleMouseMove(e) {
        try {
            if (!this.isResizing || !this.currentResizeWidget) return;
            
            const minWidth = 280;
            const minHeight = 180;
            const maxWidth = 800;
            const maxHeight = 600;
            
            // Calculate new dimensions based on mouse movement
            const deltaX = e.clientX - this.resizeStartX;
            const deltaY = e.clientY - this.resizeStartY;
            
            const newWidth = Math.max(minWidth, Math.min(maxWidth, this.resizeStartWidth + deltaX));
            const newHeight = Math.max(minHeight, Math.min(maxHeight, this.resizeStartHeight + deltaY));
            this.lastResizeDimensions = { width: newWidth, height: newHeight };
            
            // Apply new size
            this.currentResizeWidget.style.width = `${newWidth}px`;
            this.currentResizeWidget.style.height = `${newHeight}px`;
            this.updateDatasetSizing(this.currentResizeWidget, { manual: true, dimensions: this.lastResizeDimensions });
            
            // Force chart resize if the widget contains one
            this.resizeWidgetCharts(this.currentResizeWidget);
            
        } catch (error) {
            console.error('Error in handleMouseMove:', error);
        }
    }

    handleMouseUp(e) {
        try {
            if (this.isResizing) {
                this.isResizing = false;
                
                if (this.currentResizeWidget) {
                    this.currentResizeWidget.classList.remove('resizing');
                    
                    const finalDimensions = this.lastResizeDimensions || {
                        width: this.currentResizeWidget.getBoundingClientRect().width,
                        height: this.currentResizeWidget.getBoundingClientRect().height
                    };

                    this.updateDatasetSizing(this.currentResizeWidget, {
                        manual: true,
                        dimensions: finalDimensions
                    });

                    this.currentResizeWidget.style.width = '';
                    this.currentResizeWidget.style.height = '';

                    // Final chart resize
                    this.resizeWidgetCharts(this.currentResizeWidget);
                    
                    this.saveLayoutToStorage();
                    console.log('Resize completed for widget:', this.currentResizeWidget.dataset.widgetType);
                    this.currentResizeWidget = null;
                }
                
                // Clean up resize variables
                this.resizeStartX = null;
                this.resizeStartY = null;
                this.resizeStartWidth = null;
                this.resizeStartHeight = null;
                this.lastResizeDimensions = null;
            }
        } catch (error) {
            console.error('Error in handleMouseUp:', error);
        }
    }

    resizeWidgetCharts(widget) {
        try {
            // Find canvas elements in the widget and trigger resize
            const canvases = widget.querySelectorAll('canvas');
            canvases.forEach(canvas => {
                const chartId = canvas.id;
                
                // If it's a Chart.js chart, trigger resize
                if (window.Chart && Chart.getChart && Chart.getChart(canvas)) {
                    const chart = Chart.getChart(canvas);
                    setTimeout(() => {
                        chart.resize();
                    }, 10);
                }
            });
        } catch (error) {
            console.error('Error resizing widget charts:', error);
        }
    }

    // Layout persistence
    saveLayoutToStorage() {
        try {
            if (!this.widgetsContainer) return;
            
            const widgets = Array.from(this.widgetsContainer.querySelectorAll('.widget')).map((widget, index) => {
                this.updateDatasetSizing(widget);
                const columnSpan = parseInt(widget.dataset.gridColumnSpan ?? '', 10);
                const rowSpan = parseInt(widget.dataset.gridRowSpan ?? '', 10);

                return {
                    id: widget.dataset.widgetId,
                    type: widget.dataset.widgetType,
                    size: widget.classList.contains('widget-large') ? 'large' : 
                          widget.classList.contains('widget-small') ? 'small' : 'medium',
                    canResize: widget.dataset.canResize !== 'false',
                    style: {
                        width: widget.style.width || '',
                        height: widget.style.height || ''
                    },
                    grid: {
                        columnSpan: Number.isInteger(columnSpan) && columnSpan > 0 ? columnSpan : null,
                        rowSpan: Number.isInteger(rowSpan) && rowSpan > 0 ? rowSpan : null
                    },
                    order: index // Save order for proper reordering
                };
            });
            
            localStorage.setItem(DASHBOARD_LAYOUT_KEY, JSON.stringify(widgets));
            LEGACY_LAYOUT_KEYS.forEach((legacyKey) => {
                if (legacyKey !== DASHBOARD_LAYOUT_KEY) {
                    localStorage.removeItem(legacyKey);
                }
            });
            console.log('Layout saved to storage:', widgets.length, 'widgets');
        } catch (error) {
            console.error('Error saving layout to storage:', error);
        }
    }

    loadLayoutFromStorage() {
        let saved = localStorage.getItem(DASHBOARD_LAYOUT_KEY);
        if (!saved) {
            for (const legacyKey of LEGACY_LAYOUT_KEYS) {
                const legacyValue = localStorage.getItem(legacyKey);
                if (legacyValue) {
                    saved = legacyValue;
                    localStorage.setItem(DASHBOARD_LAYOUT_KEY, legacyValue);
                    localStorage.removeItem(legacyKey);
                    break;
                }
            }
        }

        if (!saved) return;
        
        try {
            const layout = JSON.parse(saved);
            
            // Sort by order to maintain proper widget sequence
            layout.sort((a, b) => (a.order || 0) - (b.order || 0));
            
            // Only add widgets that don't already exist
            layout.forEach(widgetData => {
                if (!widgetData.id || !widgetData.type) return;

                const existing = this.widgetsContainer.querySelector(`[data-widget-id="${widgetData.id}"]`);
                if (existing) {
                    this.ensureWidgetStructure(existing);
                    this.applyWidgetLayoutState(existing, widgetData);
                    this.initWidget(existing);
                    return;
                }

                const template = this.widgetTemplates[widgetData.type];
                if (!template) {
                    console.warn('Unknown widget type:', widgetData.type);
                    return;
                }

                const widgetHtml = this.generateWidgetHtml(widgetData.id, widgetData.type, template);
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = widgetHtml;
                const newWidget = tempDiv.firstElementChild;

                if (!newWidget) return;

                this.ensureWidgetStructure(newWidget);
                this.applyWidgetLayoutState(newWidget, widgetData);
                this.widgetsContainer.appendChild(newWidget);
                this.initWidget(newWidget);
            });
            
            // Re-initialize Lucide icons
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
            
            console.log('Layout loaded from storage:', layout.length, 'widgets');
        } catch (e) {
            console.warn('Failed to load dashboard layout:', e);
            // Clear corrupted layout
            localStorage.removeItem(DASHBOARD_LAYOUT_KEY);
            LEGACY_LAYOUT_KEYS.forEach((legacyKey) => localStorage.removeItem(legacyKey));
        }
    }

    resetLayout() {
        if (confirm('¿Estás seguro de que quieres resetear el layout del dashboard?')) {
            localStorage.removeItem(DASHBOARD_LAYOUT_KEY);
            LEGACY_LAYOUT_KEYS.forEach((legacyKey) => localStorage.removeItem(legacyKey));
            location.reload();
        }
    }

    openSettings() {
        alert('Configuración del dashboard - Próximamente');
    }

    initWidgetChart(widget, chartId) {
        // This would integrate with the existing chart initialization
        // For now, just ensure the chart gets created if it exists in the global charts object
        const canvas = widget.querySelector(`#${chartId}`);
        if (canvas && typeof Chart !== 'undefined') {
            // Chart initialization would happen here
            // This integrates with existing chart logic
            console.log(`Initializing chart ${chartId} for widget`);
        }
    }
}

// Initialize dashboard when DOM is ready
let interactiveDashboard;

let updateInterval;

function bootstrap() {
    try {
        console.log('🚀 Initializing Mission Center Dashboard...');
        
        // Initialize navigation first
        initNavigation();
        console.log('✅ Navigation initialized');
        
        // Initialize charts
        initCharts();
        console.log('✅ Charts initialized');
        
        // Initialize interactive dashboard
        interactiveDashboard = new InteractiveDashboard();
        if (typeof window !== 'undefined') {
            window.interactiveDashboard = interactiveDashboard;
        }
        console.log('✅ Interactive dashboard initialized');
        
        // Show initial section
        showSection(currentSection);
        console.log('✅ Initial section shown');
        
        // Start update loop with initial delay
        setTimeout(() => {
            updateLoop();
            // Set up regular updates, clear any existing interval first
            if (updateInterval) clearInterval(updateInterval);
            updateInterval = setInterval(updateLoop, 1000);
        }, 100);
        
        console.log('✅ Update loop started');
        
    } catch (error) {
        console.error('❌ Fatal error during bootstrap:', error);
        setConnectionState(false, 'Error de inicialización - Refresca la página');
    }
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});

document.addEventListener("DOMContentLoaded", bootstrap);
