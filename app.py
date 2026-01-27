import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import re

# Configuración de la página
st.set_page_config(
    page_title="Control de Acceso Vehicular",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
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
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        
        c.execute('''
            INSERT INTO registro_ingresos (patente, guardia, tipo_ingreso)
            VALUES (?, ?, ?)
        ''', (patente_clean, guardia, tipo_ingreso))
        
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
    conn = sqlite3.connect('vehiculos_autorizados.db')
    df = pd.read_sql_query('''
        SELECT r.patente, r.fecha_hora, r.guardia, r.tipo_ingreso, 
               v.propietario, v.depto
        FROM registro_ingresos r
        LEFT JOIN vehiculos v ON r.patente = v.patente
        WHERE DATE(r.fecha_hora) = DATE('now')
        ORDER BY r.fecha_hora DESC
    ''', conn)
    conn.close()
    return df

def desactivar_vehiculo(vehiculo_id):
    """Desactiva un vehículo (borrado lógico)"""
    conn = sqlite3.connect('vehiculos_autorizados.db')
    c = conn.cursor()
    c.execute('UPDATE vehiculos SET activo = 0 WHERE id = ?', (vehiculo_id,))
    conn.commit()
    conn.close()

# Inicializar base de datos
init_db()

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
    
    # Estadísticas del día
    st.subheader("📊 Resumen del Día")
    df_hoy = obtener_registros_hoy()
    st.metric("Ingresos Hoy", len(df_hoy))
    
    df_vehiculos = obtener_vehiculos()
    st.metric("Total Autorizados", len(df_vehiculos))

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
    
    if buscar_btn and patente_buscar:
        if not nombre_guardia:
            st.error("❌ Debes ingresar tu nombre como guardia primero")
        else:
            resultado = buscar_vehiculo(patente_buscar)
            
            if resultado:
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
                
                # Registrar ingreso
                tipo_ingreso = st.selectbox("Tipo de Ingreso", ["Residente", "Visita", "Servicio"])
                
                if st.button("✅ CONFIRMAR INGRESO", type="primary"):
                    if registrar_ingreso(resultado[1], nombre_guardia, tipo_ingreso):
                        st.success(f"✅ Ingreso registrado a las {datetime.now().strftime('%H:%M:%S')}")
                        st.balloons()
                    else:
                        st.error("Error al registrar ingreso")
            else:
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
    st.header("📋 Vehículos Autorizados")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_patente = st.text_input("🔎 Filtrar por Patente", key="filtro_patente")
    
    with col2:
        filtro_depto = st.text_input("🔎 Filtrar por Depto", key="filtro_depto")
    
    with col3:
        filtro_propietario = st.text_input("🔎 Filtrar por Propietario", key="filtro_propietario")
    
    # Obtener y filtrar datos
    df = obtener_vehiculos()
    
    if not df.empty:
        # Aplicar filtros
        if filtro_patente:
            df = df[df['patente'].str.contains(filtro_patente.upper(), na=False)]
        if filtro_depto:
            df = df[df['depto'].str.contains(filtro_depto, na=False, case=False)]
        if filtro_propietario:
            df = df[df['propietario'].str.contains(filtro_propietario, na=False, case=False)]
        
        st.dataframe(
            df[['patente', 'propietario', 'depto', 'marca', 'modelo', 'color', 'telefono']],
            use_container_width=True,
            hide_index=True
        )
        
        st.download_button(
            label="📥 Descargar Lista (Excel)",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f"vehiculos_autorizados_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No hay vehículos registrados aún")

# TAB 4: REGISTRO DE INGRESOS
with tab4:
    st.header("📈 Registro de Ingresos del Día")
    
    df_ingresos = obtener_registros_hoy()
    
    if not df_ingresos.empty:
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
        
    else:
        st.info("No hay ingresos registrados hoy")

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>Sistema de Control de Acceso Vehicular v1.0 | Desarrollado para Guardias de Seguridad</p>
    </div>
    """, unsafe_allow_html=True)
