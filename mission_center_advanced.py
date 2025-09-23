#!/usr/bin/env python3
"""
Mission Center Clone - Versión web avanzada estilo Windows
Monitor completo del sistema con gráficos en tiempo real
"""

import sys
import os
import time
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
from collections import deque
from datetime import datetime

# Añadir el path del proyecto
sys.path.insert(0, os.path.dirname(__file__))

try:
    from mission_center_clone.data import (
        collect_cpu_snapshot,
        collect_memory_snapshot,
        collect_disk_snapshot,
        collect_network_snapshot,
        collect_process_snapshot,
        collect_gpu_snapshot,
        collect_io_snapshot,
        collect_pcie_snapshot
    )
    DATA_AVAILABLE = True
    print("✅ Todos los colectores de datos disponibles")
except ImportError as e:
    print(f"⚠️ Warning: {e}")
    DATA_AVAILABLE = False

class DataCollector:
    def __init__(self):
        self.history_size = 60  # 60 puntos de historia (1 minuto a 1Hz)
        self.cpu_history = deque(maxlen=self.history_size)
        self.memory_history = deque(maxlen=self.history_size)
        self.cpu_cores_history = {}
        self.network_history = deque(maxlen=self.history_size)
        self.disk_history = deque(maxlen=self.history_size)
        
        self.current_data = {}
        self.last_update = time.time()
        
        # Iniciar hilo de recolección
        self.running = True
        self.thread = threading.Thread(target=self.collect_loop, daemon=True)
        self.thread.start()
    
    def collect_loop(self):
        while self.running:
            try:
                self.collect_all_data()
                time.sleep(1)  # Actualizar cada segundo
            except Exception as e:
                print(f"Error en recolección: {e}")
                time.sleep(2)
    
    def collect_all_data(self):
        if not DATA_AVAILABLE:
            return
        
        timestamp = time.time()
        
        # CPU
        cpu_data = collect_cpu_snapshot()
        self.cpu_history.append({
            'time': timestamp,
            'usage': cpu_data.usage_percent,
            'frequency': cpu_data.frequency_current_mhz or 0
        })
        
        # CPU por núcleo
        for core in cpu_data.per_core:
            core_id = f"core_{core.core_id}"
            if core_id not in self.cpu_cores_history:
                self.cpu_cores_history[core_id] = deque(maxlen=self.history_size)
            self.cpu_cores_history[core_id].append({
                'time': timestamp,
                'usage': core.usage_percent,
                'frequency': core.frequency_mhz or 0
            })
        
        # Memoria
        mem_data = collect_memory_snapshot()
        self.memory_history.append({
            'time': timestamp,
            'usage': mem_data.percent,
            'used': mem_data.used_bytes,
            'available': mem_data.available_bytes,
            'swap_usage': mem_data.swap_percent,
            'swap_used': mem_data.swap_used_bytes
        })
        
        # Red
        net_data = collect_network_snapshot()
        total_sent = sum(i.sent_bytes_per_sec for i in net_data.interfaces)
        total_recv = sum(i.recv_bytes_per_sec for i in net_data.interfaces)
        self.network_history.append({
            'time': timestamp,
            'sent': total_sent,
            'recv': total_recv
        })
        
        # Disco
        disk_data = collect_disk_snapshot()
        total_read = sum(d.read_bytes_per_sec or 0 for d in disk_data.devices)
        total_write = sum(d.write_bytes_per_sec or 0 for d in disk_data.devices)
        self.disk_history.append({
            'time': timestamp,
            'read': total_read,
            'write': total_write
        })
        
        # Recopilar datos actuales completos
        try:
            processes = collect_process_snapshot()
            gpu_data = collect_gpu_snapshot()
            io_data = collect_io_snapshot()
            pcie_data = collect_pcie_snapshot()
        except:
            processes = None
            gpu_data = []
            io_data = None
            pcie_data = None
        
        self.current_data = {
            'timestamp': timestamp,
            'cpu': {
                'usage_percent': cpu_data.usage_percent,
                'frequency_current': cpu_data.frequency_current_mhz or 0,
                'frequency_max': cpu_data.frequency_max_mhz or 0,
                'logical_cores': cpu_data.logical_cores,
                'physical_cores': cpu_data.physical_cores or 0,
                'load_average': cpu_data.load_average,
                'context_switches': cpu_data.context_switches or 0,
                'interrupts': cpu_data.interrupts or 0,
                'cores': [
                    {
                        'id': core.core_id,
                        'usage': core.usage_percent,
                        'frequency': core.frequency_mhz or 0
                    }
                    for core in cpu_data.per_core
                ]
            },
            'memory': {
                'total_bytes': mem_data.total_bytes,
                'used_bytes': mem_data.used_bytes,
                'available_bytes': mem_data.available_bytes,
                'percent': mem_data.percent,
                'swap_total_bytes': mem_data.swap_total_bytes,
                'swap_used_bytes': mem_data.swap_used_bytes,
                'swap_percent': mem_data.swap_percent
            },
            'disk': {
                'devices': [
                    {
                        'name': d.name,
                        'mountpoint': d.mountpoint,
                        'total_bytes': d.total_bytes,
                        'used_bytes': d.used_bytes,
                        'free_bytes': d.free_bytes,
                        'read_rate': d.read_bytes_per_sec or 0,
                        'write_rate': d.write_bytes_per_sec or 0
                    }
                    for d in disk_data.devices
                ]
            },
            'network': {
                'interfaces': [
                    {
                        'name': i.name,
                        'is_up': i.is_up,
                        'sent_rate': i.sent_bytes_per_sec,
                        'recv_rate': i.recv_bytes_per_sec,
                        'address': i.address
                    }
                    for i in net_data.interfaces
                ]
            },
            'gpu': [
                {
                    'name': gpu.name,
                    'vendor': gpu.vendor,
                    'memory_total': gpu.memory_total_bytes,
                    'memory_used': gpu.memory_used_bytes,
                    'utilization': gpu.utilization_percent or 0,
                    'temperature': gpu.temperature_celsius or 0
                }
                for gpu in gpu_data
            ] if gpu_data else [],
            'processes': {
                'count': len(processes.processes) if processes else 0,
                'top_cpu': [
                    {
                        'pid': p.pid,
                        'name': p.name,
                        'cpu_percent': p.cpu_percent,
                        'memory_bytes': p.memory_bytes,
                        'username': p.username
                    }
                    for p in (processes.processes[:10] if processes else [])
                ]
            },
            'io': {
                'read_rate': io_data.read_bytes_per_sec if io_data else 0,
                'write_rate': io_data.write_bytes_per_sec if io_data else 0
            } if io_data else {'read_rate': 0, 'write_rate': 0},
            'pcie': {
                'device_count': len(pcie_data.devices) if pcie_data else 0,
                'active_links': len([d for d in (pcie_data.devices if pcie_data else []) if d.link_speed_gtps])
            }
        }
        
        self.last_update = timestamp

