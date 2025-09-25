

const charts = {};
const miniCharts = new Map();
const coresHistory = new Map();
let currentSection = "overview";
const CORE_HISTORY_LENGTH = 60;

const NAV_ITEMS = Array.from(document.querySelectorAll(".nav-item"));

const STATUS_ELEMENTS = {
    pill: () => document.getElementById("status-pill"),
    text: () => document.getElementById("status-text"),
    indicator: () => document.getElementById("status-indicator"),
    lastUpdate: () => document.getElementById("last-update"),
    uptime: () => document.getElementById("uptime-value"),
    host: () => document.getElementById("host-name"),
    os: () => document.getElementById("os-name"),
    permissions: () => document.getElementById("permissions-indicator"),
};

function formatBytes(value) {
    if (!value && value !== 0) return "--";
    const units = ["B", "KB", "MB", "GB", "TB", "PB"];
    let size = Math.abs(value);
    let unit = 0;
    while (size >= 1024 && unit < units.length - 1) {
        size /= 1024;
        unit += 1;
    }
    const sign = value < 0 ? "-" : "";
    return `${sign}${size.toFixed(size >= 100 ? 0 : 1)} ${units[unit]}`;
}

function formatNumber(value) {
    if (value === null || value === undefined) return "--";
    return Number(value).toLocaleString();
}

function formatFrequency(value) {
    if (!value && value !== 0) return "--";
    return `${value.toFixed(0)} MHz`;
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
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
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
    return new Chart(canvas.getContext("2d"), Chart.helpers.merge(baseConfig, options));
}

function setConnectionState(isConnected) {
    const pill = STATUS_ELEMENTS.pill();
    const text = STATUS_ELEMENTS.text();
    if (!pill || !text) return;
    pill.classList.remove("online", "offline");
    pill.classList.add(isConnected ? "online" : "offline");
    pill.setAttribute("aria-label", isConnected ? "Conexión establecida" : "Conexión caída");
    text.textContent = isConnected ? "Conectado ✅" : "Error de conexión ❌";
}

function updateStatusMeta(current) {
    const lastUpdate = STATUS_ELEMENTS.lastUpdate();
    if (lastUpdate) {
        lastUpdate.textContent = new Date().toLocaleTimeString();
    }

    const system = current?.system || {};

    const uptime = STATUS_ELEMENTS.uptime();
    if (uptime) {
        uptime.textContent = system.uptime_seconds != null ? formatDuration(system.uptime_seconds) : "--";
    }

    const host = STATUS_ELEMENTS.host();
    if (host) {
        host.textContent = system.hostname || "--";
    }

    const os = STATUS_ELEMENTS.os();
    if (os) {
        const summaryParts = [];
        const osLabel = [system.os_name, system.os_version].filter(Boolean).join(" ");
        if (osLabel) summaryParts.push(osLabel);
        if (system.architecture) summaryParts.push(system.architecture);
        const summary = summaryParts.join(" · ");
        const virt = system.virtualization ? ` (${system.virtualization})` : "";
        os.textContent = summary ? `${summary}${virt}` : "--";
    }
    
    updatePermissionsIndicator(current?.permissions);
}

function updatePermissionsIndicator(permissions) {
    const indicator = STATUS_ELEMENTS.permissions();
    if (!indicator || !permissions) return;
    
    const level = permissions.permission_level || "limited";
    const accessPercentage = permissions.access_percentage || 0;
    

    indicator.classList.remove("perm-full", "perm-good", "perm-partial", "perm-limited");
    

    indicator.classList.add(`perm-${level}`);
    

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
    
    indicator.textContent = `${icon} ${label} (${accessPercentage}%)`;
    indicator.title = permissions.warnings?.length > 0 
        ? `Permisos: ${label}\n\nAdvertencias:\n${permissions.warnings.join('\n')}`
        : `Permisos: ${label} - ${accessPercentage}% de rutas del sistema accesibles`;
}

function initCharts() {
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
}

