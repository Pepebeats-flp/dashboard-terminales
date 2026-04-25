# dashboard.py

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import os

# -------------------------------------------------
# FUNCIONES AUXILIARES
# -------------------------------------------------

def normalizar_texto(col):
    return (
        col.astype(str)
        .str.strip()
        .str.replace(r"\\s+", " ", regex=True)
        .str.upper()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
    )

def limpiar_terminal(col):
    # Eliminar artículos comunes al inicio del nombre
    return (
        col.str.replace(
            r"^(EL|LA|LOS|LAS)\s+",
            "",
            regex=True
        )
    )

# -------------------------------------------------
# CONFIGURACIÓN GENERAL
# -------------------------------------------------

st.set_page_config(
    page_title="Dashboard Revisiones",
    layout="wide"
)

st.title("Dashboard de Revisiones por Terminal")

# -------------------------------------------------
# CARGA DE DATOS
# -------------------------------------------------

# Reemplaza por tu archivo real
# Ejemplo:
# df = pd.read_csv("revisiones.csv")
# Lista para almacenar DataFrames
dataframes = []

# Excluir archivo de coordenadas del listado principal
coords_file_name = "coordenadas_terminales.csv"

csv_files = sorted([
    file for file in os.listdir()
    if file.endswith('.csv')
    and file != coords_file_name
])
csv_names = [os.path.splitext(file)[0] for file in csv_files]
# Eliminar "estado_general-" y guardar solo el cliente
csv_names = [name.replace("estado_general-", "") for name in csv_names]

# Leer cada archivo CSV y almacenarlo en la lista de DataFrames ademas de agregar una columna con el nombre del cliente
    
for file, client_name in zip(csv_files, csv_names):
    try:
        print(f"Leyendo archivo: {file}")
        
        df = pd.read_csv(
            file,
            sep=None,          # Detecta separador automáticamente
            engine="python",   # Necesario para sep=None
            encoding="latin1", # Evita errores comunes de encoding
            on_bad_lines="skip" # Salta filas corruptas
        )
        
        df['CLIENTE'] = client_name
        dataframes.append(df)
    except Exception as e:
        print(f"Error al leer {file}: {e}")
# Concatenar todos los DataFrames en uno solo
if dataframes:
    df = pd.concat(dataframes, ignore_index=True)
    print("DataFrames concatenados exitosamente.")
    # Normalizar nombres de terminal desde el inicio
    if "LUGAR INSPECCION" in df.columns:
        df["LUGAR INSPECCION"] = normalizar_texto(
            df["LUGAR INSPECCION"]
        )
        df["LUGAR INSPECCION"] = limpiar_terminal(
            df["LUGAR INSPECCION"]
        )
        # DEBUG: imprimir terminales únicos tal como quedan en registros
        terminales_unicos = sorted(
            df["LUGAR INSPECCION"]
            .dropna()
            .unique()
        )

        print("\n--- TERMINALES DETECTADOS EN REGISTROS ---")
        print(f"Total terminales únicos: {len(terminales_unicos)}")

        for t in terminales_unicos:
            print(t)

        print("--- FIN LISTA TERMINALES ---\n")
else:
    print("No se encontraron archivos CSV para procesar.")


#Eliminar columnas donde todos los valores son nulos, y el ESTADO sea "Eliminada"
df = df.dropna(axis=1, how='all')
df = df[df['ESTADO'] != 'Eliminada']
# Mostrar el DataFrame final
print(df.head())
# Limpiar nombre de columnas (quita caracteres raros tipo ï»¿)
df.columns = df.columns.str.replace('ï»¿', '')
df.columns = df.columns.str.strip()

# Convertir fechas
df["FECHA CREACION"] = pd.to_datetime(
    df["FECHA CREACION"],
    dayfirst=True,
    errors="coerce"
)

# Convertir horas
df["HORA CREACION"] = pd.to_datetime(
    df["HORA CREACION"],
    format="%H:%M:%S",
    errors="coerce"
).dt.time

# Crear variables útiles

df["fecha"] = df["FECHA CREACION"]

