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
        'About': "Control de Acceso Integral v3.0\nDesarrollado por Simatec S.A."
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
    
    /* Hacer el botón del sidebar más visible */
    button[kind="header"] {
        background-color: #FF4B4B !important;
        color: white !important;
        font-size: 20px !important;
        padding: 10px !important;
        border-radius: 5px !important;
    }
    
    /* Asegurar que el toggle del sidebar sea visible */
    [data-testid="collapsedControl"] {
        background-color: #FF4B4B !important;
        color: white !important;
        font-size: 24px !important;
        padding: 15px !important;
        margin: 10px !important;
        border: 2px solid white !important;
        border-radius: 8px !important;
    }
    </style>
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
        propietario TEXT NOT NULL, depto TEXT, marca TEXT, modelo TEXT, color TEXT,
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
    rut = rut.replace(".", "").replace("-", "").upper()
    if len(rut) < 2:
        return False
    rut_num, dv = rut[:-1], rut[-1]
    if not rut_num.isdigit():
        return False
    suma, multiplo = 0, 2
    for r in reversed(rut_num):
        suma += int(r) * multiplo
        multiplo = 8 if multiplo == 7 else multiplo + 1
    dvr = 11 - (suma % 11)
    dvr = '0' if dvr == 11 else 'K' if dvr == 10 else str(dvr)
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

def agregar_persona(rut, nombre, depto, telefono, tipo, observaciones=""):
    try:
        conn = sqlite3.connect('control_acceso.db')
        c = conn.cursor()
        fecha_registro_chile = datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''INSERT INTO personas (rut, nombre, depto, telefono, tipo, fecha_registro, observaciones)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (rut.upper(), nombre.upper(), depto, telefono, tipo, fecha_registro_chile, observaciones))
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

def agregar_vehiculo(patente, propietario, depto, marca="", modelo="", color="", telefono="", observaciones=""):
    try:
        conn = sqlite3.connect('control_acceso.db')
        c = conn.cursor()
        fecha_registro_chile = datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''INSERT INTO vehiculos (patente, propietario, depto, marca, modelo, color, telefono, fecha_registro, observaciones)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (patente.upper(), propietario.upper(), depto, marca, modelo, color, telefono, fecha_registro_chile, observaciones))
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

