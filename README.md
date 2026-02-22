# 🚗 Control de Acceso Integral v3.0

Sistema de control de acceso para vehículos y personas desarrollado para Raúl Seguridad S.A.

## ✨ Características

### 🔍 Validación Dual
- **Vehículos**: Validación por patente chilena
- **Personas**: Validación por RUT con dígito verificador

### 👮 Gestión de Guardias
- 14 guardias pre-cargados automáticamente
- Dropdown en sidebar (sin necesidad de escribir)
- Sistema de activación/desactivación

### ⏰ Sistema de Turnos Automático
- **Turno Día**: 8:00 - 20:00 ☀️
- **Turno Noche**: 20:00 - 8:00 🌙
- Detección automática según hora de Chile
- Registro en cada ingreso

### 📊 Registros Completos
- Historial de ingresos por día o rango de fechas
- Filtros por tipo (vehículo/persona)
- Estadísticas por turno
- Exportación a CSV

## 🚀 Despliegue en Streamlit Cloud

### 1. Preparar Repositorio GitHub

1. Crear nuevo repositorio en [github.com](https://github.com)
2. Subir estos 4 archivos:
   - `app.py`
   - `requirements.txt`  
   - `README.md`
   - `.gitignore`

### 2. Conectar a Streamlit Cloud

1. Ir a [share.streamlit.io](https://share.streamlit.io)
2. Click en "New app"
3. Seleccionar tu repositorio
4. Main file: `app.py`
5. Click "Deploy"
6. ¡Esperar 3-5 minutos!

## 📋 Guardias Pre-cargados

Al iniciar, se cargan automáticamente 14 guardias del archivo Excel.

## 🧪 Prueba Rápida

1. Seleccionar guardia en sidebar
2. TAB "Personas" → Agregar persona con RUT `12345678-9`
3. TAB "Validar Entrada" → Buscar RUT y confirmar ingreso
4. TAB "Registros" → Ver ingreso con turno automático ✅

## 🔧 Estructura

```
├── app.py                 # Aplicación principal (750 líneas)
├── requirements.txt       # Dependencias
├── README.md             # Este archivo
└── .gitignore            # Archivos a ignorar
```

## 💾 Base de Datos

SQLite (se crea automáticamente):
- vehiculos
- personas  
- guardias
- registro_ingresos

## 🆘 Soporte

Si hay problemas, revisar logs en Streamlit Cloud → "Manage app" → "Logs"

---

**Versión**: 3.0 | **Última actualización**: Enero 2026