df["hora"] = pd.to_datetime(
    df["HORA CREACION"].astype(str),
    errors="coerce"
).dt.hour

# Día de la semana en español y ordenado
dias_map = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

orden_dias = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo"
]

df["dia_semana"] = (
    df["FECHA CREACION"]
    .dt.day_name()
    .map(dias_map)
)

df["dia_semana"] = pd.Categorical(
    df["dia_semana"],
    categories=orden_dias,
    ordered=True
)

df["mes"] = df["FECHA CREACION"].dt.month

print("Datos preparados correctamente")

inspecciones_diarias = (
    df.groupby(
        ["CLIENTE", "LUGAR INSPECCION", "fecha"]
    )
    .size()
    .reset_index(name="n_inspecciones")
)

# Normalizar nombres también en inspecciones_diarias
inspecciones_diarias["LUGAR INSPECCION"] = normalizar_texto(
    inspecciones_diarias["LUGAR INSPECCION"]
)
inspecciones_diarias["LUGAR INSPECCION"] = limpiar_terminal(
    inspecciones_diarias["LUGAR INSPECCION"]
)

# Promedio diario por terminal

media_diaria_terminal = (
    inspecciones_diarias
    .groupby("LUGAR INSPECCION")["n_inspecciones"]
    .mean()
    .sort_values(ascending=False)
)

print(media_diaria_terminal)

# -------------------------------------------------
# CARGA Y UNIÓN DE COORDENADAS DE TERMINALES
# -------------------------------------------------

# Inicialización segura de coordenadas (evita errores si no existe archivo)
coords_df = pd.DataFrame()
# Ruta del archivo de coordenadas
coords_file = "terminales_coordenadas.csv"

if os.path.exists(coords_file):
    coords_df = pd.read_csv(coords_file)

    # Normalizar nombres inmediatamente al cargar coordenadas
    coords_df.columns = coords_df.columns.str.strip()
    coords_df["LUGAR INSPECCION"] = normalizar_texto(coords_df["LUGAR INSPECCION"])
    coords_df["LUGAR INSPECCION"] = limpiar_terminal(coords_df["LUGAR INSPECCION"])

    # Convertir coordenadas a numéricas (clave para mapas)
    coords_df["LATITUD"] = pd.to_numeric(
        coords_df["LATITUD"],
        errors="coerce"
    )

    coords_df["LONGITUD"] = pd.to_numeric(
        coords_df["LONGITUD"],
        errors="coerce"
    )

    # Debug: mostrar primeras filas de coordenadas cargadas
    print("\n--- PRIMERAS COORDENADAS CARGADAS ---")
    print(coords_df.head())
    print("--- FIN COORDENADAS ---\n")

    # con columnas: LUGAR INSPECCION, LATITUD, LONGITUD

    if "LUGAR INSPECCION" in coords_df.columns and "LATITUD" in coords_df.columns and "LONGITUD" in coords_df.columns:
        try:
            df = df.merge(
                coords_df,
                on="LUGAR INSPECCION",
                how="left"
            )
            # Debug: detectar terminales sin match
            terminales_df = set(df["LUGAR INSPECCION"].unique())
            terminales_coords = set(coords_df["LUGAR INSPECCION"].unique())

            terminales_sin_match = terminales_df - terminales_coords

            print(
                f"Terminales sin coordenadas encontradas en archivo: {len(terminales_sin_match)}"
            )

            if len(terminales_sin_match) > 0:
                print(
                    "Ejemplo terminales sin match:",
                    list(terminales_sin_match)[:10]
                )

                # Guardar terminales sin coordenadas en archivo para depuración
                if len(terminales_sin_match) > 0:
                    df_sin_coords = pd.DataFrame(
                        sorted(list(terminales_sin_match)),
                        columns=["LUGAR INSPECCION"]
                    )

                    df_sin_coords.to_csv(
                        "terminales_sin_coordenadas.csv",
                        index=False
                    )

                    print(
                        "Archivo 'terminales_sin_coordenadas.csv' generado con terminales sin coordenadas."
                    )
            # Debug: contar coordenadas válidas
            valid_coords = df[
                ["LATITUD", "LONGITUD"]
            ].dropna().shape[0]

            print(
                f"Filas con coordenadas válidas: {valid_coords}"
            )
            # Eliminar coordenadas inválidas (0,0)
            df = df[
                ~(
                    (df["LATITUD"] == 0) &
                    (df["LONGITUD"] == 0)
                )
            ]
        except Exception as e:
            print(f"Error al unir coordenadas: {e}")
    else:
        print("El archivo de coordenadas no tiene las columnas necesarias.")
