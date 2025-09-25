#!/usr/bin/env bash
# Mission Center - Lanzador con permisos elevados
# Este script solicita permisos de administrador automáticamente

cd "$(dirname "$0")"
python3 scripts/launch_with_permissions.py