# Mensaje de ayuda si no hay guardia seleccionado
if 'guardia_select' not in st.session_state or not st.session_state.get('guardia_select'):
    st.error("👈 **¡IMPORTANTE!** Para usar la aplicación, necesitas abrir el panel lateral izquierdo")
    
    # Instrucciones más claras
    st.markdown("""
    <div style='background-color: #FFF3CD; padding: 20px; border-radius: 10px; border: 2px solid #FF4B4B;'>
        <h2 style='color: #856404;'>🔑 ATAJO DE TECLADO: Presiona la tecla <code>[</code></h2>
        <h3 style='color: #856404;'>O busca arriba a la IZQUIERDA un botón rojo ☰ o ></h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.info("""
        ### 💡 Formas de abrir el panel:
        
        **1. TECLADO:** Presiona **`[`** (corchete izquierdo)
        
        **2. MOUSE:** Click en el botón arriba a la izquierda
        
        **3. CELULAR:** Toca el icono de menú (☰)
        """)
    
    with col2:
        st.warning("""
        ### 📋 Después de abrirlo:
        
        1. ✅ Verás "👤 Guardia en Turno"
        2. ✅ Selecciona tu nombre
        3. ✅ Aparecerá el turno automático
        4. ✅ ¡Ya puedes trabajar!
        """)
    
    st.markdown("---")
    st.success("💡 **TIP:** Si no ves el botón para abrir el panel, presiona la tecla **`[`** en tu teclado")

st.divider()

# SIDEBAR
with st.sidebar:
    st.header("👤 Guardia en Turno")
    guardias_disponibles = obtener_guardias_activos()
    
    if guardias_disponibles:
        nombre_guardia = st.selectbox("Seleccionar Guardia", options=[""] + guardias_disponibles, key="guardia_select")
    else:
        st.warning("⚠️ No hay guardias registrados")
        nombre_guardia = st.text_input("Nombre del Guardia", key="guardia_nombre_manual")
    
    if not nombre_guardia:
        st.warning("⚠️ Selecciona un guardia para continuar")
    else:
        turno_actual = determinar_turno()
        st.success(f"✅ Guardia: {nombre_guardia}")
        st.info(f"{'☀️' if 'Día' in turno_actual else '🌙'} {turno_actual}")
    
    st.divider()
    hora_actual = datetime.now(CHILE_TZ).strftime('%H:%M:%S')
    fecha_actual = datetime.now(CHILE_TZ).strftime('%d/%m/%Y')
    st.info(f"🕐 **Hora Chile:** {hora_actual}")
    st.caption(f"📅 {fecha_actual}")
    
    auto_refresh = st.checkbox("🔄 Actualización automática (30s)", value=st.session_state.auto_refresh)
    if auto_refresh != st.session_state.auto_refresh:
        st.session_state.auto_refresh = auto_refresh
        st.session_state.last_refresh_time = datetime.now(CHILE_TZ)
    
    st.divider()
    st.subheader("📊 Resumen del Día")
    df_hoy = obtener_registros_hoy()
    
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("Ingresos", len(df_hoy))
    with col_stat2:
        if not df_hoy.empty:
            vehiculos_hoy = len(df_hoy[df_hoy['tipo_registro'] == 'VEHICULO'])
            personas_hoy = len(df_hoy[df_hoy['tipo_registro'] == 'PERSONA'])
            st.metric("🚗 Veh", vehiculos_hoy)
            st.metric("👤 Per", personas_hoy)
    
    df_vehiculos = obtener_vehiculos()
    df_personas = obtener_personas()
    st.metric("Autorizados", len(df_vehiculos) + len(df_personas))

# TABS
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Validar Entrada", "🚗 Vehículos", "👤 Personas", "👮 Guardias", "📈 Registros"])

# TAB 1: VALIDAR ENTRADA
with tab1:
    st.header("🔍 Validación de Entrada")
    
    if not nombre_guardia:
        st.warning("⚠️ **IMPORTANTE:** Debes seleccionar un guardia en el panel lateral izquierdo (sidebar) para continuar")
        st.info("👈 **Mira a la izquierda** → Abre el panel lateral (sidebar) si está cerrado y selecciona tu nombre de la lista")
        
        # Botón de ayuda visual
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            ### 📋 Pasos para empezar:
            1. 👈 Abre el **panel lateral izquierdo** (sidebar)
            2. 👤 Selecciona tu **nombre** de la lista de guardias
            3. ✅ El turno se detectará automáticamente
            4. 🚀 ¡Listo! Ya puedes validar entradas
            """)
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
                depto = st.text_input("Departamento/Unidad")
                marca = st.text_input("Marca")
            with col2:
                modelo = st.text_input("Modelo")
                color = st.text_input("Color")
                telefono = st.text_input("Teléfono")
                observaciones_veh = st.text_area("Observaciones")
            
            submitted = st.form_submit_button("💾 GUARDAR VEHÍCULO", type="primary", use_container_width=True)
            if submitted:
                if not nueva_patente or not propietario:
                    st.error("❌ Debes completar los campos obligatorios (*)")
                elif not validar_patente(nueva_patente):
                    st.error("❌ Formato de patente inválido")
                else:
                    exito, mensaje = agregar_vehiculo(nueva_patente, propietario, depto, marca, modelo, color, telefono, observaciones_veh)
                    if exito:
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
                    st.markdown(f"{estado} **{row['patente']}** - {row['propietario']} (Depto: {row['depto']}) | 📱 {row['telefono'] if row['telefono'] else 'Sin teléfono'} | 🚗 {row['marca']} {row['modelo']} ({row['color']})")
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
            
            csv = df_veh[['patente', 'propietario', 'depto', 'marca', 'modelo']].to_csv(index=False).encode('utf-8')
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
                observaciones_per = st.text_area("Observaciones")
            
            submitted_per = st.form_submit_button("💾 GUARDAR PERSONA", type="primary", use_container_width=True)
            if submitted_per:
                if not nuevo_rut or not nombre_per or not tipo_per:
                    st.error("❌ Debes completar los campos obligatorios (*)")
                elif not validar_rut(nuevo_rut):
                    st.error("❌ RUT inválido")
                else:
                    exito, mensaje = agregar_persona(nuevo_rut, nombre_per, depto_per, telefono_per, tipo_per, observaciones_per)
                    if exito:
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
                st.markdown(f"{estado} **{formatear_rut(row['rut'])}** - {row['nombre']} (Depto: {row['depto']}) | 📱 {row['telefono'] if row['telefono'] else 'Sin teléfono'} | Tipo: {row['tipo']}")
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
st.markdown('<div style="text-align: center; color: gray;"><p>Sistema de Control de Acceso v3.0 | Desarrollado por ´Simatec S.A .</p></div>', unsafe_allow_html=True)
