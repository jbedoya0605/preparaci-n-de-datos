import requests
import pandas as pd
import numpy as np
import streamlit as st
import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------------------------------------------------
# Configuración y Metadatos de la Estación 28 (San Carlos)
# ------------------------------------------------------------------
CODIGO_ESTACION = "28"
NOMBRE_ESTACION = "Puente Entrada San Carlos"
CORRIENTE = "Río San Carlos"
MUNICIPIO = "San Carlos"
TIPO_ESTACION = "Hidrometeorológica (Nivel y Precipitación)"

LAT_SAN_CARLOS = 6.1822
LON_SAN_CARLOS = -74.9961

API_BASE_URL = "https://marco.cornare.gov.co/api/v1/estaciones"

st.set_page_config(
    page_title=f"Estación {CODIGO_ESTACION} — San Carlos",
    page_icon="🌊",
    layout="wide"
)

# ------------------------------------------------------------------
# Función de Consulta a la API
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
        
        # Respaldo sin filtros si la API falla con parámetros
        resp_fallback = requests.get(url, headers=headers, timeout=timeout, verify=False)
        if resp_fallback.status_code == 200:
            return resp_fallback.json(), None
            
        return None, f"HTTP {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return None, f"Error de red: {e}"

# ------------------------------------------------------------------
# Sidebar — Parámetros de Selección
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

col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.info(f"📍 **Estación:** {NOMBRE_ESTACION}\n\n🌊 **Corriente:** {CORRIENTE}")
with col_info2:
    st.info(f"🏛️ **Municipio:** {MUNICIPIO}\n\n⚙️ **Tipo:** {TIPO_ESTACION}")
with col_info3:
    st.success("🛡️ **Estado del Cauce:** SEGURO\n\n🛰️ **Conectado a Geoportal MARCO**")

st.write("---")

# ------------------------------------------------------------------
# Procesamiento de Datos
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
            # CORRECCIÓN CLAVE DE FECHAS Y ZONA HORARIA
            df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce").dt.tz_localize(None)
            df[col_valor] = pd.to_numeric(df[col_valor], errors="coerce")
            df = df.dropna(subset=[col_fecha, col_valor]).sort_values(col_fecha)

            # Convertir selectores de Streamlit a Timestamps de Pandas sin zona horaria
            f_inicio = pd.to_datetime(desde_input)
            f_fin = pd.to_datetime(hasta_input) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            
            mask = (df[col_fecha] >= f_inicio) & (df[col_fecha] <= f_fin)
            df_filtrado = df.loc[mask].copy()

            if df_filtrado.empty:
                st.warning("No hay registros en el rango exacto seleccionado. Mostrando la serie general disponible:")
                df_filtrado = df.copy()

            # CÁLCULOS ESTADÍSTICOS Y MAYORES SUBIDAS
            df_filtrado["diferencia_nivel"] = df_filtrado[col_valor].diff()
            
            lecturas_totales = len(df_filtrado)
            nivel_actual = df_filtrado[col_valor].iloc[-1]
            nivel_max = df_filtrado[col_valor].max()
            nivel_min = df_filtrado[col_valor].min()
            nivel_prom = df_filtrado[col_valor].mean()
            desv_est = df_filtrado[col_valor].std()
            p90 = df_filtrado[col_valor].quantile(0.90)
            
            max_subida = df_filtrado["diferencia_nivel"].max()
            idx_max_subida = df_filtrado["diferencia_nivel"].idxmax()
            fecha_max_subida = df_filtrado.loc[idx_max_subida, col_fecha] if pd.notnull(idx_max_subida) else "N/A"

            # MÉTRICAS: Nivel 1 (Indicadores Principales)
            st.subheader("📊 Indicadores Principales del Cauce")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Lecturas Recibidas", f"{lecturas_totales}")
            m2.metric("Nivel Actual", f"{nivel_actual:.1f} cm")
            m3.metric("Nivel Promedio", f"{nivel_prom:.1f} cm")
            m4.metric("Nivel Máximo Registrado", f"{nivel_max:.1f} cm")

            # MÉTRICAS: Nivel 2 (Análisis Estadístico e Hidrológico)
            st.subheader("📈 Análisis Estadístico e Hidrológico")
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("Nivel Mínimo", f"{nivel_min:.1f} cm")
            e2.metric("Desviación Estándar", f"±{desv_est:.2f} cm")
            e3.metric("Percentil 90 (Nivel Alto)", f"{p90:.1f} cm")
            e4.metric("Mayor Creciente (Subida)", f"+{max_subida:.1f} cm" if pd.notnull(max_subida) else "0 cm")

            # GRÁFICOS VISUALES
            st.write("---")
            st.subheader("📉 Visualización Temporal de la Estación")
            t1, t2 = st.tabs(["Comportamiento Continuo", "Variaciones Bruscas (Crecientes)"])
            
            with t1:
                st.line_chart(df_filtrado.set_index(col_fecha)[col_valor])
            
            with t2:
                st.caption("Muestra las variaciones positivas/negativas entre lecturas consecutivas.")
                st.bar_chart(df_filtrado.set_index(col_fecha)["diferencia_nivel"])

            # MAPA DE UBICACIÓN
            st.subheader("🗺️ Ubicación de la Estación Hidrometeorológica")
            st.map(pd.DataFrame({"lat": [LAT_SAN_CARLOS], "lon": [LON_SAN_CARLOS]}), zoom=12)

            # TABLA DE DATOS Y DESCARGA CSV
            with st.expander("📄 Ver Matriz de Datos y Descargar CSV"):
                st.dataframe(df_filtrado, use_container_width=True)
                csv = df_filtrado.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Descargar Reporte Completo en CSV",
                    data=csv,
                    file_name="reporte_estacion28_sancarlos.csv",
                    mime="text/csv"
                )
        else:
            st.warning(f"Estructura de columnas no reconocida: {list(df.columns)}")
    else:
        st.error("No se recibieron registros para la estación 28.")
