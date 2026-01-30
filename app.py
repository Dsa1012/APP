import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import re
import pytz

# Configurar zona horaria de Chile
CHILE_TZ = pytz.timezone('America/Santiago')

# Configuración de la página
st.set_page_config(
    page_title="Control de Acceso Vehicular",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Sistema de Control de Acceso Vehicular v2.0\nDesarrollado para Guardias de Seguridad"
    }
)

# CSS personalizado
st.markdown("""
    <style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .stAlert {
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# Funciones de base de datos
def init_db():
    """Inicializa la base de datos SQLite"""
    conn = sqlite3.connect('vehiculos_autorizados.db')
    c = conn.cursor()
    
    # Tabla de vehículos autorizados
    c.execute('''
        CREATE TABLE IF NOT EXISTS vehiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patente TEXT UNIQUE NOT NULL,
            propietario TEXT NOT NULL,
            depto TEXT,
            marca TEXT,
            modelo TEXT,
            color TEXT,
            telefono TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activo INTEGER DEFAULT 1,
            observaciones TEXT
        )
    ''')
    
    # Tabla de registro de ingresos
    c.execute('''
        CREATE TABLE IF NOT EXISTS registro_ingresos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patente TEXT NOT NULL,
            fecha_hora TEXT NOT NULL,
            guardia TEXT NOT NULL,
            tipo_ingreso TEXT,
            FOREIGN KEY (patente) REFERENCES vehiculos (patente)
        )
    ''')
    
    conn.commit()
    conn.close()

def validar_patente(patente):
    """Valida formato de patente chilena"""
    # Formato antiguo: AA-BB-11 o Formato nuevo: AA-AA-11
    patron1 = r'^[A-Z]{2}-[A-Z]{2}-\d{2}$'  # Nuevo
    patron2 = r'^[A-Z]{4}\d{2}$'  # Nuevo sin guiones
    patron3 = r'^[A-Z]{2}-\d{2}-\d{2}$'  # Antiguo
    patron4 = r'^[A-Z]{2}\d{4}$'  # Antiguo sin guiones
    
    patente_upper = patente.upper().replace(" ", "")
    
    return (re.match(patron1, patente_upper) or 
            re.match(patron2, patente_upper) or
            re.match(patron3, patente_upper) or
            re.match(patron4, patente_upper))

def agregar_vehiculo(patente, propietario, depto, marca, modelo, color, telefono, observaciones):
    """Agrega un nuevo vehículo autorizado"""
    try:
        conn = sqlite3.connect('vehiculos_autorizados.db')
        c = conn.cursor()
        
        patente_clean = patente.upper().replace(" ", "")
        
        c.execute('''
            INSERT INTO vehiculos (patente, propietario, depto, marca, modelo, color, telefono, observaciones)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (patente_clean, propietario, depto, marca, modelo, color, telefono, observaciones))
        
        conn.commit()
        conn.close()
        return True, "Vehículo agregado exitosamente"
    except sqlite3.IntegrityError:
        return False, "Esta patente ya está registrada"
    except Exception as e:
        return False, f"Error: {str(e)}"

def buscar_vehiculo(patente):
    """Busca un vehículo por patente"""
    conn = sqlite3.connect('vehiculos_autorizados.db')
    c = conn.cursor()
    
    patente_clean = patente.upper().replace(" ", "")
    
    c.execute('''
        SELECT * FROM vehiculos 
        WHERE patente = ? AND activo = 1
    ''', (patente_clean,))
    
    resultado = c.fetchone()
    conn.close()
    
    return resultado

def registrar_ingreso(patente, guardia, tipo_ingreso):
    """Registra un ingreso de vehículo"""
    try:
        conn = sqlite3.connect('vehiculos_autorizados.db')
        c = conn.cursor()
        
        patente_clean = patente.upper().replace(" ", "")
        
        # Obtener hora actual de Chile
        fecha_hora_chile = datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        c.execute('''
            INSERT INTO registro_ingresos (patente, guardia, tipo_ingreso, fecha_hora)
            VALUES (?, ?, ?, ?)
        ''', (patente_clean, guardia, tipo_ingreso, fecha_hora_chile))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def obtener_vehiculos():
    """Obtiene todos los vehículos activos"""
    conn = sqlite3.connect('vehiculos_autorizados.db')
    df = pd.read_sql_query('''
        SELECT id, patente, propietario, depto, marca, modelo, color, 
               telefono, fecha_registro, observaciones
        FROM vehiculos 
        WHERE activo = 1
        ORDER BY fecha_registro DESC
    ''', conn)
    conn.close()
    return df

def obtener_registros_hoy():
    """Obtiene los registros de ingreso del día"""
    # Obtener fecha actual de Chile
    fecha_hoy_chile = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('vehiculos_autorizados.db')
    df = pd.read_sql_query('''
        SELECT r.patente, r.fecha_hora, r.guardia, r.tipo_ingreso, 
               v.propietario, v.depto
        FROM registro_ingresos r
        LEFT JOIN vehiculos v ON r.patente = v.patente
        WHERE DATE(r.fecha_hora) = ?
        ORDER BY r.fecha_hora DESC
    ''', conn, params=[fecha_hoy_chile])
    conn.close()
    return df

def desactivar_vehiculo(vehiculo_id):
    """Desactiva un vehículo (borrado lógico)"""
    conn = sqlite3.connect('vehiculos_autorizados.db')
    c = conn.cursor()
    c.execute('UPDATE vehiculos SET activo = 0 WHERE id = ?', (vehiculo_id,))
    conn.commit()
    conn.close()

def reactivar_vehiculo(vehiculo_id):
    """Reactiva un vehículo previamente desactivado"""
    conn = sqlite3.connect('vehiculos_autorizados.db')
    c = conn.cursor()
    c.execute('UPDATE vehiculos SET activo = 1 WHERE id = ?', (vehiculo_id,))
    conn.commit()
    conn.close()

def obtener_todos_vehiculos():
    """Obtiene todos los vehículos (activos e inactivos)"""
    conn = sqlite3.connect('vehiculos_autorizados.db')
    df = pd.read_sql_query('''
        SELECT id, patente, propietario, depto, marca, modelo, color, 
               telefono, fecha_registro, observaciones, activo
        FROM vehiculos 
        ORDER BY activo DESC, fecha_registro DESC
    ''', conn)
    conn.close()
    return df

def obtener_registros_rango_fechas(fecha_inicio, fecha_fin):
    """Obtiene registros entre dos fechas"""
    conn = sqlite3.connect('vehiculos_autorizados.db')
    df = pd.read_sql_query('''
        SELECT r.patente, r.fecha_hora, r.guardia, r.tipo_ingreso, 
               v.propietario, v.depto
        FROM registro_ingresos r
        LEFT JOIN vehiculos v ON r.patente = v.patente
        WHERE DATE(r.fecha_hora) BETWEEN ? AND ?
        ORDER BY r.fecha_hora DESC
    ''', conn, params=[fecha_inicio, fecha_fin])
    conn.close()
    return df

def obtener_estadisticas_periodo(dias=7):
    """Obtiene estadísticas de los últimos N días"""
    fecha_fin = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
    fecha_inicio = (datetime.now(CHILE_TZ) - pd.Timedelta(days=dias-1)).strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('vehiculos_autorizados.db')
    
    # Total de ingresos
    df_total = pd.read_sql_query('''
        SELECT COUNT(*) as total
        FROM registro_ingresos
        WHERE DATE(fecha_hora) BETWEEN ? AND ?
    ''', conn, params=[fecha_inicio, fecha_fin])
    
    # Ingresos por día
    df_por_dia = pd.read_sql_query('''
        SELECT DATE(fecha_hora) as fecha, COUNT(*) as cantidad
        FROM registro_ingresos
        WHERE DATE(fecha_hora) BETWEEN ? AND ?
        GROUP BY DATE(fecha_hora)
        ORDER BY fecha
    ''', conn, params=[fecha_inicio, fecha_fin])
    
    # Vehículos más frecuentes
    df_vehiculos = pd.read_sql_query('''
        SELECT r.patente, v.propietario, v.depto, COUNT(*) as cantidad
        FROM registro_ingresos r
        LEFT JOIN vehiculos v ON r.patente = v.patente
        WHERE DATE(r.fecha_hora) BETWEEN ? AND ?
        GROUP BY r.patente
        ORDER BY cantidad DESC
        LIMIT 10
    ''', conn, params=[fecha_inicio, fecha_fin])
    
    # Horarios pico
    df_horarios = pd.read_sql_query('''
        SELECT 
            CAST(strftime('%H', fecha_hora) AS INTEGER) as hora,
            COUNT(*) as cantidad
        FROM registro_ingresos
        WHERE DATE(fecha_hora) BETWEEN ? AND ?
        GROUP BY hora
        ORDER BY hora
    ''', conn, params=[fecha_inicio, fecha_fin])
    
    conn.close()
    
    return {
        'total': df_total['total'].iloc[0] if not df_total.empty else 0,
        'por_dia': df_por_dia,
        'vehiculos': df_vehiculos,
        'horarios': df_horarios,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    }

# Inicializar base de datos
init_db()

# Inicializar session_state
if 'vehiculo_encontrado' not in st.session_state:
    st.session_state.vehiculo_encontrado = None
if 'mostrar_confirmacion' not in st.session_state:
    st.session_state.mostrar_confirmacion = False
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = datetime.now(CHILE_TZ)

# Auto-refresh cada 30 segundos (solo si está habilitado)
if st.session_state.auto_refresh:
    tiempo_transcurrido = (datetime.now(CHILE_TZ) - st.session_state.last_refresh_time).total_seconds()
    if tiempo_transcurrido > 30:
        st.session_state.last_refresh_time = datetime.now(CHILE_TZ)
        st.rerun()

# Título principal
st.markdown('<p class="big-font">🚗 Control de Acceso Vehicular</p>', unsafe_allow_html=True)
st.markdown("### Sistema para Guardias de Seguridad - Condominio")

# Sidebar para login
with st.sidebar:
    st.header("👤 Guardia en Turno")
    nombre_guardia = st.text_input("Nombre del Guardia", key="guardia_nombre")
    
    if not nombre_guardia:
        st.warning("⚠️ Ingresa tu nombre para continuar")
    else:
        st.success(f"✅ Turno: {nombre_guardia}")
    
    st.divider()
    
    # Hora actual de Chile con auto-refresh
    hora_actual = datetime.now(CHILE_TZ).strftime('%H:%M:%S')
    fecha_actual = datetime.now(CHILE_TZ).strftime('%d/%m/%Y')
    st.info(f"🕐 **Hora Chile:** {hora_actual}")
    st.caption(f"📅 {fecha_actual}")
    
    # Toggle de auto-refresh
    auto_refresh = st.checkbox(
        "🔄 Actualización automática (30s)", 
        value=st.session_state.auto_refresh,
        help="Actualiza la hora y estadísticas cada 30 segundos"
    )
    if auto_refresh != st.session_state.auto_refresh:
        st.session_state.auto_refresh = auto_refresh
        st.session_state.last_refresh_time = datetime.now(CHILE_TZ)
    
    st.divider()
    
    # Estadísticas del día
    st.subheader("📊 Resumen del Día")
    df_hoy = obtener_registros_hoy()
    
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("Ingresos", len(df_hoy))
    with col_stat2:
        # Calcular cambio respecto a ayer
        fecha_ayer = (datetime.now(CHILE_TZ) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        df_ayer = obtener_registros_rango_fechas(fecha_ayer, fecha_ayer)
        delta = len(df_hoy) - len(df_ayer)
        st.metric("vs Ayer", f"{delta:+d}", delta=delta)
    
    df_vehiculos = obtener_vehiculos()
    st.metric("Autorizados", len(df_vehiculos))


# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Validar Ingreso", "➕ Agregar Vehículo", "📋 Lista de Autorizados", "📈 Registro de Ingresos"])

# TAB 1: VALIDAR INGRESO
with tab1:
    st.header("🔍 Validar Ingreso de Vehículo")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        patente_buscar = st.text_input(
            "Ingresa la Patente del Vehículo",
            placeholder="Ej: BBBB22 o BB-BB-22",
            key="patente_buscar",
            help="Formatos válidos: BBBB22, BB-BB-22, BB-22-22"
        ).upper()
    
    with col2:
        st.write("")
        st.write("")
        buscar_btn = st.button("🔎 BUSCAR", type="primary", use_container_width=True)
    
    # Limpiar búsqueda anterior si se presiona buscar
    if buscar_btn:
        st.session_state.vehiculo_encontrado = None
        st.session_state.mostrar_confirmacion = False
        
        if not patente_buscar:
            st.warning("⚠️ Por favor ingresa una patente")
        elif not nombre_guardia:
            st.error("❌ Debes ingresar tu nombre como guardia primero")
        else:
            resultado = buscar_vehiculo(patente_buscar)
            if resultado:
                st.session_state.vehiculo_encontrado = resultado
                st.session_state.mostrar_confirmacion = True
            else:
                st.session_state.vehiculo_encontrado = None
                st.session_state.mostrar_confirmacion = False
    
    # Mostrar resultados si hay un vehículo encontrado
    if st.session_state.mostrar_confirmacion and st.session_state.vehiculo_encontrado:
        resultado = st.session_state.vehiculo_encontrado
        
        st.success("✅ VEHÍCULO AUTORIZADO - PUEDE INGRESAR")
        
        # Mostrar información del vehículo
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"**Patente:** {resultado[1]}")
            st.info(f"**Propietario:** {resultado[2]}")
            st.info(f"**Depto:** {resultado[3]}")
        
        with col2:
            st.info(f"**Marca:** {resultado[4]}")
            st.info(f"**Modelo:** {resultado[5]}")
            st.info(f"**Color:** {resultado[6]}")
        
        with col3:
            st.info(f"**Teléfono:** {resultado[7]}")
            if resultado[10]:
                st.warning(f"**Obs:** {resultado[10]}")
        
        st.divider()
        
        # Formulario de confirmación de ingreso
        with st.form("form_confirmar_ingreso", clear_on_submit=True):
            tipo_ingreso = st.selectbox(
                "Tipo de Ingreso", 
                ["Residente", "Visita", "Servicio"],
                key="tipo_ingreso_select"
            )
            
            col_a, col_b, col_c = st.columns([1, 1, 1])
            
            with col_b:
                confirmar_btn = st.form_submit_button(
                    "✅ CONFIRMAR INGRESO", 
                    type="primary", 
                    use_container_width=True
                )
            
            if confirmar_btn:
                if registrar_ingreso(resultado[1], nombre_guardia, tipo_ingreso):
                    hora_chile = datetime.now(CHILE_TZ).strftime('%H:%M:%S')
                    st.success(f"✅ Ingreso registrado a las {hora_chile}")
                    st.info(f"**Vehículo:** {resultado[1]} | **Tipo:** {tipo_ingreso}")
                    st.balloons()
                    # Limpiar el estado después de registrar
                    st.session_state.vehiculo_encontrado = None
                    st.session_state.mostrar_confirmacion = False
                    st.rerun()
                else:
                    st.error("Error al registrar ingreso")
        
        # Botón para nueva búsqueda
        if st.button("🔄 NUEVA BÚSQUEDA", use_container_width=True):
            st.session_state.vehiculo_encontrado = None
            st.session_state.mostrar_confirmacion = False
            st.rerun()
    
    elif buscar_btn and not st.session_state.vehiculo_encontrado:
        st.error("❌ VEHÍCULO NO AUTORIZADO")
        st.warning("⚠️ Este vehículo NO tiene permiso de ingreso al condominio")
        st.info("💡 Si debe ingresar, solicita autorización al administrador o agrega el vehículo.")

# TAB 2: AGREGAR VEHÍCULO
with tab2:
    st.header("➕ Agregar Nuevo Vehículo Autorizado")
    
    with st.form("form_agregar"):
        col1, col2 = st.columns(2)
        
        with col1:
            nueva_patente = st.text_input("Patente *", placeholder="BB-BB-22 o BBBB22")
            propietario = st.text_input("Nombre Propietario *", placeholder="Juan Pérez")
            depto = st.text_input("Depto/Casa *", placeholder="Ej: 101, Casa 5")
            marca = st.text_input("Marca", placeholder="Toyota, Chevrolet, etc.")
        
        with col2:
            modelo = st.text_input("Modelo", placeholder="Corolla, Spark, etc.")
            color = st.text_input("Color", placeholder="Blanco, Negro, etc.")
            telefono = st.text_input("Teléfono", placeholder="+56912345678")
            observaciones = st.text_area("Observaciones", placeholder="Notas adicionales...")
        
        submitted = st.form_submit_button("💾 GUARDAR VEHÍCULO", type="primary", use_container_width=True)
        
        if submitted:
            if not nueva_patente or not propietario or not depto:
                st.error("❌ Debes completar los campos obligatorios (*)")
            elif not validar_patente(nueva_patente):
                st.error("❌ Formato de patente inválido. Usa formato chileno: BB-BB-22 o BBBB22")
            else:
                exito, mensaje = agregar_vehiculo(
                    nueva_patente, propietario, depto, 
                    marca, modelo, color, telefono, observaciones
                )
                
                if exito:
                    st.success(f"✅ {mensaje}")
                    st.balloons()
                else:
                    st.error(f"❌ {mensaje}")

# TAB 3: LISTA DE AUTORIZADOS
with tab3:
    st.header("📋 Gestión de Vehículos Autorizados")
    
    # Selector de vista
    col_vista1, col_vista2 = st.columns([3, 1])
    
    with col_vista1:
        vista = st.radio(
            "Mostrar:",
            ["✅ Solo Activos", "📋 Todos (Activos e Inactivos)"],
            horizontal=True,
            key="vista_vehiculos"
        )
    
    with col_vista2:
        st.write("")
        st.write("")
    
    st.divider()
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_patente = st.text_input("🔎 Filtrar por Patente", key="filtro_patente")
    
    with col2:
        filtro_depto = st.text_input("🔎 Filtrar por Depto", key="filtro_depto")
    
    with col3:
        filtro_propietario = st.text_input("🔎 Filtrar por Propietario", key="filtro_propietario")
    
    st.divider()
    
    # Obtener datos según vista seleccionada
    if vista == "✅ Solo Activos":
        df = obtener_vehiculos()
        # Agregar columna 'activo' para mantener consistencia
        df['activo'] = 1
        mostrar_columna_estado = False
    else:
        df = obtener_todos_vehiculos()
        mostrar_columna_estado = True
    
    if not df.empty:
        # Aplicar filtros
        if filtro_patente:
            df = df[df['patente'].str.contains(filtro_patente.upper(), na=False)]
        if filtro_depto:
            df = df[df['depto'].str.contains(filtro_depto, na=False, case=False)]
        if filtro_propietario:
            df = df[df['propietario'].str.contains(filtro_propietario, na=False, case=False)]
        
        if df.empty:
            st.warning("🔍 No se encontraron vehículos con los filtros aplicados")
        else:
            st.success(f"📊 Mostrando {len(df)} vehículo(s)")
            
            # Mostrar tabla de vehículos con acciones
            for idx, row in df.iterrows():
                with st.container():
                    col_info, col_actions = st.columns([4, 1])
                    
                    with col_info:
                        # Indicador de estado
                        if row['activo'] == 1:
                            estado_emoji = "✅"
                            estado_color = "normal"
                        else:
                            estado_emoji = "❌"
                            estado_color = "inverse"
                        
                        # Mostrar información del vehículo
                        st.markdown(f"""
                        {estado_emoji} **{row['patente']}** - {row['propietario']} (Depto: {row['depto']})  
                        📱 {row['telefono'] if row['telefono'] else 'Sin teléfono'} | 
                        🚗 {row['marca']} {row['modelo']} ({row['color']})
                        """)
                        
                        if row['observaciones']:
                            st.caption(f"💬 {row['observaciones']}")
                    
                    with col_actions:
                        if row['activo'] == 1:
                            # Botón para desactivar
                            if st.button(
                                "🗑️ Eliminar", 
                                key=f"deactivate_{row['id']}", 
                                type="secondary",
                                use_container_width=True
                            ):
                                # Guardar en session state para confirmación
                                st.session_state[f'confirm_delete_{row["id"]}'] = True
                                st.rerun()
                            
                            # Mostrar confirmación si está en session state
                            if st.session_state.get(f'confirm_delete_{row["id"]}', False):
                                st.warning("⚠️ ¿Confirmar?")
                                col_si, col_no = st.columns(2)
                                
                                with col_si:
                                    if st.button("Sí", key=f"confirm_yes_{row['id']}", type="primary"):
                                        desactivar_vehiculo(row['id'])
                                        st.session_state[f'confirm_delete_{row["id"]}'] = False
                                        st.success(f"✅ Vehículo {row['patente']} eliminado")
                                        st.rerun()
                                
                                with col_no:
                                    if st.button("No", key=f"confirm_no_{row['id']}"):
                                        st.session_state[f'confirm_delete_{row["id"]}'] = False
                                        st.rerun()
                        else:
                            # Botón para reactivar
                            if st.button(
                                "♻️ Reactivar", 
                                key=f"reactivate_{row['id']}", 
                                type="primary",
                                use_container_width=True
                            ):
                                reactivar_vehiculo(row['id'])
                                st.success(f"✅ Vehículo {row['patente']} reactivado")
                                st.rerun()
                    
                    st.divider()
            
            # Botón de descarga
            st.subheader("📥 Exportar Datos")
            
            col_download1, col_download2 = st.columns(2)
            
            with col_download1:
                # Exportar solo activos
                df_activos = df[df['activo'] == 1] if mostrar_columna_estado else df
                if not df_activos.empty:
                    csv_activos = df_activos[['patente', 'propietario', 'depto', 'marca', 'modelo', 'color', 'telefono']].to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar Activos (CSV)",
                        data=csv_activos,
                        file_name=f"vehiculos_activos_{datetime.now(CHILE_TZ).strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            
            with col_download2:
                # Exportar todos
                if mostrar_columna_estado:
                    csv_todos = df[['patente', 'propietario', 'depto', 'marca', 'modelo', 'color', 'telefono', 'activo']].to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar Todos (CSV)",
                        data=csv_todos,
                        file_name=f"vehiculos_todos_{datetime.now(CHILE_TZ).strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
    else:
        st.info("📝 No hay vehículos registrados aún. Ve a la pestaña '➕ Agregar Vehículo' para empezar.")


# TAB 4: REGISTRO DE INGRESOS Y ESTADÍSTICAS
with tab4:
    st.header("📈 Registro de Ingresos y Estadísticas")
    
    # Selector de período
    periodo = st.radio(
        "Selecciona período:",
        ["📅 Hoy", "📊 Última Semana", "📆 Último Mes", "🔍 Rango Personalizado", "📈 Dashboard"],
        horizontal=True
    )
    
    st.divider()
    
    if periodo == "📅 Hoy":
        # Vista del día actual
        st.subheader(f"Ingresos de Hoy - {datetime.now(CHILE_TZ).strftime('%d/%m/%Y')}")
        
        df_ingresos = obtener_registros_hoy()
        
        if not df_ingresos.empty:
            # Métricas rápidas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Ingresos", len(df_ingresos))
            
            with col2:
                residentes = len(df_ingresos[df_ingresos['tipo_ingreso'] == 'Residente'])
                st.metric("Residentes", residentes)
            
            with col3:
                visitas = len(df_ingresos[df_ingresos['tipo_ingreso'] == 'Visita'])
                st.metric("Visitas", visitas)
            
            with col4:
                servicios = len(df_ingresos[df_ingresos['tipo_ingreso'] == 'Servicio'])
                st.metric("Servicios", servicios)
            
            st.divider()
            
            # Tabla de registros
            st.subheader("📋 Detalle de Ingresos")
            st.dataframe(
                df_ingresos,
                use_container_width=True,
                hide_index=True
            )
            
            # Gráfico de ingresos por hora
            st.subheader("📊 Ingresos por Hora")
            df_ingresos['hora'] = pd.to_datetime(df_ingresos['fecha_hora']).dt.hour
            ingresos_hora = df_ingresos.groupby('hora').size()
            st.bar_chart(ingresos_hora)
            
            # Exportar
            csv_hoy = df_ingresos.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Registros de Hoy (CSV)",
                data=csv_hoy,
                file_name=f"ingresos_{datetime.now(CHILE_TZ).strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No hay ingresos registrados hoy")
    
    elif periodo == "📊 Última Semana":
        # Vista de última semana
        st.subheader("📊 Estadísticas de los Últimos 7 Días")
        
        stats = obtener_estadisticas_periodo(7)
        
        # Métricas generales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Ingresos", stats['total'])
        
        with col2:
            promedio = stats['total'] / 7
            st.metric("Promedio Diario", f"{promedio:.1f}")
        
        with col3:
            if not stats['por_dia'].empty:
                dia_mas_activo = stats['por_dia'].loc[stats['por_dia']['cantidad'].idxmax()]
                fecha_formateada = pd.to_datetime(dia_mas_activo['fecha']).strftime('%d/%m')
                st.metric("Día Más Activo", f"{fecha_formateada} ({int(dia_mas_activo['cantidad'])})")
            else:
                st.metric("Día Más Activo", "N/A")
        
        st.divider()
        
        # Gráfico de ingresos por día
        if not stats['por_dia'].empty:
            st.subheader("📈 Tendencia Semanal")
            stats['por_dia']['fecha'] = pd.to_datetime(stats['por_dia']['fecha'])
            stats['por_dia']['dia'] = stats['por_dia']['fecha'].dt.strftime('%d/%m')
            
            import plotly.express as px
            fig = px.line(
                stats['por_dia'], 
                x='dia', 
                y='cantidad',
                markers=True,
                title='Ingresos por Día (Última Semana)'
            )
            fig.update_layout(xaxis_title="Fecha", yaxis_title="Cantidad de Ingresos")
            st.plotly_chart(fig, use_container_width=True)
        
        # Top vehículos
        if not stats['vehiculos'].empty:
            st.subheader("🏆 Top 10 Vehículos Más Frecuentes")
            st.dataframe(
                stats['vehiculos'][['patente', 'propietario', 'depto', 'cantidad']],
                use_container_width=True,
                hide_index=True
            )
        
        # Horarios pico
        if not stats['horarios'].empty:
            st.subheader("⏰ Horarios de Mayor Tráfico")
            st.bar_chart(stats['horarios'].set_index('hora')['cantidad'])
    
    elif periodo == "📆 Último Mes":
        # Vista de último mes
        st.subheader("📆 Estadísticas de los Últimos 30 Días")
        
        stats = obtener_estadisticas_periodo(30)
        
        # Métricas generales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Ingresos", stats['total'])
        
        with col2:
            promedio = stats['total'] / 30
            st.metric("Promedio Diario", f"{promedio:.1f}")
        
        with col3:
            if not stats['vehiculos'].empty:
                vehiculos_unicos = len(stats['vehiculos'])
                st.metric("Vehículos Únicos", vehiculos_unicos)
            else:
                st.metric("Vehículos Únicos", 0)
        
        with col4:
            if not stats['por_dia'].empty:
                dia_mas_activo = stats['por_dia'].loc[stats['por_dia']['cantidad'].idxmax()]
                st.metric("Máximo en un Día", int(dia_mas_activo['cantidad']))
            else:
                st.metric("Máximo en un Día", 0)
        
        st.divider()
        
        # Gráfico de tendencia mensual
        if not stats['por_dia'].empty:
            st.subheader("📈 Tendencia Mensual")
            stats['por_dia']['fecha'] = pd.to_datetime(stats['por_dia']['fecha'])
            stats['por_dia']['dia'] = stats['por_dia']['fecha'].dt.strftime('%d/%m')
            
            import plotly.express as px
            fig = px.area(
                stats['por_dia'], 
                x='dia', 
                y='cantidad',
                title='Ingresos por Día (Último Mes)'
            )
            fig.update_layout(xaxis_title="Fecha", yaxis_title="Cantidad de Ingresos")
            st.plotly_chart(fig, use_container_width=True)
        
        # Top 10 vehículos
        if not stats['vehiculos'].empty:
            st.subheader("🏆 Top 10 Vehículos del Mes")
            
            import plotly.express as px
            fig = px.bar(
                stats['vehiculos'].head(10),
                x='patente',
                y='cantidad',
                text='cantidad',
                title='Vehículos Más Frecuentes'
            )
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(
                stats['vehiculos'][['patente', 'propietario', 'depto', 'cantidad']],
                use_container_width=True,
                hide_index=True
            )
    
    elif periodo == "🔍 Rango Personalizado":
        # Selector de rango de fechas
        st.subheader("🔍 Selecciona Rango de Fechas")
        
        col_fecha1, col_fecha2 = st.columns(2)
        
        with col_fecha1:
            fecha_inicio = st.date_input(
                "Fecha Inicio",
                value=datetime.now(CHILE_TZ) - pd.Timedelta(days=7),
                max_value=datetime.now(CHILE_TZ)
            )
        
        with col_fecha2:
            fecha_fin = st.date_input(
                "Fecha Fin",
                value=datetime.now(CHILE_TZ),
                max_value=datetime.now(CHILE_TZ)
            )
        
        if fecha_inicio > fecha_fin:
            st.error("❌ La fecha de inicio debe ser anterior a la fecha de fin")
        else:
            fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
            fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
            
            df_rango = obtener_registros_rango_fechas(fecha_inicio_str, fecha_fin_str)
            
            if not df_rango.empty:
                st.success(f"📊 {len(df_rango)} registros encontrados")
                
                # Métricas
                col1, col2, col3 = st.columns(3)
                
                dias_diferencia = (fecha_fin - fecha_inicio).days + 1
                
                with col1:
                    st.metric("Total Ingresos", len(df_rango))
                
                with col2:
                    promedio = len(df_rango) / dias_diferencia
                    st.metric("Promedio Diario", f"{promedio:.1f}")
                
                with col3:
                    st.metric("Días Analizados", dias_diferencia)
                
                st.divider()
                
                # Tabla de registros
                st.dataframe(
                    df_rango,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Exportar
                csv_rango = df_rango.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Registros (CSV)",
                    data=csv_rango,
                    file_name=f"ingresos_{fecha_inicio_str}_a_{fecha_fin_str}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No hay registros en el rango seleccionado")
    
    else:  # Dashboard
        st.subheader("📈 Dashboard de Estadísticas")
        
        # Tabs para diferentes períodos
        tab_dash1, tab_dash2, tab_dash3 = st.tabs(["📅 Hoy", "📊 Semana", "📆 Mes"])
        
        with tab_dash1:
            df_hoy = obtener_registros_hoy()
            
            if not df_hoy.empty:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Hoy", len(df_hoy))
                
                with col2:
                    if len(df_hoy) > 0:
                        ultima_hora = pd.to_datetime(df_hoy['fecha_hora'].iloc[0]).strftime('%H:%M')
                        st.metric("Último Ingreso", ultima_hora)
                    else:
                        st.metric("Último Ingreso", "N/A")
                
                with col3:
                    vehiculos_hoy = df_hoy['patente'].nunique()
                    st.metric("Vehículos Únicos", vehiculos_hoy)
                
                # Gráfico por tipo
                if 'tipo_ingreso' in df_hoy.columns:
                    tipo_counts = df_hoy['tipo_ingreso'].value_counts()
                    
                    import plotly.express as px
                    fig = px.pie(
                        values=tipo_counts.values,
                        names=tipo_counts.index,
                        title='Distribución por Tipo de Ingreso'
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos para hoy")
        
        with tab_dash2:
            stats_semana = obtener_estadisticas_periodo(7)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Semana", stats_semana['total'])
            
            with col2:
                promedio = stats_semana['total'] / 7
                st.metric("Promedio Diario", f"{promedio:.1f}")
            
            with col3:
                if not stats_semana['vehiculos'].empty:
                    st.metric("Vehículos Únicos", len(stats_semana['vehiculos']))
                else:
                    st.metric("Vehículos Únicos", 0)
            
            # Gráfico de horarios pico
            if not stats_semana['horarios'].empty:
                st.subheader("⏰ Horarios Pico de la Semana")
                
                import plotly.express as px
                fig = px.bar(
                    stats_semana['horarios'],
                    x='hora',
                    y='cantidad',
                    title='Ingresos por Hora'
                )
                fig.update_layout(xaxis_title="Hora del Día", yaxis_title="Cantidad")
                st.plotly_chart(fig, use_container_width=True)
        
        with tab_dash3:
            stats_mes = obtener_estadisticas_periodo(30)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Mes", stats_mes['total'])
            
            with col2:
                promedio = stats_mes['total'] / 30
                st.metric("Promedio Diario", f"{promedio:.1f}")
            
            with col3:
                if not stats_mes['vehiculos'].empty:
                    st.metric("Vehículos Únicos", len(stats_mes['vehiculos']))
                else:
                    st.metric("Vehículos Únicos", 0)
            
            with col4:
                if not stats_mes['por_dia'].empty:
                    max_dia = stats_mes['por_dia']['cantidad'].max()
                    st.metric("Máximo en un Día", int(max_dia))
                else:
                    st.metric("Máximo en un Día", 0)
            
            # Top vehículos del mes
            if not stats_mes['vehiculos'].empty:
                st.subheader("🏆 Top 5 Vehículos del Mes")
                top_5 = stats_mes['vehiculos'].head(5)
                
                for idx, row in top_5.iterrows():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"**{row['patente']}** - {row['propietario']} (Depto {row['depto']})")
                    with col_b:
                        st.metric("Ingresos", int(row['cantidad']))

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>Sistema de Control de Acceso Vehicular v2.0 | Desarrollado para Guardias de Seguridad</p>
    </div>
    """, unsafe_allow_html=True)
