import requests
import pandas as pd
import numpy as np
import streamlit as st
import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------------------------------------------------
# Configuración y Metadatos de tu Estación (Código 28)
# ------------------------------------------------------------------
CODIGO_ESTACION = "28"
NOMBRE_ESTACION = "Puente Entrada San Carlos"
CORRIENTE = "Río San Carlos"
MUNICIPIO = "San Carlos"
TIPO_ESTACION = "Hidrometeorológica (Nivel y Precipitación)"
ESTADO_INICIAL = "SEGURO"

# Coordenadas San Carlos, Antioquia
LAT_SAN_CARLOS = 6.1822
LON_SAN_CARLOS = -74.9961

API_BASE_URL = "https://marco.cornare.gov.co/api/v1/estaciones"

st.set_page_config(
    page_title=f"Estación {CODIGO_ESTACION} — {NOMBRE_ESTUDIANTE if 'NOMBRE_ESTUDIANTE' in locals() else 'San Carlos'}",
    page_icon="🌊",
    layout="wide"
)

# ------------------------------------------------------------------
# Funciones de consulta a la API de CORNARE
# ------------------------------------------------------------------
def obtener_serie_nivel(codigo_estacion, desde, hasta, calidad=1, timeout=30):
    url = f"{API_BASE_URL}/{codigo_estacion}/nivel"
    params = {"desde": desde, "hasta": hasta, "calidad": calidad}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout, verify=False)
        if resp.status_code == 200:
            return resp.json(), None
        
        # Respaldo sin filtro si el servidor retorna error con rango
        resp_fallback = requests.get(url, headers=headers, timeout=timeout, verify=False)
        if resp_fallback.status_code == 200:
            return resp_fallback.json(), None
            
        return None, f"HTTP {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return None, f"Error de red: {e}"

# ------------------------------------------------------------------
# Sidebar — Configuración Personalizada
# ------------------------------------------------------------------
st.sidebar.header("📍 Estación Seleccionada")
NOMBRE_ESTUDIANTE = st.sidebar.text_input("Estudiante", "Juan David Bedoya Hernández")

st.sidebar.markdown(f"**Código:** {CODIGO_ESTACION}")
st.sidebar.markdown(f"**Ubicación:** {NOMBRE_ESTACION}")
st.sidebar.markdown(f"**Fuente:** {CORRIENTE}")
st.sidebar.markdown(f"**Municipio:** {MUNICIPIO}")
st.sidebar.markdown(f"**Sensores:** Nivel y Precipitación")

st.sidebar.write("---")
st.sidebar.subheader("📅 Rango de Fechas")
fecha_fin_def = datetime.date(2026, 9, 1)
fecha_inicio_def = datetime.date(2026, 8, 25)

desde_input = st.sidebar.date_input("Desde", value=fecha_inicio_def)
hasta_input = st.sidebar.date_input("Hasta", value=fecha_fin_def)

desde_str = desde_input.strftime("%Y-%m-%d")
hasta_str = hasta_input.strftime("%Y-%m-%d")

# ------------------------------------------------------------------
# Encabezado Principal y Ficha Técnica
# ------------------------------------------------------------------
st.title(f"🌊 Monitoreo en Tiempo Real — Estación {CODIGO_ESTACION}")
st.caption(f"Estudiante: **{NOMBRE_ESTUDIANTE}** · Sistema MARCO — CORNARE")

# Tarjetas Informativas
col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.info(f"📍 **Estación:** {NOMBRE_ESTACION}\n\n🌊 **Corriente:** {CORRIENTE}")
with col_info2:
    st.info(f"🏛️ **Municipio:** {MUNICIPIO}\n\n⚙️ **Tipo:** {TIPO_ESTACION}")
with col_info3:
    st.success(f"🛡️ **Estado del Cauce:** {ESTADO_INICIAL}\n\n🛰️ **Conectado a Geoportal MARCO**")

st.write("---")

# ------------------------------------------------------------------
# Procesamiento de Datos y Análisis Visual
# ------------------------------------------------------------------
datos, error = obtener_serie_nivel(CODIGO_ESTACION, desde_str, hasta_str)

if error:
    st.error(f"Error al conectar con la estación {CODIGO_ESTACION}: {error}")
