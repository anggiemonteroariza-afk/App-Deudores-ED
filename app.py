import streamlit as st
import pandas as pd
import os
from datetime import date
import matplotlib.pyplot as plt
import io
import tempfile
import shutil
from git import Repo

# ---------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------------
st.set_page_config(
    page_title="Mini App Deudores",
    page_icon="💸",
    layout="wide"
)

FILE_PATH = "DeudoresPrueba.xlsx"

# Secrets
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_URL = st.secrets["REPO_URL"]

# ---------------------------------------------------------
# FUNCIÓN GUARDAR + PUSH A GITHUB
# ---------------------------------------------------------
def save_and_push(data: pd.DataFrame):
    temp_dir = tempfile.mkdtemp()

    try:
        auth_repo_url = REPO_URL.replace(
            "https://",
            f"https://{GITHUB_TOKEN}@"
        )

        repo = Repo.clone_from(auth_repo_url, temp_dir)

        excel_path = os.path.join(temp_dir, FILE_PATH)
        data.to_excel(excel_path, index=False)

        repo.git.add(FILE_PATH)
        repo.index.commit("Actualización automática desde Streamlit")
        repo.remote(name="origin").push()

    finally:
        shutil.rmtree(temp_dir)

# ---------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------
if os.path.exists(FILE_PATH):
    df = pd.read_excel(FILE_PATH)
else:
    df = pd.DataFrame(columns=["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"])

# Asegurar columnas
for col in ["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"]:
    if col not in df.columns:
        df[col] = None

# Normalización
df["Cliente"] = df["Cliente"].astype(str).str.strip().str.upper()
df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

def normalize_paid(x):
    return str(x).upper() in ["1", "TRUE", "SI", "SÍ", "YES", "PAGADO"]

df["Pagado"] = df["Pagado"].apply(normalize_paid)

# Limpiar
df = df.dropna(how="all")
df = df[df["Pagado"] != True]
df = df.sort_values(by="Cliente")
df = df.reset_index(drop=True)
df["Consecutivo"] = df.index + 1

# ---------------------------------------------------------
# TÍTULO
# ---------------------------------------------------------
st.title("💸 App de Registro de Deudores")

# ---------------------------------------------------------
# REGISTRAR NUEVO DEUDOR
# ---------------------------------------------------------
st.subheader("➕ Registrar nuevo deudor")

col1, col2, col3 = st.columns(3)

with col1:
    cliente = st.text_input("Cliente").strip().upper()

with col2:
    fecha = st.date_input(
        "Fecha",
        value=date.today(),
        max_value=date.today(),
        key="fecha_nuevo"
    )

with col3:
    valor = st.number_input(
        "Valor (COP)",
        min_value=0.0,
        step=1000.0,
        format="%.0f"
    )

if st.button("Guardar nuevo registro"):
    if cliente == "":
        st.error("El nombre del cliente es obligatorio.")
    else:
        new_row = {
            "Consecutivo": len(df) + 1,
            "Cliente": cliente,
            "Fecha": fecha,
            "Valor": valor,
            "Pagado": False
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_and_push(df)
        st.success("Registro guardado exitosamente.")
        st.rerun()

# ---------------------------------------------------------
# FILTRO
# ---------------------------------------------------------
st.subheader("🔎 Filtro por cliente")

clientes_unicos = sorted(df["Cliente"].unique())
filtro_cliente = st.selectbox(
    "Selecciona un cliente (opcional)",
    ["Todos"] + clientes_unicos
)

df_editable = df if filtro_cliente == "Todos" else df[df["Cliente"] == filtro_cliente]

# ---------------------------------------------------------
# TABLA EDITABLE
# ---------------------------------------------------------
st.subheader("✏️ Editar directamente en la tabla")

df_temp = df_editable.copy()
df_temp["Fecha"] = pd.to_datetime(df_temp["Fecha"])

edited = st.data_editor(
    df_temp,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Pagado": st.column_config.CheckboxColumn("Pagado"),
        "Fecha": st.column_config.DateColumn("Fecha", max_value=date.today()),
        "Valor": st.column_config.NumberColumn(
            "Valor",
            min_value=0.0,
            step=1000.0,
            format="%.0f"
        )
    },
    disabled=["Consecutivo"]
)

if st.button("💾 Guardar cambios de la tabla"):
    df_updated = df.copy()

    for _, row in edited.iterrows():
        idx = df[df["Consecutivo"] == row["Consecutivo"]].index
        if len(idx) > 0:
            i = idx[0]
            df_updated.at[i, "Cliente"] = row["Cliente"].strip().upper()
            df_updated.at[i, "Fecha"] = row["Fecha"].date()
            df_updated.at[i, "Valor"] = float(row["Valor"])
            df_updated.at[i, "Pagado"] = bool(row["Pagado"])

    df_updated = df_updated[df_updated["Pagado"] != True]
    df_updated = df_updated.sort_values(by="Cliente")
    df_updated = df_updated.reset_index(drop=True)
    df_updated["Consecutivo"] = df_updated.index + 1

    save_and_push(df_updated)
    st.success("Cambios guardados correctamente.")
    st.rerun()

# ---------------------------------------------------------
# TOTALES
# ---------------------------------------------------------
st.subheader("📊 Total por cliente")

if len(df) > 0:
    totales = df.groupby("Cliente")["Valor"].sum().reset_index()
    totales["Valor"] = totales["Valor"].apply(lambda x: f"${x:,.0f}")
    st.dataframe(totales, use_container_width=True)

    gran_total = df["Valor"].sum()
    st.subheader(f"💰 Gran total: **${gran_total:,.0f}**")
else:
    st.info("No hay deudores activos.")

# ---------------------------------------------------------
# IMAGEN
# ---------------------------------------------------------
st.subheader("🖼️ Descargar imagen del total por cliente")

if len(df) > 0:
    fig, ax = plt.subplots(figsize=(6, len(totales) * 0.5 + 1))
    ax.axis("off")

    tabla = ax.table(
        cellText=totales.values,
        colLabels=totales.columns,
        cellLoc="center",
        loc="center"
    )

    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    tabla.scale(1, 1.5)

    buffer_img = io.BytesIO()
    plt.savefig(buffer_img, format="png", bbox_inches="tight", dpi=300)
    buffer_img.seek(0)

    st.image(buffer_img)
    st.download_button(
        "⬇️ Descargar imagen (PNG)",
        buffer_img,
        "Total_por_cliente.png",
        "image/png"
    )