# Instancia global del colector
collector = DataCollector()

class MissionCenterHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_html()
        elif self.path == '/api/current':
            self.send_current_data()
        elif self.path == '/api/history':
            self.send_history_data()
        else:
            self.send_response(404)
            self.end_headers()
    
    def send_html(self):
        html = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mission Center - Monitor del Sistema</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
            overflow-x: hidden;
        }
        
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: 200px;
            height: 100vh;
            background: rgba(15, 23, 42, 0.95);
            border-right: 1px solid rgba(34, 211, 238, 0.3);
            padding: 20px 0;
            z-index: 1000;
        }
        
        .sidebar h2 {
            text-align: center;
            color: #22d3ee;
            margin-bottom: 30px;
            font-size: 1.2em;
        }
        
        .nav-item {
            padding: 12px 20px;
            margin: 5px 0;
            cursor: pointer;
            border-left: 3px solid transparent;
            transition: all 0.3s;
        }
        
        .nav-item:hover, .nav-item.active {
            background: rgba(34, 211, 238, 0.1);
            border-left-color: #22d3ee;
        }
        
        .main-content {
            margin-left: 200px;
            padding: 20px;
            min-height: 100vh;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid rgba(34, 211, 238, 0.3);
        }
        
        .status-bar {
            background: rgba(34, 211, 238, 0.1);
            border: 1px solid #22d3ee;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 0.9em;
        }
        
        .dashboard {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: rgba(17, 24, 39, 0.8);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(34, 211, 238, 0.3);
            backdrop-filter: blur(10px);
        }
        
        .card h3 {
            color: #22d3ee;
            margin-bottom: 15px;
            font-size: 1.3em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .metric-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .metric {
            background: rgba(34, 211, 238, 0.05);
            padding: 8px 12px;
            border-radius: 6px;
            border-left: 3px solid #22d3ee;
        }
        
        .metric-label {
            font-size: 0.8em;
            color: #94a3b8;
            margin-bottom: 2px;
        }
        
        .metric-value {
            font-size: 1.1em;
            font-weight: bold;
            color: #22d3ee;
        }
        
        .chart-container {
            height: 200px;
            margin-top: 15px;
        }
        
        .cores-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 8px;
            margin-top: 15px;
        }
        
        .core-item {
            background: rgba(34, 211, 238, 0.05);
            border: 1px solid rgba(34, 211, 238, 0.2);
            border-radius: 6px;
            padding: 8px;
            text-align: center;
        }
        
        .core-usage {
            font-size: 1.2em;
            font-weight: bold;
            color: #22d3ee;
        }
        
        .process-table {
            background: rgba(17, 24, 39, 0.8);
            border-radius: 12px;
            border: 1px solid rgba(34, 211, 238, 0.3);
            overflow: hidden;
        }
        
        .table-header {
            background: rgba(34, 211, 238, 0.1);
            padding: 15px 20px;
            font-weight: bold;
            border-bottom: 1px solid rgba(34, 211, 238, 0.3);
        }
        
        .table-row {
            padding: 10px 20px;
            border-bottom: 1px solid rgba(34, 211, 238, 0.1);
            display: grid;
            grid-template-columns: 60px 200px 80px 100px 120px;
            gap: 15px;
            align-items: center;
        }
        
        .table-row:hover {
            background: rgba(34, 211, 238, 0.05);
        }
        
        .full-width {
            grid-column: 1 / -1;
        }
        
        .hidden { display: none; }
        
        @media (max-width: 768px) {
            .sidebar { transform: translateX(-100%); }
            .main-content { margin-left: 0; }
            .dashboard { grid-template-columns: 1fr; }
            .metric-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>🖥️ Mission Center</h2>
        <div class="nav-item active" onclick="showSection('overview')">📊 Resumen</div>
        <div class="nav-item" onclick="showSection('performance')">⚡ Rendimiento</div>
        <div class="nav-item" onclick="showSection('processes')">🔄 Procesos</div>
        <div class="nav-item" onclick="showSection('services')">⚙️ Servicios</div>
    </div>
    
    <div class="main-content">
        <div class="header">
            <h1>Monitor del Sistema</h1>
            <div class="status-bar" id="status">
                <span id="status-text">Conectando...</span>
                <span id="last-update"></span>
            </div>
        </div>
        
        <!-- Sección Resumen -->
        <div id="overview-section">
            <div class="dashboard">
                <!-- CPU Card -->
                <div class="card">
                    <h3>🔥 CPU</h3>
                    <div class="metric-grid">
                        <div class="metric">
                            <div class="metric-label">Uso Total</div>
                            <div class="metric-value" id="cpu-usage">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Frecuencia</div>
                            <div class="metric-value" id="cpu-freq">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Núcleos Lógicos</div>
                            <div class="metric-value" id="cpu-cores">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Núcleos Físicos</div>
                            <div class="metric-value" id="cpu-physical">--</div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="cpuChart"></canvas>
                    </div>
                </div>
                
                <!-- Memory Card -->
                <div class="card">
                    <h3>💾 Memoria</h3>
                    <div class="metric-grid">
                        <div class="metric">
                            <div class="metric-label">RAM Usada</div>
                            <div class="metric-value" id="mem-usage">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Total RAM</div>
                            <div class="metric-value" id="mem-total">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Swap Usada</div>
                            <div class="metric-value" id="swap-usage">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Total Swap</div>
                            <div class="metric-value" id="swap-total">--</div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="memoryChart"></canvas>
                    </div>
                </div>
                
                <!-- Disk Card -->
                <div class="card">
                    <h3>💽 Almacenamiento</h3>
                    <div class="metric-grid">
                        <div class="metric">
                            <div class="metric-label">Lectura</div>
                            <div class="metric-value" id="disk-read">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Escritura</div>
                            <div class="metric-value" id="disk-write">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Dispositivos</div>
                            <div class="metric-value" id="disk-count">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">E/S Total</div>
                            <div class="metric-value" id="io-total">--</div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="diskChart"></canvas>
                    </div>
                </div>
                
                <!-- Network Card -->
                <div class="card">
                    <h3>🌐 Red</h3>
                    <div class="metric-grid">
                        <div class="metric">
                            <div class="metric-label">Subida</div>
                            <div class="metric-value" id="net-sent">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Bajada</div>
                            <div class="metric-value" id="net-recv">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Interfaces</div>
                            <div class="metric-value" id="net-interfaces">--</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">GPU</div>
                            <div class="metric-value" id="gpu-count">--</div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="networkChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Sección Rendimiento -->
        <div id="performance-section" class="hidden">
            <div class="card full-width">
                <h3>🔥 CPU por Núcleo</h3>
                <div class="cores-grid" id="cpu-cores-grid">
                    <!-- Núcleos generados dinámicamente -->
                </div>
                <div class="chart-container">
                    <canvas id="coresChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Sección Procesos -->
        <div id="processes-section" class="hidden">
            <div class="process-table">
                <div class="table-header">Procesos con Mayor Uso de CPU</div>
                <div class="table-row" style="font-weight: bold; background: rgba(34, 211, 238, 0.1);">
                    <div>PID</div>
                    <div>Nombre</div>
                    <div>CPU %</div>
                    <div>Memoria</div>
                    <div>Usuario</div>
                </div>
                <div id="processes-list">
                    <!-- Procesos generados dinámicamente -->
                </div>
            </div>
        </div>
        
        <!-- Sección Servicios -->
        <div id="services-section" class="hidden">
            <div class="card">
                <h3>⚙️ Información del Sistema</h3>
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-label">PCIe Dispositivos</div>
                        <div class="metric-value" id="pcie-devices">--</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Enlaces Activos</div>
                        <div class="metric-value" id="pcie-active">--</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Context Switches</div>
                        <div class="metric-value" id="context-switches">--</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Interrupciones</div>
                        <div class="metric-value" id="interrupts">--</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Variables globales
        let charts = {};
        let currentSection = 'overview';
        
        // Utilidades
        function formatBytes(bytes) {
            if (!bytes || bytes === 0) return '0 B';
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            let size = Math.abs(bytes);
            let unit = 0;
            while (size >= 1024 && unit < units.length - 1) {
                size /= 1024;
                unit++;
            }
            return size.toFixed(1) + ' ' + units[unit];
        }
        
        function formatNumber(num) {
            if (!num) return '0';
            return num.toLocaleString();
        }
        
        // Navegación
        function showSection(section) {
            // Ocultar todas las secciones
            document.querySelectorAll('[id$="-section"]').forEach(el => el.classList.add('hidden'));
            // Mostrar la sección seleccionada
            document.getElementById(section + '-section').classList.remove('hidden');
            
            // Actualizar navegación
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
            
            currentSection = section;
        }
        
        // Inicializar gráficos
        function initCharts() {
            const chartConfig = {
                type: 'line',
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: false },
                        y: { beginAtZero: true, max: 100 }
                    },
                    elements: { point: { radius: 0 } }
                }
            };
            
            // CPU Chart
            charts.cpu = new Chart(document.getElementById('cpuChart'), {
                ...chartConfig,
                data: {
                    labels: Array(60).fill(''),
                    datasets: [{
                        data: Array(60).fill(0),
                        borderColor: '#22d3ee',
                        backgroundColor: 'rgba(34, 211, 238, 0.1)',
                        fill: true
                    }]
                }
            });
            
            // Memory Chart
            charts.memory = new Chart(document.getElementById('memoryChart'), {
                ...chartConfig,
                data: {
                    labels: Array(60).fill(''),
                    datasets: [
                        {
                            data: Array(60).fill(0),
                            borderColor: '#22d3ee',
                            backgroundColor: 'rgba(34, 211, 238, 0.1)',
                            fill: true
                        },
                        {
                            data: Array(60).fill(0),
                            borderColor: '#f97316',
                            backgroundColor: 'rgba(249, 115, 22, 0.1)',
                            fill: true
                        }
                    ]
                }
            });
            
            // Disk Chart
            charts.disk = new Chart(document.getElementById('diskChart'), {
                ...chartConfig,
                options: {
                    ...chartConfig.options,
                    scales: {
                        x: { display: false },
                        y: { beginAtZero: true }
                    }
                },
                data: {
                    labels: Array(60).fill(''),
                    datasets: [
                        {
                            data: Array(60).fill(0),
                            borderColor: '#22c55e',
                            backgroundColor: 'rgba(34, 197, 94, 0.1)',
                            fill: true
                        },
                        {
                            data: Array(60).fill(0),
                            borderColor: '#ef4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            fill: true
                        }
                    ]
                }
            });
            
            // Network Chart
            charts.network = new Chart(document.getElementById('networkChart'), {
                ...chartConfig,
                options: {
                    ...chartConfig.options,
                    scales: {
                        x: { display: false },
                        y: { beginAtZero: true }
                    }
                },
                data: {
                    labels: Array(60).fill(''),
                    datasets: [
                        {
                            data: Array(60).fill(0),
                            borderColor: '#a855f7',
                            backgroundColor: 'rgba(168, 85, 247, 0.1)',
                            fill: true
                        },
                        {
                            data: Array(60).fill(0),
                            borderColor: '#ec4899',
                            backgroundColor: 'rgba(236, 72, 153, 0.1)',
                            fill: true
                        }
                    ]
                }
            });
        }
        
        // Actualizar datos
        function updateData() {
            fetch('/api/current')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('status-text').textContent = 'Conectado ✅';
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                    
                    if (data.error) {
                        console.error('Error:', data.error);
                        return;
                    }
                    
                    updateOverview(data);
                    updatePerformance(data);
                    updateProcesses(data);
                    updateServices(data);
                })
                .catch(e => {
                    document.getElementById('status-text').textContent = 'Error de conexión ❌';
                    console.error('Fetch error:', e);
                });
            
            // Actualizar historial de gráficos
            fetch('/api/history')
                .then(r => r.json())
                .then(history => {
                    updateCharts(history);
                })
                .catch(e => console.error('History fetch error:', e));
        }
        
        function updateOverview(data) {
            // CPU
            document.getElementById('cpu-usage').textContent = data.cpu.usage_percent.toFixed(1) + '%';
            document.getElementById('cpu-freq').textContent = data.cpu.frequency_current.toFixed(0) + ' MHz';
            document.getElementById('cpu-cores').textContent = data.cpu.logical_cores;
            document.getElementById('cpu-physical').textContent = data.cpu.physical_cores;
            
            // Memory
            document.getElementById('mem-usage').textContent = data.memory.percent.toFixed(1) + '%';
            document.getElementById('mem-total').textContent = formatBytes(data.memory.total_bytes);
            document.getElementById('swap-usage').textContent = data.memory.swap_percent.toFixed(1) + '%';
            document.getElementById('swap-total').textContent = formatBytes(data.memory.swap_total_bytes);
            
            // Disk
            const totalRead = data.disk.devices.reduce((sum, d) => sum + d.read_rate, 0);
            const totalWrite = data.disk.devices.reduce((sum, d) => sum + d.write_rate, 0);
            document.getElementById('disk-read').textContent = formatBytes(totalRead) + '/s';
            document.getElementById('disk-write').textContent = formatBytes(totalWrite) + '/s';
            document.getElementById('disk-count').textContent = data.disk.devices.length;
            document.getElementById('io-total').textContent = formatBytes(data.io.read_rate + data.io.write_rate) + '/s';
            
            // Network
            const totalSent = data.network.interfaces.reduce((sum, i) => sum + i.sent_rate, 0);
            const totalRecv = data.network.interfaces.reduce((sum, i) => sum + i.recv_rate, 0);
            document.getElementById('net-sent').textContent = formatBytes(totalSent) + '/s';
            document.getElementById('net-recv').textContent = formatBytes(totalRecv) + '/s';
            document.getElementById('net-interfaces').textContent = data.network.interfaces.filter(i => i.is_up).length;
            document.getElementById('gpu-count').textContent = data.gpu.length;
        }
        
        function updatePerformance(data) {
            // CPU por núcleo
            const coresGrid = document.getElementById('cpu-cores-grid');
            coresGrid.innerHTML = '';
            
            data.cpu.cores.forEach(core => {
                const coreDiv = document.createElement('div');
                coreDiv.className = 'core-item';
                coreDiv.innerHTML = `
                    <div>Núcleo ${core.id}</div>
                    <div class="core-usage">${core.usage.toFixed(1)}%</div>
                    <div style="font-size: 0.8em; color: #94a3b8;">${core.frequency.toFixed(0)} MHz</div>
                `;
                coresGrid.appendChild(coreDiv);
            });
        }
        
        function updateProcesses(data) {
            const processList = document.getElementById('processes-list');
            processList.innerHTML = '';
            
            data.processes.top_cpu.forEach(proc => {
                const row = document.createElement('div');
                row.className = 'table-row';
                row.innerHTML = `
                    <div>${proc.pid}</div>
                    <div>${proc.name}</div>
                    <div>${proc.cpu_percent.toFixed(1)}%</div>
                    <div>${formatBytes(proc.memory_bytes)}</div>
                    <div>${proc.username || '--'}</div>
                `;
                processList.appendChild(row);
            });
        }
        
        function updateServices(data) {
            document.getElementById('pcie-devices').textContent = data.pcie.device_count;
            document.getElementById('pcie-active').textContent = data.pcie.active_links;
            document.getElementById('context-switches').textContent = formatNumber(data.cpu.context_switches);
            document.getElementById('interrupts').textContent = formatNumber(data.cpu.interrupts);
        }
        
        function updateCharts(history) {
            if (!history) return;
            
            // CPU Chart
            if (history.cpu && charts.cpu) {
                const cpuData = history.cpu.map(d => d.usage);
                charts.cpu.data.datasets[0].data = cpuData;
                charts.cpu.update('none');
            }
            
            // Memory Chart (RAM + Swap)
            if (history.memory && charts.memory) {
                const ramData = history.memory.map(d => d.usage);
                const swapData = history.memory.map(d => d.swap_usage);
                charts.memory.data.datasets[0].data = ramData;
                charts.memory.data.datasets[1].data = swapData;
                charts.memory.update('none');
            }
            
            // Disk Chart (Read + Write)
            if (history.disk && charts.disk) {
                const readData = history.disk.map(d => d.read / 1024 / 1024); // MB/s
                const writeData = history.disk.map(d => d.write / 1024 / 1024); // MB/s
                charts.disk.data.datasets[0].data = readData;
                charts.disk.data.datasets[1].data = writeData;
                charts.disk.update('none');
            }
            
            // Network Chart (Sent + Received)
            if (history.network && charts.network) {
                const sentData = history.network.map(d => d.sent / 1024 / 1024); // MB/s
                const recvData = history.network.map(d => d.recv / 1024 / 1024); // MB/s
                charts.network.data.datasets[0].data = sentData;
                charts.network.data.datasets[1].data = recvData;
                charts.network.update('none');
            }
        }
        
        // Inicialización
        document.addEventListener('DOMContentLoaded', () => {
            initCharts();
            updateData();
            setInterval(updateData, 1000); // Actualizar cada segundo
        });
    </script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def send_current_data(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(collector.current_data, default=str).encode('utf-8'))
    
    def send_history_data(self):
        history = {
            'cpu': list(collector.cpu_history),
            'memory': list(collector.memory_history),
            'network': list(collector.network_history),
            'disk': list(collector.disk_history),
            'cpu_cores': {k: list(v) for k, v in collector.cpu_cores_history.items()}
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(history, default=str).encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # Silenciar logs HTTP

def main():
    import socket
    
    # Encontrar puerto disponible
    def find_free_port():
        for port in [8080, 8081, 8082, 8083, 8084]:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue
        return None
    
    PORT = find_free_port()
    if not PORT:
        print("❌ No se pudo encontrar un puerto disponible")
        return
    
    print("🚀 Mission Center Clone - Versión Avanzada")
    print("🎯 Interfaz estilo Windows con gráficos en tiempo real")
    print(f"⚡ Servidor iniciando en puerto {PORT}...")
    
    try:
        server = HTTPServer(('localhost', PORT), MissionCenterHandler)
        print(f"✅ Servidor corriendo en http://localhost:{PORT}")
        print("🌐 Abre tu navegador y ve a la URL de arriba")
        print("📊 Incluye: gráficos en tiempo real, CPU por núcleo, swap, procesos y más")
        print("⏹️  Presiona Ctrl+C para detener")
        
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor...")
        collector.running = False
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()