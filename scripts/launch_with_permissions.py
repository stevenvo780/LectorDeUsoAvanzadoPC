#!/usr/bin/env python3
"""
Lanzador de Mission Center con permisos elevados usando PolicyKit.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Ruta base del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
MAIN_SCRIPT = PROJECT_ROOT / "main.py"
PYTHON_EXECUTABLE = sys.executable


def check_permissions():
    """Verifica si tenemos los permisos necesarios."""
    # Verificar acceso a archivos del sistema que requieren permisos
    test_files = [
        "/proc/meminfo",
        "/proc/cpuinfo", 
        "/proc/stat",
        "/proc/loadavg",
        "/sys/class/dmi/id/product_name",
        "/sys/class/hwmon",
        "/sys/devices/system/cpu",
    ]
    
    accessible_files = 0
    for file_path in test_files:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    f.read(1)  # Intentar leer al menos 1 byte
                accessible_files += 1
        except (PermissionError, OSError):
            continue
    
    return accessible_files >= len(test_files) * 0.8  # Al menos 80% accesible


def check_container_environment():
    """Detecta si estamos ejecutando en un contenedor o entorno restringido."""
    container_indicators = [
        # Verificar archivos de contenedor
        os.path.exists("/.dockerenv"),
        os.path.exists("/run/.containerenv"),
        # Verificar variables de entorno
        "container" in os.environ,
        "DOCKER_CONTAINER" in os.environ,
        "KUBERNETES_SERVICE_HOST" in os.environ,
    ]
    
    # Verificar si no se pueden elevar privilegios
    no_new_privs = False
    try:
        # Intentar verificar la bandera no_new_privs
        result = subprocess.run(
            ["grep", "-q", "NoNewPrivs.*1", "/proc/self/status"],
            capture_output=True,
            timeout=5
        )
        no_new_privs = result.returncode == 0
    except:
        pass
    
    return {
        "is_container": any(container_indicators),
        "no_new_privs": no_new_privs,
        "has_restrictions": any(container_indicators) or no_new_privs
    }


def check_pkexec():
    """Verifica si pkexec está disponible."""
    return shutil.which("pkexec") is not None


def check_sudo():
    """Verifica si sudo está disponible."""
    return shutil.which("sudo") is not None


def create_policy_file():
    """Crea un archivo de política para PolicyKit."""
    policy_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>
  <action id="org.missioncenter.run">
    <description>Run Mission Center with system access</description>
    <message>Mission Center necesita acceso al sistema para monitorear recursos</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">{python}</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>
</policyconfig>""".format(python=PYTHON_EXECUTABLE)
    
    policy_file = PROJECT_ROOT / "mission-center.policy"
    policy_file.write_text(policy_content)
    return policy_file


def install_policy():
    """Instala la política de PolicyKit."""
    policy_file = create_policy_file()
    system_policy_dir = Path("/usr/share/polkit-1/actions")
    
    if system_policy_dir.exists():
        try:
            # Copiar la política al directorio del sistema
            subprocess.run([
                "sudo", "cp", str(policy_file), 
                str(system_policy_dir / "mission-center.policy")
            ], check=True)
            print("✅ Política de PolicyKit instalada correctamente")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Error instalando política: {e}")
            return False
    else:
        print("⚠️  Directorio de políticas no encontrado")
        return False


def launch_with_pkexec():
    """Lanza la aplicación usando pkexec."""
    try:
        cmd = [
            "pkexec", 
            "--action-id", "org.missioncenter.run",
            PYTHON_EXECUTABLE,
            str(MAIN_SCRIPT)
        ]
        
        print("🔐 Solicitando permisos de administrador...")
        print("💡 Se abrirá una ventana de autenticación")
        
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando con pkexec: {e}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Operación cancelada por el usuario")
        return False
    
    return True


def launch_with_sudo():
    """Lanza la aplicación usando sudo."""
    try:
        cmd = [
            "sudo", 
            PYTHON_EXECUTABLE,
            str(MAIN_SCRIPT)
        ]
        
        print("🔐 Solicitando permisos de administrador con sudo...")
        
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando con sudo: {e}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Operación cancelada por el usuario")
        return False
    
    return True


def launch_normal():
    """Lanza la aplicación normalmente (sin permisos elevados)."""
    try:
        cmd = [PYTHON_EXECUTABLE, str(MAIN_SCRIPT)]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    except KeyboardInterrupt:
        print("\n🛑 Aplicación detenida por el usuario")


def main():
    """Función principal."""
    print("🚀 Mission Center - Lanzador con Permisos")
    print("=" * 45)
    
    # Verificar entorno de ejecución
    container_info = check_container_environment()
    
    if container_info["has_restrictions"]:
        print("🐳 Entorno contenedorizado o restringido detectado")
        if container_info["is_container"]:
            print("📦 Ejecutándose dentro de un contenedor")
        if container_info["no_new_privs"]:
            print("🔒 Bandera 'no new privileges' activa")
        print("")
        print("💡 En entornos contenedorizados:")
        print("   • Los datos básicos del sistema están disponibles")
        print("   • Algunos sensores pueden no ser accesibles")
        print("   • La elevación de privilegios está restringida")
        print("")
        print("🎯 Iniciando Mission Center en modo contenedor...")
        launch_normal()
        return
    
    # Verificar si ya tenemos los permisos necesarios
    if check_permissions():
        print("✅ Permisos suficientes detectados")
        print("🎯 Iniciando Mission Center...")
        launch_normal()
        return
    
    print("⚠️  Se requieren permisos elevados para acceso completo al sistema")
    print("📊 Esto permite monitorear:")
    print("   • Información detallada de CPU y temperatura")
    print("   • Estadísticas de memoria y swap") 
    print("   • Datos de sensores de hardware")
    print("   • Información completa de procesos")
    print("   • Estadísticas de E/S de disco")
    print("")
    
    # Verificar métodos de elevación disponibles
    has_pkexec = check_pkexec()
    has_sudo = check_sudo()
    
    if has_pkexec:
        print("🔐 Usando PolicyKit (pkexec) para solicitar permisos...")
        
        # Preguntar si instalar la política
        print("💡 ¿Deseas instalar la política de PolicyKit para futuros usos? (y/N): ", end="")
        try:
            response = input().strip().lower()
            if response in ['y', 'yes', 's', 'si', 'sí']:
                if install_policy():
                    print("✅ Política instalada correctamente")
                else:
                    print("⚠️  No se pudo instalar la política, continuando sin ella")
        except KeyboardInterrupt:
            print("\n🛑 Operación cancelada")
            return
        
        if launch_with_pkexec():
            return
            
    if has_sudo:
        print("🔐 Usando sudo como alternativa...")
        if launch_with_sudo():
            return
    
    if not has_pkexec and not has_sudo:
        print("❌ No se encontraron métodos de elevación de permisos")
        print("💡 Instala 'policykit-1' o 'sudo' para usar permisos elevados")
    
    print("⚠️  Ejecutando con permisos limitados...")
    print("📊 Algunas métricas pueden no estar disponibles")
    launch_normal()


if __name__ == "__main__":
    main()