else:
    print("Archivo de coordenadas no encontrado.")

# -------------------------------------------------
# PREPARACIÓN DE DATOS
# -------------------------------------------------

if "fecha" in inspecciones_diarias.columns:

    inspecciones_diarias["fecha"] = pd.to_datetime(
        inspecciones_diarias["fecha"]
    )

    inspecciones_diarias["hora"] = (
        inspecciones_diarias["fecha"]
        .dt.hour
    )

    inspecciones_diarias["dia"] = (
        inspecciones_diarias["fecha"]
        .dt.date
    )

    inspecciones_diarias["dia_semana"] = (
        inspecciones_diarias["fecha"]
        .dt.day_name()
    )

# -------------------------------------------------
# FILTROS INTERACTIVOS
# -------------------------------------------------

st.sidebar.header("Filtros")

clientes = sorted(
    inspecciones_diarias["CLIENTE"]
    .dropna()
    .unique()
)

cliente_sel = st.sidebar.multiselect(
    "Seleccionar Cliente",
    clientes,
    default=clientes
)

# Terminales dependen del cliente seleccionado
terminales = sorted(
    inspecciones_diarias[
        inspecciones_diarias["CLIENTE"].isin(cliente_sel)
    ]["LUGAR INSPECCION"]
    .dropna()
    .unique()
)

terminal_sel = st.sidebar.multiselect(
    "Seleccionar Terminal",
    terminales,
    default=terminales
)

df_f = inspecciones_diarias[
    (inspecciones_diarias["LUGAR INSPECCION"].isin(terminal_sel)) &
    (inspecciones_diarias["CLIENTE"].isin(cliente_sel))
]

# -------------------------------------------------
# ANÁLISIS AUTOMÁTICO
# -------------------------------------------------

st.subheader(
    "Resumen automático"
)

col1, col2, col3 = st.columns(3)

total_rev = df_f["n_inspecciones"].sum()

promedio = df_f["n_inspecciones"].mean()

# Calcular días únicos
dias_unicos = df_f["dia"].nunique()

if dias_unicos > 0:
    promedio_por_dia = total_rev / dias_unicos
else:
    promedio_por_dia = 0

diferencia_total_promedio = total_rev - promedio_por_dia



# Terminal con mayor promedio diario
top_terminal_prom = (
    df_f
    .groupby("LUGAR INSPECCION")
    ["n_inspecciones"]
    .mean()
    .idxmax()
)

col1.metric(
    "Total revisiones",
    int(total_rev)
)

col2.metric(
    "Promedio por día",
    round(promedio_por_dia, 2)
)


col1_2 = st.columns(1)[0]

col1_2.metric(
    "Terminal con mayor promedio diario",
    top_terminal_prom
)

fecha_min = df_f["dia"].min()
fecha_max = df_f["dia"].max()

if pd.notnull(fecha_min) and pd.notnull(fecha_max):
    rango_fechas = f"{fecha_min} a {fecha_max}"
else:
    rango_fechas = "Sin datos"

col1_3, col2_3 = st.columns(2)


col2_3.metric(
    "Rango de fechas",
    rango_fechas
)

# -------------------------------------------------
# 1. PROMEDIO DIARIO POR TERMINAL
# -------------------------------------------------

st.subheader(
    "Promedio diario de revisiones por terminal"
)

media_terminal_prom = (
    df_f
    .groupby("LUGAR INSPECCION")[
        "n_inspecciones"
    ]
    .mean()
    .reset_index(name="promedio_diario")
)

