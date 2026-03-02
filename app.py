import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import re
import pytz

# Configurar zona horaria de Chile
CHILE_TZ = pytz.timezone('America/Santiago')

# Configuración de la página
st.set_page_config(
    page_title="Control de Acceso - Raúl Seguridad",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",  # Siempre expandido
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Control de Acceso Integral v3.0\nDesarrollado por Raúl Seguridad S.A."
    }
)

# CSS personalizado  
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .big-font {font-size:30px !important; font-weight: bold;}
    .stAlert {padding: 1rem; margin: 1rem 0;}
    .stDeployButton {display:none;}
    .stApp header {background-color: transparent;}
    
    /* Ocultar COMPLETAMENTE el botón de colapsar sidebar */
    button[kind="header"],
    [data-testid="collapsedControl"],
    .css-1544g2n,
    .css-163ttbj {
        display: none !important;
        visibility: hidden !important;
    }
    </style>
    
    <script>
    // Forzar que el sidebar esté abierto
    window.addEventListener('load', function() {
        const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            sidebar.setAttribute('aria-expanded', 'true');
            sidebar.style.display = 'block';
            sidebar.style.visibility = 'visible';
        }
    });
    </script>
    """, unsafe_allow_html=True)

# Lista de guardias iniciales
GUARDIAS_INICIALES = [
    "BECERRA VALDIVIA MARTHA CECILIA", "BRIZUELA MATURANA CAROLINA MAGDALENA",
    "CARO CATILLO CAROLINA ALEJANDRA", "CASTILLO ARAYA CAMILA JAVIERA",
    "CEBALLOS VELASQUEZ FRANCESCA PILAR", "DE LA CRUZ NUÑEZ CAROLINE",
    "FERREIRA VARGAS LAUDENI", "LOPEZ ALCOCER MARIA NEIDY",
    "LOPEZ LADINO LINA MARCELA", "PEREZ LOPEZ LAURA",
    "RAMIREZ MORALES RODRIGO ALEJANDRO", "SALINAS MORA ALEJANDRA JAVIERA",
    "BRIZUELA VERONICA", "OLAVE CATALINA"
]

# ==================== FUNCIONES DE BASE DE DATOS ====================

def init_db():
    conn = sqlite3.connect('control_acceso.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS vehiculos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, patente TEXT UNIQUE NOT NULL,
        propietario TEXT NOT NULL, rut TEXT, depto TEXT, marca TEXT, modelo TEXT, color TEXT,
        telefono TEXT, fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        activo INTEGER DEFAULT 1, observaciones TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS personas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, rut TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL, depto TEXT, telefono TEXT, tipo TEXT,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        activo INTEGER DEFAULT 1, observaciones TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS guardias (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE NOT NULL,
        telefono TEXT, activo INTEGER DEFAULT 1)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS registro_ingresos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tipo_registro TEXT NOT NULL,
        identificador TEXT NOT NULL, nombre_persona TEXT, depto TEXT,
        fecha_hora TEXT NOT NULL, guardia TEXT NOT NULL, turno TEXT NOT NULL,
        tipo_ingreso TEXT, observaciones TEXT)''')
    
    # MIGRACIÓN: Agregar columna RUT a tabla vehiculos si no existe
    try:
        c.execute("SELECT rut FROM vehiculos LIMIT 1")
    except sqlite3.OperationalError:
        # La columna no existe, agregarla
        c.execute("ALTER TABLE vehiculos ADD COLUMN rut TEXT")
    
    # MIGRACIÓN: Agregar columna estado_autorizacion a vehiculos
    try:
        c.execute("SELECT estado_autorizacion FROM vehiculos LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE vehiculos ADD COLUMN estado_autorizacion TEXT DEFAULT 'AUTORIZADO'")
    
    # MIGRACIÓN: Agregar columna estado_autorizacion a personas
    try:
        c.execute("SELECT estado_autorizacion FROM personas LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE personas ADD COLUMN estado_autorizacion TEXT DEFAULT 'AUTORIZADO'")
    
    conn.commit()
    conn.close()

def cargar_guardias_iniciales():
    conn = sqlite3.connect('control_acceso.db')
    c = conn.cursor()
    for nombre in GUARDIAS_INICIALES:
        try:
            c.execute('INSERT OR IGNORE INTO guardias (nombre, telefono) VALUES (?, ?)', (nombre, ""))
        except:
            pass
    conn.commit()
    conn.close()

# ==================== VALIDACIÓN ====================

def validar_patente(patente):
    patente = patente.replace("-", "").replace(" ", "").upper()
    return any(re.match(p, patente) for p in [r'^[A-Z]{4}\d{2}$', r'^[A-Z]{2}\d{4}$', r'^[A-Z]{2}\d{2}\d{2}$'])

def validar_rut(rut):
    """Valida formato RUT chileno con dígito verificador"""
    rut = rut.replace(".", "").replace("-", "").upper()
    if len(rut) < 2:
        return False
    
    rut_num = rut[:-1]
    dv = rut[-1]
    
    if not rut_num.isdigit():
        return False
    
    # Calcular dígito verificador con algoritmo módulo 11
    suma = 0
    multiplo = 2
    for r in reversed(rut_num):
        suma += int(r) * multiplo
        multiplo += 1
        if multiplo == 8:
            multiplo = 2
    
    resto = suma % 11
    dvr = 11 - resto
    
    if dvr == 11:
        dvr = '0'
    elif dvr == 10:
        dvr = 'K'
    else:
        dvr = str(dvr)
    
    return dv == dvr

def formatear_rut(rut):
    rut = rut.replace(".", "").replace("-", "").upper()
    if len(rut) < 2:
        return rut
    rut_num, dv = rut[:-1], rut[-1]
    rut_formateado = ""
    for i, digito in enumerate(reversed(rut_num)):
        if i > 0 and i % 3 == 0:
            rut_formateado = "." + rut_formateado
        rut_formateado = digito + rut_formateado
    return f"{rut_formateado}-{dv}"

def determinar_turno():
    return "Día (8:00-20:00)" if 8 <= datetime.now(CHILE_TZ).hour < 20 else "Noche (20:00-8:00)"

# ==================== GUARDIAS ====================

def agregar_guardia(nombre, telefono=""):
    try:
        conn = sqlite3.connect('control_acceso.db')
        c = conn.cursor()
        c.execute('INSERT INTO guardias (nombre, telefono) VALUES (?, ?)', (nombre.strip().upper(), telefono.strip()))
        conn.commit()
        conn.close()
        return True, f"Guardia {nombre} agregado correctamente"
    except sqlite3.IntegrityError:
        return False, f"El guardia {nombre} ya existe"
    except Exception as e:
        return False, f"Error: {str(e)}"

def obtener_guardias_activos():
    conn = sqlite3.connect('control_acceso.db')
    df = pd.read_sql_query('SELECT nombre FROM guardias WHERE activo = 1 ORDER BY nombre', conn)
    conn.close()
    return df['nombre'].tolist() if not df.empty else []

def obtener_todos_guardias():
    conn = sqlite3.connect('control_acceso.db')
    df = pd.read_sql_query('SELECT * FROM guardias ORDER BY activo DESC, nombre', conn)
    conn.close()
    return df

def desactivar_guardia(guardia_id):
    conn = sqlite3.connect('control_acceso.db')
    c = conn.cursor()
    c.execute('UPDATE guardias SET activo = 0 WHERE id = ?', (guardia_id,))
    conn.commit()
    conn.close()

def reactivar_guardia(guardia_id):
    conn = sqlite3.connect('control_acceso.db')
    c = conn.cursor()
    c.execute('UPDATE guardias SET activo = 1 WHERE id = ?', (guardia_id,))
    conn.commit()
    conn.close()

# ==================== PERSONAS ====================

def agregar_persona(rut, nombre, depto, telefono, tipo, estado_autorizacion="AUTORIZADO", observaciones=""):
    try:
        conn = sqlite3.connect('control_acceso.db')
        c = conn.cursor()
        fecha_registro_chile = datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''INSERT INTO personas (rut, nombre, depto, telefono, tipo, fecha_registro, estado_autorizacion, observaciones)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (rut.upper(), nombre.upper(), depto, telefono, tipo, fecha_registro_chile, estado_autorizacion, observaciones))
        conn.commit()
        conn.close()
        return True, f"Persona {nombre} agregada correctamente"
    except sqlite3.IntegrityError:
        return False, f"El RUT {rut} ya está registrado"
    except Exception as e:
        return False, f"Error: {str(e)}"

def buscar_persona(rut):
    conn = sqlite3.connect('control_acceso.db')
    df = pd.read_sql_query('SELECT * FROM personas WHERE rut = ? AND activo = 1', conn, params=[rut.upper()])
    conn.close()
    return df

def obtener_personas():
    conn = sqlite3.connect('control_acceso.db')
    df = pd.read_sql_query('SELECT * FROM personas WHERE activo = 1 ORDER BY nombre', conn)
    conn.close()
    return df

def obtener_todas_personas():
    conn = sqlite3.connect('control_acceso.db')
    df = pd.read_sql_query('SELECT * FROM personas ORDER BY activo DESC, nombre', conn)
    conn.close()
    return df

def desactivar_persona(persona_id):
    conn = sqlite3.connect('control_acceso.db')
    c = conn.cursor()
    c.execute('UPDATE personas SET activo = 0 WHERE id = ?', (persona_id,))
    conn.commit()
    conn.close()

def reactivar_persona(persona_id):
    conn = sqlite3.connect('control_acceso.db')
    c = conn.cursor()
    c.execute('UPDATE personas SET activo = 1 WHERE id = ?', (persona_id,))
    conn.commit()
    conn.close()

# ==================== VEHÍCULOS ====================

def agregar_vehiculo(patente, propietario, rut="", depto="", marca="", modelo="", color="", telefono="", estado_autorizacion="AUTORIZADO", observaciones=""):
    try:
        conn = sqlite3.connect('control_acceso.db')
        c = conn.cursor()
        fecha_registro_chile = datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''INSERT INTO vehiculos (patente, propietario, rut, depto, marca, modelo, color, telefono, fecha_registro, estado_autorizacion, observaciones)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (patente.upper(), propietario.upper(), rut.upper(), depto, marca, modelo, color, telefono, fecha_registro_chile, estado_autorizacion, observaciones))
        conn.commit()
        conn.close()
        return True, f"Vehículo {patente.upper()} agregado correctamente"
    except sqlite3.IntegrityError:
        return False, f"La patente {patente.upper()} ya está registrada"
    except Exception as e:
        return False, f"Error: {str(e)}"

def buscar_vehiculo(patente):
    conn = sqlite3.connect('control_acceso.db')
    df = pd.read_sql_query('SELECT * FROM vehiculos WHERE patente = ? AND activo = 1', conn, params=[patente.upper()])
    conn.close()
    return df

def obtener_vehiculos():
    conn = sqlite3.connect('control_acceso.db')
    df = pd.read_sql_query('SELECT * FROM vehiculos WHERE activo = 1 ORDER BY fecha_registro DESC', conn)
    conn.close()
    return df

def obtener_todos_vehiculos():
    conn = sqlite3.connect('control_acceso.db')
    df = pd.read_sql_query('SELECT * FROM vehiculos ORDER BY activo DESC, fecha_registro DESC', conn)
    conn.close()
    return df

def desactivar_vehiculo(vehiculo_id):
    conn = sqlite3.connect('control_acceso.db')
    c = conn.cursor()
    c.execute('UPDATE vehiculos SET activo = 0 WHERE id = ?', (vehiculo_id,))
    conn.commit()
    conn.close()

def reactivar_vehiculo(vehiculo_id):
    conn = sqlite3.connect('control_acceso.db')
    c = conn.cursor()
    c.execute('UPDATE vehiculos SET activo = 1 WHERE id = ?', (vehiculo_id,))
    conn.commit()
    conn.close()

# ==================== REGISTROS ====================

def registrar_ingreso(tipo_registro, identificador, nombre_persona, depto, guardia, turno, tipo_ingreso="", observaciones=""):
    conn = sqlite3.connect('control_acceso.db')
    c = conn.cursor()
    fecha_hora_chile = datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''INSERT INTO registro_ingresos (tipo_registro, identificador, nombre_persona, depto, fecha_hora, guardia, turno, tipo_ingreso, observaciones)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (tipo_registro, identificador, nombre_persona, depto, fecha_hora_chile, guardia, turno, tipo_ingreso, observaciones))
    conn.commit()
    conn.close()

def obtener_registros_hoy():
    fecha_hoy_chile = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
    conn = sqlite3.connect('control_acceso.db')
    df = pd.read_sql_query('''SELECT tipo_registro, identificador, nombre_persona, depto, fecha_hora, guardia, turno, tipo_ingreso
                              FROM registro_ingresos WHERE DATE(fecha_hora) = ? ORDER BY fecha_hora DESC''',
                           conn, params=[fecha_hoy_chile])
    conn.close()
    return df

def obtener_registros_rango_fechas(fecha_inicio, fecha_fin):
    conn = sqlite3.connect('control_acceso.db')
    df = pd.read_sql_query('''SELECT tipo_registro, identificador, nombre_persona, depto, fecha_hora, guardia, turno, tipo_ingreso
                              FROM registro_ingresos WHERE DATE(fecha_hora) BETWEEN ? AND ? ORDER BY fecha_hora DESC''',
                           conn, params=[fecha_inicio, fecha_fin])
    conn.close()
    return df

# ==================== INICIALIZAR ====================

init_db()
cargar_guardias_iniciales()

if 'vehiculo_encontrado' not in st.session_state:
    st.session_state.vehiculo_encontrado = None
if 'persona_encontrada' not in st.session_state:
    st.session_state.persona_encontrada = None
if 'mostrar_confirmacion_vehiculo' not in st.session_state:
    st.session_state.mostrar_confirmacion_vehiculo = False
if 'mostrar_confirmacion_persona' not in st.session_state:
    st.session_state.mostrar_confirmacion_persona = False
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = datetime.now(CHILE_TZ)

if st.session_state.auto_refresh:
    tiempo_transcurrido = (datetime.now(CHILE_TZ) - st.session_state.last_refresh_time).total_seconds()
    if tiempo_transcurrido > 30:
        st.session_state.last_refresh_time = datetime.now(CHILE_TZ)
        st.rerun()

# ==================== INTERFAZ ====================

st.markdown('<p class="big-font">🏢 Control de Acceso Integral</p>', unsafe_allow_html=True)
st.markdown("### Sistema de Seguridad - Vehículos y Personas")

# SELECTOR DE GUARDIA EN LA PÁGINA PRINCIPAL (no en sidebar)
st.subheader("👤 Selecciona Guardia en Turno")

guardias_disponibles = obtener_guardias_activos()

col_guard, col_turno, col_hora = st.columns([2, 1, 1])

with col_guard:
    if guardias_disponibles:
        # Mantener guardia seleccionado después de rerun
        if 'guardia_actual' in st.session_state and st.session_state.guardia_actual in guardias_disponibles:
            default_index = guardias_disponibles.index(st.session_state.guardia_actual) + 1
        else:
            default_index = 0
        
        nombre_guardia = st.selectbox(
            "Guardia:",
            options=[""] + guardias_disponibles,
            index=default_index,
            key="guardia_select_main"
        )
        
        # Guardar en session_state
        if nombre_guardia:
            st.session_state.guardia_actual = nombre_guardia
    else:
        st.warning("⚠️ No hay guardias registrados")
        nombre_guardia = st.text_input("Nombre del Guardia:", key="guardia_nombre_manual_main")

with col_turno:
    if nombre_guardia:
        turno_actual = determinar_turno()
        if "Día" in turno_actual:
            st.success(f"☀️ {turno_actual}")
        else:
            st.info(f"🌙 {turno_actual}")

with col_hora:
    if nombre_guardia:
        # Placeholder para el reloj que se actualiza
        reloj_placeholder = st.empty()
        hora_actual = datetime.now(CHILE_TZ).strftime('%H:%M:%S')
        fecha_actual = datetime.now(CHILE_TZ).strftime('%d/%m/%Y')
        
        with reloj_placeholder.container():
            st.metric("🕐 Hora Chile", hora_actual)
            st.caption(f"📅 {fecha_actual}")
        
        # Auto-refresh cada 30 segundos para actualizar el reloj
        if 'last_refresh_time' not in st.session_state:
            st.session_state.last_refresh_time = datetime.now(CHILE_TZ)
        
        tiempo_transcurrido = (datetime.now(CHILE_TZ) - st.session_state.last_refresh_time).total_seconds()
        if tiempo_transcurrido >= 30:
            st.session_state.last_refresh_time = datetime.now(CHILE_TZ)
            st.rerun()

if nombre_guardia:
    st.success(f"✅ Guardia activo: **{nombre_guardia}**")

st.divider()

# TABS
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Validar Entrada", "🚗 Vehículos", "👤 Personas", "👮 Guardias", "📈 Registros"])

# TAB 1: VALIDAR ENTRADA
with tab1:
    st.header("🔍 Validación de Entrada")
    
    if not nombre_guardia:
        st.warning("⚠️ Debes seleccionar un guardia para continuar")
    else:
        col_veh, col_per = st.columns(2)
        
        with col_veh:
            st.subheader("🚗 Validar Vehículo")
            with st.form("validar_vehiculo_form"):
                patente_buscar = st.text_input("Patente del Vehículo", max_chars=8).upper()
                tipo_ingreso_veh = st.selectbox("Tipo de Ingreso", ["Residente", "Visita", "Servicio"], key="tipo_veh")
                buscar_vehiculo_btn = st.form_submit_button("🔍 BUSCAR VEHÍCULO", use_container_width=True, type="primary")
                
                if buscar_vehiculo_btn and patente_buscar:
                    if not validar_patente(patente_buscar):
                        st.error("❌ Formato de patente inválido")
                    else:
                        df_vehiculo = buscar_vehiculo(patente_buscar)
                        if not df_vehiculo.empty:
                            st.session_state.vehiculo_encontrado = df_vehiculo.iloc[0]
                            st.session_state.mostrar_confirmacion_vehiculo = True
                        else:
                            st.error("❌ VEHÍCULO NO AUTORIZADO")
                            st.session_state.vehiculo_encontrado = None
            
            if st.session_state.vehiculo_encontrado is not None and st.session_state.mostrar_confirmacion_vehiculo:
                veh = st.session_state.vehiculo_encontrado
                
                # Verificar estado de autorización
                estado_aut = veh.get('estado_autorizacion', 'AUTORIZADO')
                
                if estado_aut == "NO AUTORIZADO":
                    st.error("🚫 ¡ATENCIÓN! VEHÍCULO NO AUTORIZADO - NO PERMITIR INGRESO")
                    st.write(f"**Patente:** {veh['patente']}")
                    st.write(f"**Propietario:** {veh['propietario']}")
                    st.write(f"**Depto:** {veh['depto']}")
                    if veh['observaciones']:
                        st.warning(f"**Motivo:** {veh['observaciones']}")
                    st.info("👮 Contactar al administrador o supervisor si intenta ingresar")
                    
                elif estado_aut == "RESTRINGIDO":
                    st.warning("⚠️ VEHÍCULO RESTRINGIDO - VERIFICAR ANTES DE AUTORIZAR")
                    st.write(f"**Patente:** {veh['patente']}")
                    st.write(f"**Propietario:** {veh['propietario']}")
                    st.write(f"**Depto:** {veh['depto']}")
                    if veh['marca'] or veh['modelo']:
                        st.write(f"**Vehículo:** {veh['marca']} {veh['modelo']} ({veh['color']})")
                    if veh['observaciones']:
                        st.warning(f"**Restricción:** {veh['observaciones']}")
                    
                    with st.form("confirmar_ingreso_vehiculo"):
                        st.write(f"**Tipo:** {tipo_ingreso_veh}")
                        turno_veh = determinar_turno()
                        st.caption(f"Turno: {turno_veh}")
                        st.warning("⚠️ Confirmar solo si cumple con las restricciones indicadas")
                        confirmar_btn = st.form_submit_button("⚠️ AUTORIZAR EXCEPCIONALMENTE", type="secondary", use_container_width=True)
                        
                        if confirmar_btn:
                            registrar_ingreso("VEHICULO", veh['patente'], veh['propietario'], veh['depto'], nombre_guardia, turno_veh, tipo_ingreso_veh, f"RESTRINGIDO: {veh.get('observaciones', '')}")
                            st.warning(f"⚠️ Ingreso EXCEPCIONAL de {veh['patente']} registrado")
                            st.session_state.vehiculo_encontrado = None
                            st.session_state.mostrar_confirmacion_vehiculo = False
                            st.rerun()
                
                else:  # AUTORIZADO
                    st.success("✅ VEHÍCULO AUTORIZADO")
                    st.write(f"**Patente:** {veh['patente']}")
                    st.write(f"**Propietario:** {veh['propietario']}")
                    st.write(f"**Depto:** {veh['depto']}")
                    if veh['marca'] or veh['modelo']:
                        st.write(f"**Vehículo:** {veh['marca']} {veh['modelo']} ({veh['color']})")
                    
                    with st.form("confirmar_ingreso_vehiculo"):
                        st.write(f"**Tipo:** {tipo_ingreso_veh}")
                        turno_veh = determinar_turno()
                        st.caption(f"Turno: {turno_veh}")
                        confirmar_btn = st.form_submit_button("✅ CONFIRMAR INGRESO", type="primary", use_container_width=True)
                        
                        if confirmar_btn:
                            registrar_ingreso("VEHICULO", veh['patente'], veh['propietario'], veh['depto'], nombre_guardia, turno_veh, tipo_ingreso_veh)
                            st.success(f"✅ Ingreso de {veh['patente']} registrado correctamente")
                            st.balloons()
                            st.session_state.vehiculo_encontrado = None
                            st.session_state.mostrar_confirmacion_vehiculo = False
                            st.rerun()
                
                if st.button("🔄 NUEVA BÚSQUEDA", key="nueva_busqueda_veh"):
                    st.session_state.vehiculo_encontrado = None
                    st.session_state.mostrar_confirmacion_vehiculo = False
                    st.rerun()
        
        with col_per:
            st.subheader("👤 Validar Persona")
            with st.form("validar_persona_form"):
                rut_buscar = st.text_input("RUT (sin puntos, con guión)", max_chars=12, placeholder="12345678-9").upper()
                tipo_ingreso_per = st.selectbox("Tipo de Ingreso", ["Residente", "Visita", "Servicio", "Delivery"], key="tipo_per")
                buscar_persona_btn = st.form_submit_button("🔍 BUSCAR PERSONA", use_container_width=True, type="primary")
                
                if buscar_persona_btn and rut_buscar:
                    if not validar_rut(rut_buscar):
                        st.error("❌ RUT inválido")
                    else:
                        df_persona = buscar_persona(rut_buscar)
                        if not df_persona.empty:
                            st.session_state.persona_encontrada = df_persona.iloc[0]
                            st.session_state.mostrar_confirmacion_persona = True
                        else:
                            st.error("❌ PERSONA NO AUTORIZADA")
                            st.session_state.persona_encontrada = None
            
            if st.session_state.persona_encontrada is not None and st.session_state.mostrar_confirmacion_persona:
                per = st.session_state.persona_encontrada
                
                # Verificar estado de autorización
                estado_aut = per.get('estado_autorizacion', 'AUTORIZADO')
                
                if estado_aut == "NO AUTORIZADO":
                    st.error("🚫 ¡ATENCIÓN! PERSONA NO AUTORIZADA - NO PERMITIR INGRESO")
                    st.write(f"**RUT:** {formatear_rut(per['rut'])}")
                    st.write(f"**Nombre:** {per['nombre']}")
                    st.write(f"**Depto:** {per['depto']}")
                    st.write(f"**Tipo:** {per['tipo']}")
                    if per['observaciones']:
                        st.warning(f"**Motivo:** {per['observaciones']}")
                    st.info("👮 Contactar al administrador o supervisor si intenta ingresar")
                    
                elif estado_aut == "RESTRINGIDO":
                    st.warning("⚠️ PERSONA RESTRINGIDA - VERIFICAR ANTES DE AUTORIZAR")
                    st.write(f"**RUT:** {formatear_rut(per['rut'])}")
                    st.write(f"**Nombre:** {per['nombre']}")
                    st.write(f"**Depto:** {per['depto']}")
                    st.write(f"**Tipo:** {per['tipo']}")
                    if per['observaciones']:
                        st.warning(f"**Restricción:** {per['observaciones']}")
                    
                    with st.form("confirmar_ingreso_persona"):
                        st.write(f"**Tipo Ingreso:** {tipo_ingreso_per}")
                        turno_per = determinar_turno()
                        st.caption(f"Turno: {turno_per}")
                        st.warning("⚠️ Confirmar solo si cumple con las restricciones indicadas")
                        confirmar_btn_per = st.form_submit_button("⚠️ AUTORIZAR EXCEPCIONALMENTE", type="secondary", use_container_width=True)
                        
                        if confirmar_btn_per:
                            registrar_ingreso("PERSONA", per['rut'], per['nombre'], per['depto'], nombre_guardia, turno_per, tipo_ingreso_per, f"RESTRINGIDO: {per.get('observaciones', '')}")
                            st.warning(f"⚠️ Ingreso EXCEPCIONAL de {per['nombre']} registrado")
                            st.session_state.persona_encontrada = None
                            st.session_state.mostrar_confirmacion_persona = False
                            st.rerun()
                
                else:  # AUTORIZADO
                    st.success("✅ PERSONA AUTORIZADA")
                    st.write(f"**RUT:** {formatear_rut(per['rut'])}")
                    st.write(f"**Nombre:** {per['nombre']}")
                    st.write(f"**Depto:** {per['depto']}")
                    st.write(f"**Tipo:** {per['tipo']}")
                    
                    with st.form("confirmar_ingreso_persona"):
                        st.write(f"**Tipo Ingreso:** {tipo_ingreso_per}")
                        turno_per = determinar_turno()
                        st.caption(f"Turno: {turno_per}")
                        confirmar_btn_per = st.form_submit_button("✅ CONFIRMAR INGRESO", type="primary", use_container_width=True)
                        
                        if confirmar_btn_per:
                            registrar_ingreso("PERSONA", per['rut'], per['nombre'], per['depto'], nombre_guardia, turno_per, tipo_ingreso_per)
                            st.success(f"✅ Ingreso de {per['nombre']} registrado correctamente")
                            st.balloons()
                            st.session_state.persona_encontrada = None
                            st.session_state.mostrar_confirmacion_persona = False
                            st.rerun()
                
                if st.button("🔄 NUEVA BÚSQUEDA", key="nueva_busqueda_per"):
                    st.session_state.persona_encontrada = None
                    st.session_state.mostrar_confirmacion_persona = False
                    st.rerun()

# TAB 2: VEHÍCULOS
with tab2:
    st.header("🚗 Gestión de Vehículos")
    
    with st.expander("➕ Agregar Vehículo Nuevo", expanded=False):
        with st.form("agregar_vehiculo_form"):
            col1, col2 = st.columns(2)
            with col1:
                nueva_patente = st.text_input("Patente *", max_chars=8).upper()
                propietario = st.text_input("Propietario *").upper()
                rut_veh = st.text_input("RUT del Propietario (sin puntos, con guión)", max_chars=12, placeholder="18311040-3", help="Ejemplo: 18311040-3").upper()
                depto = st.text_input("Departamento/Unidad")
            with col2:
                marca = st.text_input("Marca")
                modelo = st.text_input("Modelo")
                color = st.text_input("Color")
                telefono = st.text_input("Teléfono")
            
            # Estado de autorización
            estado_autorizacion_veh = st.selectbox(
                "Estado de Autorización *",
                ["AUTORIZADO", "NO AUTORIZADO", "RESTRINGIDO"],
                help="AUTORIZADO: Puede ingresar | NO AUTORIZADO: No puede ingresar | RESTRINGIDO: Requiere verificación adicional"
            )
            
            observaciones_veh = st.text_area("Observaciones (obligatorio para NO AUTORIZADO o RESTRINGIDO)" if estado_autorizacion_veh != "AUTORIZADO" else "Observaciones")
            
            submitted = st.form_submit_button("💾 GUARDAR VEHÍCULO", type="primary", use_container_width=True)
            if submitted:
                if not nueva_patente or not propietario:
                    st.error("❌ Debes completar los campos obligatorios (*)")
                elif not validar_patente(nueva_patente):
                    st.error("❌ Formato de patente inválido")
                elif rut_veh and not validar_rut(rut_veh):
                    st.error("❌ RUT inválido. Formato correcto: 18311040-3 (sin puntos, con guión y dígito verificador)")
                elif estado_autorizacion_veh != "AUTORIZADO" and not observaciones_veh:
                    st.error("❌ Debes indicar el motivo en Observaciones para vehículos NO AUTORIZADOS o RESTRINGIDOS")
                else:
                    exito, mensaje = agregar_vehiculo(nueva_patente, propietario, rut_veh, depto, marca, modelo, color, telefono, estado_autorizacion_veh, observaciones_veh)
                    if exito:
                        if estado_autorizacion_veh == "NO AUTORIZADO":
                            st.warning(f"⚠️ {mensaje} - Estado: NO AUTORIZADO")
                        elif estado_autorizacion_veh == "RESTRINGIDO":
                            st.warning(f"⚠️ {mensaje} - Estado: RESTRINGIDO")
                        else:
                            st.success(f"✅ {mensaje}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ {mensaje}")
    
    st.subheader("📋 Vehículos Autorizados")
    vista_veh = st.radio("Mostrar:", ["✅ Solo Activos", "📋 Todos"], horizontal=True, key="vista_vehiculos")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_patente = st.text_input("🔎 Filtrar por Patente", key="filtro_patente")
    with col2:
        filtro_depto = st.text_input("🔎 Filtrar por Depto", key="filtro_depto")
    with col3:
        filtro_propietario = st.text_input("🔎 Filtrar por Propietario", key="filtro_propietario")
    
    df_veh = obtener_vehiculos() if vista_veh == "✅ Solo Activos" else obtener_todos_vehiculos()
    if vista_veh == "✅ Solo Activos":
        df_veh['activo'] = 1
    
    if not df_veh.empty:
        if filtro_patente:
            df_veh = df_veh[df_veh['patente'].str.contains(filtro_patente.upper(), na=False)]
        if filtro_depto:
            df_veh = df_veh[df_veh['depto'].str.contains(filtro_depto, na=False, case=False)]
        if filtro_propietario:
            df_veh = df_veh[df_veh['propietario'].str.contains(filtro_propietario, na=False, case=False)]
        
        if df_veh.empty:
            st.warning("🔍 No se encontraron vehículos")
        else:
            st.success(f"📊 Mostrando {len(df_veh)} vehículo(s)")
            for idx, row in df_veh.iterrows():
                col_info, col_actions = st.columns([4, 1])
                with col_info:
                    estado = "✅" if row['activo'] == 1 else "❌"
                    
                    # Estado de autorización con colores
                    estado_aut = row.get('estado_autorizacion', 'AUTORIZADO')
                    if estado_aut == "NO AUTORIZADO":
                        badge_aut = "🚫 NO AUTORIZADO"
                        color_fondo = "background-color: #8B0000; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;"
                    elif estado_aut == "RESTRINGIDO":
                        badge_aut = "⚠️ RESTRINGIDO"
                        color_fondo = "background-color: #FF8C00; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;"
                    else:
                        badge_aut = "✅ AUTORIZADO"
                        color_fondo = "background-color: #006400; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;"
                    
                    rut_display = f"RUT: {formatear_rut(row['rut'])}" if row.get('rut') and row['rut'] else ""
                    st.markdown(f"{estado} **{row['patente']}** - {row['propietario']} {rut_display}")
                    st.markdown(f"<span style='{color_fondo}'>{badge_aut}</span>", unsafe_allow_html=True)
                    st.caption(f"Depto: {row['depto']} | 📱 {row['telefono'] if row['telefono'] else 'Sin teléfono'} | 🚗 {row['marca']} {row['modelo']} ({row['color']})")
                    if row['observaciones']:
                        st.caption(f"💬 {row['observaciones']}")
                
                with col_actions:
                    if row['activo'] == 1:
                        if st.button("🗑️", key=f"del_veh_{row['id']}", use_container_width=True):
                            desactivar_vehiculo(row['id'])
                            st.rerun()
                    else:
                        if st.button("♻️", key=f"reac_veh_{row['id']}", use_container_width=True):
                            reactivar_vehiculo(row['id'])
                            st.rerun()
                st.divider()
            
            csv = df_veh[['patente', 'propietario', 'rut', 'depto', 'marca', 'modelo']].to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar CSV", csv, f"vehiculos_{datetime.now(CHILE_TZ).strftime('%Y%m%d')}.csv", "text/csv")
    else:
        st.info("📝 No hay vehículos registrados")

# TAB 3: PERSONAS
with tab3:
    st.header("👤 Gestión de Personas")
    
    with st.expander("➕ Agregar Persona Nueva", expanded=False):
        with st.form("agregar_persona_form"):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_rut = st.text_input("RUT *", max_chars=12, placeholder="12345678-9").upper()
                nombre_per = st.text_input("Nombre Completo *").upper()
                depto_per = st.text_input("Departamento/Unidad")
            with col2:
                telefono_per = st.text_input("Teléfono")
                tipo_per = st.selectbox("Tipo *", ["Residente", "Servicio", "Proveedor", "Otro"])
            
            # Estado de autorización
            estado_autorizacion_per = st.selectbox(
                "Estado de Autorización *",
                ["AUTORIZADO", "NO AUTORIZADO", "RESTRINGIDO"],
                help="AUTORIZADO: Puede ingresar | NO AUTORIZADO: No puede ingresar | RESTRINGIDO: Requiere verificación adicional"
            )
            
            observaciones_per = st.text_area("Observaciones (obligatorio para NO AUTORIZADO o RESTRINGIDO)" if estado_autorizacion_per != "AUTORIZADO" else "Observaciones")
            
            submitted_per = st.form_submit_button("💾 GUARDAR PERSONA", type="primary", use_container_width=True)
            if submitted_per:
                if not nuevo_rut or not nombre_per or not tipo_per:
                    st.error("❌ Debes completar los campos obligatorios (*)")
                elif not validar_rut(nuevo_rut):
                    st.error("❌ RUT inválido")
                elif estado_autorizacion_per != "AUTORIZADO" and not observaciones_per:
                    st.error("❌ Debes indicar el motivo en Observaciones para personas NO AUTORIZADAS o RESTRINGIDAS")
                else:
                    exito, mensaje = agregar_persona(nuevo_rut, nombre_per, depto_per, telefono_per, tipo_per, estado_autorizacion_per, observaciones_per)
                    if exito:
                        if estado_autorizacion_per == "NO AUTORIZADO":
                            st.warning(f"⚠️ {mensaje} - Estado: NO AUTORIZADO")
                        elif estado_autorizacion_per == "RESTRINGIDO":
                            st.warning(f"⚠️ {mensaje} - Estado: RESTRINGIDO")
                        else:
                            st.success(f"✅ {mensaje}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ {mensaje}")
    
    st.subheader("📋 Personas Autorizadas")
    vista_per = st.radio("Mostrar:", ["✅ Solo Activos", "📋 Todos"], horizontal=True, key="vista_personas")
    
    df_per = obtener_personas() if vista_per == "✅ Solo Activos" else obtener_todas_personas()
    if vista_per == "✅ Solo Activos":
        df_per['activo'] = 1
    
    if not df_per.empty:
        st.success(f"📊 Mostrando {len(df_per)} persona(s)")
        for idx, row in df_per.iterrows():
            col_info, col_actions = st.columns([4, 1])
            with col_info:
                estado = "✅" if row['activo'] == 1 else "❌"
                
                # Estado de autorización con colores
                estado_aut = row.get('estado_autorizacion', 'AUTORIZADO')
                if estado_aut == "NO AUTORIZADO":
                    badge_aut = "🚫 NO AUTORIZADO"
                    color_fondo = "background-color: #8B0000; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;"
                elif estado_aut == "RESTRINGIDO":
                    badge_aut = "⚠️ RESTRINGIDO"
                    color_fondo = "background-color: #FF8C00; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;"
                else:
                    badge_aut = "✅ AUTORIZADO"
                    color_fondo = "background-color: #006400; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;"
                
                st.markdown(f"{estado} **{formatear_rut(row['rut'])}** - {row['nombre']}")
                st.markdown(f"<span style='{color_fondo}'>{badge_aut}</span>", unsafe_allow_html=True)
                st.caption(f"Depto: {row['depto']} | 📱 {row['telefono'] if row['telefono'] else 'Sin teléfono'} | Tipo: {row['tipo']}")
                if row['observaciones']:
                    st.caption(f"💬 {row['observaciones']}")
            
            with col_actions:
                if row['activo'] == 1:
                    if st.button("🗑️", key=f"del_per_{row['id']}", use_container_width=True):
                        desactivar_persona(row['id'])
                        st.rerun()
                else:
                    if st.button("♻️", key=f"reac_per_{row['id']}", use_container_width=True):
                        reactivar_persona(row['id'])
                        st.rerun()
            st.divider()
        
        csv = df_per[['rut', 'nombre', 'depto', 'telefono', 'tipo']].to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, f"personas_{datetime.now(CHILE_TZ).strftime('%Y%m%d')}.csv", "text/csv")
    else:
        st.info("📝 No hay personas registradas")

# TAB 4: GUARDIAS
with tab4:
    st.header("👮 Gestión de Guardias")
    
    # Agregar guardia nuevo (siempre visible)
    with st.expander("➕ Agregar Guardia Nuevo", expanded=False):
        with st.form("agregar_guardia_form"):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_guardia = st.text_input("Nombre del Guardia *").upper()
            with col2:
                tel_guardia = st.text_input("Teléfono")
            
            submitted_guar = st.form_submit_button("💾 AGREGAR GUARDIA", type="primary", use_container_width=True)
            if submitted_guar:
                if not nuevo_guardia:
                    st.error("❌ Debes ingresar el nombre del guardia")
                else:
                    exito, mensaje = agregar_guardia(nuevo_guardia, tel_guardia)
                    if exito:
                        st.success(f"✅ {mensaje}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ {mensaje}")
    
    st.divider()
    
    # Lista de guardias (en expander que se puede reabrir)
    with st.expander("📋 Ver Lista de Guardias", expanded=True):
        df_guardias = obtener_todos_guardias()
        
        if not df_guardias.empty:
            activos = df_guardias[df_guardias['activo'] == 1]
            inactivos = df_guardias[df_guardias['activo'] == 0]
            
            st.success(f"✅ Activos ({len(activos)})")
            for idx, row in activos.iterrows():
                col_info, col_actions = st.columns([4, 1])
                with col_info:
                    tel = row['telefono'] if row['telefono'] else "Sin teléfono"
                    st.write(f"✅ **{row['nombre']}**")
                    st.caption(f"📱 {tel}")
                with col_actions:
                    if st.button("❌", key=f"deact_guar_{row['id']}", use_container_width=True):
                        desactivar_guardia(row['id'])
                        st.rerun()
                st.divider()
            
            if not inactivos.empty:
                st.warning(f"❌ Inactivos ({len(inactivos)})")
                for idx, row in inactivos.iterrows():
                    col_info, col_actions = st.columns([4, 1])
                    with col_info:
                        st.write(f"❌ **{row['nombre']}**")
                    with col_actions:
                        if st.button("✅", key=f"react_guar_{row['id']}", use_container_width=True):
                            reactivar_guardia(row['id'])
                            st.rerun()
                    st.divider()
        else:
            st.info("No hay guardias registrados")

# TAB 5: REGISTROS
with tab5:
    st.header("📈 Registros de Ingresos")
    periodo = st.radio("Selecciona período:", ["📅 Hoy", "🔍 Rango Personalizado"], horizontal=True)
    st.divider()
    
    if periodo == "📅 Hoy":
        st.subheader(f"Ingresos de Hoy - {datetime.now(CHILE_TZ).strftime('%d/%m/%Y')}")
        df_registros = obtener_registros_hoy()
        
        if not df_registros.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total", len(df_registros))
            with col2:
                vehiculos = len(df_registros[df_registros['tipo_registro'] == 'VEHICULO'])
                st.metric("🚗 Vehículos", vehiculos)
            with col3:
                personas = len(df_registros[df_registros['tipo_registro'] == 'PERSONA'])
                st.metric("👤 Personas", personas)
            with col4:
                dia_count = len(df_registros[df_registros['turno'].str.contains('Día', na=False)])
                st.metric("☀️ Turno Día", dia_count)
            
            st.divider()
            st.dataframe(df_registros, use_container_width=True, hide_index=True)
            
            csv = df_registros.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar CSV", csv, f"registros_{datetime.now(CHILE_TZ).strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.info("No hay registros para hoy")
    
    else:
        st.subheader("🔍 Selecciona Rango de Fechas")
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha Inicio", value=datetime.now(CHILE_TZ) - timedelta(days=7), max_value=datetime.now(CHILE_TZ))
        with col2:
            fecha_fin = st.date_input("Fecha Fin", value=datetime.now(CHILE_TZ), max_value=datetime.now(CHILE_TZ))
        
        if fecha_inicio > fecha_fin:
            st.error("❌ La fecha de inicio debe ser anterior a la fecha de fin")
        else:
            df_rango = obtener_registros_rango_fechas(fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d'))
            
            if not df_rango.empty:
                st.success(f"📊 {len(df_rango)} registros encontrados")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Ingresos", len(df_rango))
                with col2:
                    vehiculos = len(df_rango[df_rango['tipo_registro'] == 'VEHICULO'])
                    st.metric("🚗 Vehículos", vehiculos)
                with col3:
                    personas = len(df_rango[df_rango['tipo_registro'] == 'PERSONA'])
                    st.metric("👤 Personas", personas)
                
                st.divider()
                st.dataframe(df_rango, use_container_width=True, hide_index=True)
                
                csv = df_rango.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar CSV", csv, f"registros_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.csv", "text/csv")
            else:
                st.info("No hay registros en el rango seleccionado")

st.divider()
st.markdown('<div style="text-align: center; color: gray;"><p>Sistema de Control de Acceso v3.0 | Desarrollado por Simatec S.A.</p></div>', unsafe_allow_html=True)