function updateOverview(data) {
    const { cpu, memory, disk, io, network, gpu } = data;
    if (cpu) {
        document.getElementById("cpu-usage").textContent = `${cpu.usage_percent?.toFixed(1) ?? "--"}%`;
        document.getElementById("cpu-freq").textContent = formatFrequency(cpu.frequency_current_mhz);
        document.getElementById("cpu-cores").textContent = formatNumber(cpu.logical_cores);
        document.getElementById("cpu-physical").textContent = formatNumber(cpu.physical_cores);
    }
    if (memory) {
        document.getElementById("mem-usage").textContent = `${memory.percent?.toFixed(1) ?? "--"}%`;
        document.getElementById("mem-total").textContent = formatBytes(memory.total_bytes);
        document.getElementById("swap-usage").textContent = `${memory.swap_percent?.toFixed(1) ?? "--"}%`;
        document.getElementById("swap-total").textContent = formatBytes(memory.swap_total_bytes);
    }
    if (disk && io) {
        const totalRead = disk.devices?.reduce((sum, dev) => sum + (dev.read_bytes_per_sec || 0), 0) || 0;
        const totalWrite = disk.devices?.reduce((sum, dev) => sum + (dev.write_bytes_per_sec || 0), 0) || 0;
        document.getElementById("disk-read").textContent = `${formatBytes(totalRead)}/s`;
        document.getElementById("disk-write").textContent = `${formatBytes(totalWrite)}/s`;
        document.getElementById("disk-count").textContent = formatNumber(disk.devices?.length ?? 0);
        document.getElementById("io-total").textContent = `${formatBytes(io.read_bytes_per_sec + io.write_bytes_per_sec)} /s`;
    }
    if (network) {
        const totalSent = network.interfaces?.reduce((sum, iface) => sum + (iface.sent_bytes_per_sec || 0), 0) || 0;
        const totalRecv = network.interfaces?.reduce((sum, iface) => sum + (iface.recv_bytes_per_sec || 0), 0) || 0;
        document.getElementById("net-sent").textContent = `${formatBytes(totalSent)}/s`;
        document.getElementById("net-recv").textContent = `${formatBytes(totalRecv)}/s`;
        document.getElementById("net-interfaces").textContent = formatNumber(
            network.interfaces?.filter((iface) => iface.is_up).length ?? 0,
        );
    }
    document.getElementById("gpu-count").textContent = formatNumber(gpu?.length ?? 0);
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

function formatDuration(seconds) {
    if (seconds === null || seconds === undefined || Number.isNaN(seconds)) {
        return "--";
    }
    const total = Math.max(0, Math.floor(Number(seconds)));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const secs = total % 60;
    return `${hours.toString().padStart(2, "0")}h ${minutes.toString().padStart(2, "0")}m ${secs
        .toString()
        .padStart(2, "0")}s`;
}

async function fetchJSON(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
}

async function updateLoop() {
    try {
        const [current, history] = await Promise.all([
            fetchJSON("/api/current"),
            fetchJSON("/api/history"),
        ]);
        setConnectionState(true);
        updateStatusMeta(current);

        updateOverview(current);
        updatePerformance(current);
        updateProcesses(current);
        updateSensorTables(current);
        updateSystemInfo(current);
        updateHistoryCharts(history);
        updateGPUGrid(current.gpu);
        updateIODevicesGrid(current.io);
    } catch (error) {
        setConnectionState(false);
        console.error("Fetch error", error);
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
class InteractiveDashboard {
    constructor() {
        this.widgetsContainer = document.getElementById('widgets-container');
        this.dropIndicator = document.getElementById('drop-indicator');
        this.widgetModal = document.getElementById('widget-selector-modal');
        this.selectedWidgetType = null;
        this.draggedWidget = null;
        this.isResizing = false;
        this.currentResizeWidget = null;

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
                metrics: ['gpu-usage', 'gpu-memory', 'gpu-temp', 'gpu-power'],
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

        this.initEventListeners();
        this.loadLayoutFromStorage();
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
        const metricsHtml = template.metrics.map(metricId => {
            const [category, metric] = metricId.split('-');
            return `
                <div class="metric">
                    <div class="metric-label">${this.getMetricLabel(metricId)}</div>
                    <div class="metric-value" id="${metricId}">--</div>
                </div>
            `;
        }).join('');

        const chartHtml = template.chartId ? `
            <div class="chart-container">
                <canvas id="${template.chartId}"></canvas>
            </div>
        ` : '';

        return `
            <div class="widget widget-medium" data-widget-id="${widgetId}" data-widget-type="${widgetType}" draggable="true">
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
            'gpu-count': 'GPUs'
        };
        return labels[metricId] || metricId;
    }

    initWidget(widget) {
        // Add remove functionality
        const removeBtn = widget.querySelector('[data-action="remove"]');
        removeBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removeWidget(widget);
        });

        // Add resize functionality
        const resizeBtn = widget.querySelector('[data-action="resize"]');
        resizeBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleWidgetSize(widget);
        });
    }

    removeWidget(widget) {
        if (confirm('¿Estás seguro de que quieres eliminar este widget?')) {
            widget.remove();
            this.saveLayoutToStorage();
        }
    }

    toggleWidgetSize(widget) {
        const currentSize = widget.classList.contains('widget-large') ? 'large' : 
                          widget.classList.contains('widget-small') ? 'small' : 'medium';
        
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
        
        this.saveLayoutToStorage();
    }

    // Drag and Drop functionality
    handleDragStart(e) {
        if (!e.target.classList.contains('widget')) return;
        
        this.draggedWidget = e.target;
        e.target.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
    }

    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        if (this.draggedWidget) {
            this.showDropIndicator(e);
        }
    }

    handleDrop(e) {
        e.preventDefault();
        this.hideDropIndicator();
        
        if (!this.draggedWidget) return;
        
        const targetWidget = e.target.closest('.widget');
        if (targetWidget && targetWidget !== this.draggedWidget) {
            // Insert before target widget
            this.widgetsContainer.insertBefore(this.draggedWidget, targetWidget);
            this.saveLayoutToStorage();
        }
    }

    handleDragEnd(e) {
        if (e.target.classList.contains('widget')) {
            e.target.classList.remove('dragging');
        }
        this.draggedWidget = null;
        this.hideDropIndicator();
    }

    showDropIndicator(e) {
        const rect = this.widgetsContainer.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.dropIndicator.style.display = 'flex';
        this.dropIndicator.style.left = `${Math.max(0, x - 150)}px`;
        this.dropIndicator.style.top = `${Math.max(0, y - 75)}px`;
        this.dropIndicator.style.width = '300px';
        this.dropIndicator.style.height = '150px';
    }

    hideDropIndicator() {
        this.dropIndicator.style.display = 'none';
    }

    // Resize functionality
    handleMouseDown(e) {
        if (e.target.classList.contains('resize-handle')) {
            this.isResizing = true;
            this.currentResizeWidget = e.target.closest('.widget');
            this.currentResizeWidget.classList.add('resizing');
            e.preventDefault();
        }
    }

    handleMouseMove(e) {
        if (!this.isResizing || !this.currentResizeWidget) return;
        
        // Simple resize implementation - could be enhanced
        const rect = this.currentResizeWidget.getBoundingClientRect();
        const minWidth = 300;
        const minHeight = 200;
        
        const newWidth = Math.max(minWidth, e.clientX - rect.left);
        const newHeight = Math.max(minHeight, e.clientY - rect.top);
        
        this.currentResizeWidget.style.width = `${newWidth}px`;
        this.currentResizeWidget.style.height = `${newHeight}px`;
    }

    handleMouseUp(e) {
        if (this.isResizing) {
            this.isResizing = false;
            if (this.currentResizeWidget) {
                this.currentResizeWidget.classList.remove('resizing');
                this.saveLayoutToStorage();
                this.currentResizeWidget = null;
            }
        }
    }

    // Layout persistence
    saveLayoutToStorage() {
        const widgets = Array.from(this.widgetsContainer.querySelectorAll('.widget')).map(widget => ({
            id: widget.dataset.widgetId,
            type: widget.dataset.widgetType,
            size: widget.classList.contains('widget-large') ? 'large' : 
                  widget.classList.contains('widget-small') ? 'small' : 'medium',
            style: {
                width: widget.style.width || '',
                height: widget.style.height || ''
            }
        }));
        
        localStorage.setItem('dashboard-layout', JSON.stringify(widgets));
    }

    loadLayoutFromStorage() {
        const saved = localStorage.getItem('dashboard-layout');
        if (!saved) return;
        
        try {
            const layout = JSON.parse(saved);
            
            // Only add widgets that don't already exist
            layout.forEach(widgetData => {
                const existing = document.querySelector(`[data-widget-id="${widgetData.id}"]`);
                if (existing) return;
                
                const template = this.widgetTemplates[widgetData.type];
                if (!template) return;
                
                const widgetHtml = this.generateWidgetHtml(widgetData.id, widgetData.type, template);
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = widgetHtml;
                const newWidget = tempDiv.firstElementChild;
                
                // Apply saved size and style
                newWidget.classList.remove('widget-small', 'widget-medium', 'widget-large');
                newWidget.classList.add(`widget-${widgetData.size}`);
                
                if (widgetData.style.width) newWidget.style.width = widgetData.style.width;
                if (widgetData.style.height) newWidget.style.height = widgetData.style.height;
                
                this.widgetsContainer.appendChild(newWidget);
                this.initWidget(newWidget);
            });
            
            // Re-initialize Lucide icons
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        } catch (e) {
            console.warn('Failed to load dashboard layout:', e);
        }
    }

    resetLayout() {
        if (confirm('¿Estás seguro de que quieres resetear el layout del dashboard?')) {
            localStorage.removeItem('dashboard-layout');
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

function bootstrap() {
    initNavigation();
    initCharts();
    
    // Initialize interactive dashboard
    interactiveDashboard = new InteractiveDashboard();
    
    showSection(currentSection);
    updateLoop();
    setInterval(updateLoop, 1000);
}

document.addEventListener("DOMContentLoaded", bootstrap);