media_terminal_total = (
    df_f
    .groupby("LUGAR INSPECCION")[
        "n_inspecciones"
    ]
    .sum()
    .reset_index(name="total_registros")
)

media_terminal_df = media_terminal_prom.merge(
    media_terminal_total,
    on="LUGAR INSPECCION"
)

media_terminal_plot = (
    media_terminal_df
    .sort_values(
        "promedio_diario",
        ascending=False
    )
    .head(20)
)

fig1 = px.bar(
    media_terminal_plot,
    x="LUGAR INSPECCION",
    y="promedio_diario",
    title="Promedio diario por terminal"
)

fig1.update_layout(
    xaxis_tickangle=-45
)

fig1.update_traces(
    customdata=media_terminal_plot[["total_registros"]].values,
    hovertemplate=(
        "Terminal: %{x}<br>"
        "Promedio por día: %{y:.2f}<br>"
        "Total registros: %{customdata[0]}<extra></extra>"
    )
)

st.plotly_chart(
    fig1,
    use_container_width=True
)

# -------------------------------------------------
# 2. REVISIÓN POR DEPÓSITO
# -------------------------------------------------

if "deposito" in df_f.columns:

    st.subheader(
        "Revisiones por depósito"
    )

    deposito_df = (

        df_f
        .groupby("deposito")
        ["n_inspecciones"]
        .sum()
        .reset_index()

    )

    fig2 = px.bar(

        deposito_df.sort_values(
            "n_inspecciones",
            ascending=False
        ),

        x="deposito",
        y="n_inspecciones"

    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

# -------------------------------------------------
# 3. BLOQUES HORARIOS
# -------------------------------------------------


st.subheader(
    "Heatmap Terminal vs Hora"
)

df_hora_terminal = (
    df[
        (df["LUGAR INSPECCION"].isin(terminal_sel)) &
        (df["CLIENTE"].isin(cliente_sel))
    ]
    .groupby(
        ["LUGAR INSPECCION", "hora"]
    )
    .size()
    .reset_index(name="revisiones")
)

pivot_ht = df_hora_terminal.pivot(
    index="LUGAR INSPECCION",
    columns="hora",
    values="revisiones"
)
pivot_ht = pivot_ht.fillna(0)

# Calcular promedio por día para hover
pivot_ht_prom = pivot_ht.copy()
if dias_unicos > 0:
    pivot_ht_prom = pivot_ht_prom / dias_unicos

fig_ht = px.imshow(
    pivot_ht,
    aspect="auto"
)

fig_ht.update_traces(
    customdata=pivot_ht_prom.values,
    hovertemplate=(
        "Terminal: %{y}<br>"
        "Hora: %{x}<br>"
        "Total revisiones: %{z}<br>"
        "Promedio por día: %{customdata:.2f}<extra></extra>"
    )
)

st.plotly_chart(
    fig_ht,
    use_container_width=True
)

# -------------------------------------------------
# 4C. HEATMAP TERMINAL VS DIA SEMANA
# -------------------------------------------------

st.subheader(
    "Heatmap Terminal vs Día Semana"
)

df_dia_terminal = (
    df[
        (df["LUGAR INSPECCION"].isin(terminal_sel)) &
        (df["CLIENTE"].isin(cliente_sel))
    ]
    .groupby(
        ["LUGAR INSPECCION", "dia_semana"]
    )
    .size()
    .reset_index(name="revisiones")
)

pivot_dt = df_dia_terminal.pivot(
    index="LUGAR INSPECCION",
    columns="dia_semana",
    values="revisiones"
)
pivot_dt = pivot_dt.fillna(0)

pivot_dt = pivot_dt.reindex(
    columns=orden_dias
)

# Agregar versión promedio por día
conteo_dias_semana = (
    df[
        (df["LUGAR INSPECCION"].isin(terminal_sel)) &
        (df["CLIENTE"].isin(cliente_sel))
    ]
    .groupby("dia_semana")["fecha"]
    .nunique()
)

pivot_dt_prom = pivot_dt.copy()
for col in pivot_dt_prom.columns:
    if col in conteo_dias_semana and conteo_dias_semana[col] > 0:
        pivot_dt_prom[col] = (
            pivot_dt_prom[col] /
            conteo_dias_semana[col]
        )

fig_dt = px.imshow(
    pivot_dt,
    aspect="auto"
)

fig_dt.update_traces(
    customdata=pivot_dt_prom.values,
    hovertemplate=(
        "Terminal: %{y}<br>"
        "Día: %{x}<br>"
        "Total revisiones: %{z}<br>"
        "Promedio por día: %{customdata:.2f}<extra></extra>"
    )
)

st.plotly_chart(
    fig_dt,
    use_container_width=True
)

# -------------------------------------------------
# 5. EVOLUCIÓN DIARIA
# -------------------------------------------------

if "dia" in df_f.columns:

    st.subheader(
        "Evolución diaria"
    )

    diario_df = (

        df_f
        .groupby("dia")
        ["n_inspecciones"]
        .sum()
        .reset_index()

    )

    fig5 = px.line(

        diario_df,
        x="dia",
        y="n_inspecciones"

    )



    st.plotly_chart(
        fig5,
        use_container_width=True
    )

# -------------------------------------------------
# MAPA GEOGRÁFICO DE REVISIÓN POR TERMINAL
# -------------------------------------------------

st.subheader("Mapa geográfico de revisiones por terminal")

# --- Coordenadas limpias ---
coords_clean = coords_df.copy()

coords_clean["LATITUD"] = pd.to_numeric(coords_clean["LATITUD"], errors="coerce")
coords_clean["LONGITUD"] = pd.to_numeric(coords_clean["LONGITUD"], errors="coerce")

coords_clean = coords_clean.dropna(subset=["LATITUD", "LONGITUD"])
coords_clean = coords_clean[~((coords_clean["LATITUD"] == 0) & (coords_clean["LONGITUD"] == 0))]

# --- Agregación de eventos ---
map_df = (
    df_f.groupby("LUGAR INSPECCION")
    .size()
    .reset_index(name="EVENTOS")
)

# --- Merge ---
map_df = map_df.merge(coords_clean, on="LUGAR INSPECCION", how="left")

map_df["LATITUD"] = pd.to_numeric(map_df["LATITUD"], errors="coerce")
map_df["LONGITUD"] = pd.to_numeric(map_df["LONGITUD"], errors="coerce")

map_df = map_df.dropna(subset=["LATITUD", "LONGITUD"])

# --- Debug mínimo útil ---
st.write("Registros con coordenadas válidas:", len(map_df))

# --- Render mapa ---
if len(map_df) > 0:

    fig_map = px.scatter_mapbox(
        map_df,
        lat="LATITUD",
        lon="LONGITUD",
        size="EVENTOS",
        color_discrete_sequence=["red"],
        hover_name="LUGAR INSPECCION",
        zoom=10,
        height=600
    )

    # --- unir promedio diario al mapa ---
    if "promedio_diario" in media_terminal_df.columns:
        map_df = map_df.merge(
            media_terminal_df[["LUGAR INSPECCION", "promedio_diario"]],
            on="LUGAR INSPECCION",
            how="left"
        )

    # --- custom hover ---
    fig_map.update_traces(
        customdata=map_df[["EVENTOS", "promedio_diario"]].values,
        hovertemplate=(
            "Terminal: %{hovertext}<br>"
            "Registros: %{customdata[0]}<br>"
            "Promedio diario: %{customdata[1]:.2f}<extra></extra>"
        ),
        marker=dict(
            opacity=0.85
        )
    )

    fig_map.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=0, r=0, t=0, b=0),
        mapbox=dict(
            center=dict(
                lat=map_df["LATITUD"].mean(),
                lon=map_df["LONGITUD"].mean()
            )
        )
    )

    st.plotly_chart(fig_map, use_container_width=True)

else:
    st.warning("No hay coordenadas válidas para mostrar en el mapa")