else:
    registros = []
    if isinstance(datos, list):
        registros = datos
    elif isinstance(datos, dict):
        registros = datos.get("data", datos.get("results", datos.get("values", [])))

    if registros:
        df = pd.DataFrame(registros)
        
        col_fecha = next((col for col in ["level_date", "fecha", "fecha_hora", "date"] if col in df.columns), None)
        col_valor = next((col for col in ["level", "nivel", "valor", "value"] if col in df.columns), None)

        if col_fecha and col_valor:
            df[col_fecha] = pd.to_datetime(df[col_fecha])
            
            # Filtro por rango de fechas en Pandas
            f_inicio = pd.to_datetime(desde_input)
            f_fin = pd.to_datetime(hasta_input) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            mask = (df[col_fecha] >= f_inicio) & (df[col_fecha] <= f_fin)
            df_filtrado = df.loc[mask].sort_values(col_fecha).copy()

            if df_filtrado.empty:
                st.warning("No hay lecturas en las fechas exactas. Mostrando registros disponibles de la estación:")
                df_filtrado = df.sort_values(col_fecha).copy()

            # Cálculo de Mayores Subidas y Análisis Hidrológico
            df_filtrado["diferencia_nivel"] = df_filtrado[col_valor].diff()
            max_subida = df_filtrado["diferencia_nivel"].max()
            
            # Fila de fecha con la mayor subida repentina
            idx_max_subida = df_filtrado["diferencia_nivel"].idxmax()
            fecha_max_subida = df_filtrado.loc[idx_max_subida, col_fecha] if pd.notnull(idx_max_subida) else "N/A"

            nivel_max = df_filtrado[col_valor].max()
            nivel_min = df_filtrado[col_valor].min()
            nivel_prom = df_filtrado[col_valor].mean()
            nivel_actual = df_filtrado[col_valor].iloc[-1]

            # --- Métricas Estadísticas Visuales ---
            st.subheader("📊 Resumen Hidrológico")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Nivel Actual", f"{nivel_actual:.1f} cm")
            m2.metric("Nivel Máximo", f"{nivel_max:.1f} cm")
            m3.metric("Nivel Promedio", f"{nivel_prom:.1f} cm")
            m4.metric("Nivel Mínimo", f"{nivel_min:.1f} cm")
            m5.metric("Mayor Creciente", f"+{max_subida:.1f} cm" if pd.notnull(max_subida) else "0 cm")

            # --- Gráficos Interactivos ---
            st.subheader("📈 Comportamiento del Río San Carlos")
            tab_graf1, tab_graf2 = st.tabs(["📉 Serie de Nivel", "⚡ Mayores Subidas (Variaciones)"])
            
            with tab_graf1:
                st.line_chart(df_filtrado.set_index(col_fecha)[col_valor])
            
            with tab_graf2:
                st.caption("Visualiza las variaciones bruscas de nivel entre lecturas consecutivas.")
                st.bar_chart(df_filtrado.set_index(col_fecha)["diferencia_nivel"])

            # --- Alerta de Creciente Relevante ---
            if pd.notnull(max_subida) and max_subida > 0:
                st.warning(f"⚡ **Pico de Aumento Detectado:** La mayor subida repentina registrada fue de **+{max_subida:.2f} cm** el día **{fecha_max_subida}**.")

            # --- Mapa de Ubicación Exacta ---
            st.subheader("🗺️ Ubicación Geográfica de la Estación")
            df_mapa = pd.DataFrame({"lat": [LAT_SAN_CARLOS], "lon": [LON_SAN_CARLOS]})
            st.map(df_mapa, zoom=12)

            # --- Descarga y Datos Crudos ---
            with st.expander("📁 Explorar y Descargar Datos de la Estación 28"):
                st.dataframe(df_filtrado, use_container_width=True)
                csv = df_filtrado.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Descargar Reporte CSV",
                    data=csv,
                    file_name=f"estacion_28_sancarlos_{desde_str}_a_{hasta_str}.csv",
                    mime="text/csv"
                )
        else:
            st.warning(f"Estructura de campos no reconocida. Columnas recibidas: {list(df.columns)}")
    else:
        st.error("No se recibieron datos para la estación 28 en el servidor.")
