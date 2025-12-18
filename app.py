import streamlit as st
import pandas as pd
import os
from datetime import date
import matplotlib.pyplot as plt
import io
from git import Repo

# ---------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------
st.set_page_config(page_title="Mini App Deudores", page_icon="💸", layout="wide")

FILE_PATH = "DeudoresPrueba.xlsx"
REPO_URL = st.secrets["REPO_URL"]
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# ---------------------------------------------------------
# CLONAR REPO SI NO EXISTE
# ---------------------------------------------------------
if not os.path.exists(".git"):
    Repo.clone_from(
        REPO_URL.replace("https://", f"https://{GITHUB_TOKEN}@"),
        "."
    )

repo = Repo(".")

# ---------------------------------------------------------
# CARGA SEGURA DEL ARCHIVO
# ---------------------------------------------------------
def load_data():
    try:
        return pd.read_excel(FILE_PATH)
    except Exception:
        return pd.DataFrame(
            columns=["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"]
        )

df = load_data()

# Normalización
df["Cliente"] = df.get("Cliente", "").astype(str).str.strip().str.upper()
df["Fecha"] = pd.to_datetime(df.get("Fecha"), errors="coerce").dt.date
df["Valor"] = pd.to_numeric(df.get("Valor"), errors="coerce").fillna(0)

def normalize_paid(x):
    return str(x).upper() in ["1", "TRUE", "PAGADO", "SI", "SÍ", "YES"]

df["Pagado"] = df.get("Pagado", False).apply(normalize_paid)

# Eliminar vacíos y pagados
df = df.dropna(how="all")
df = df[df["Pagado"] != True]

# Ordenar y consecutivo
df = df.sort_values(by="Cliente").reset_index(drop=True)
df["Consecutivo"] = df.index + 1

# ---------------------------------------------------------
# GUARDAR + PUSH A GITHUB
# ---------------------------------------------------------
def save_and_push(data):
    data.to_excel(FILE_PATH, index=False)
    repo.git.add(FILE_PATH)
    repo.index.commit("Actualización de deudores")
    repo.remote().push()

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
st.title("💸 App de Registro de Deudores")

# ---------------------------------------------------------
# NUEVO REGISTRO
# ---------------------------------------------------------
st.subheader("➕ Registrar nuevo deudor")

c1, c2, c3 = st.columns(3)

with c1:
    cliente = st.text_input("Cliente").strip().upper()
with c2:
    fecha = st.date_input("Fecha", value=date.today(), max_value=date.today())
with c3:
    valor = st.number_input(
        "Valor (COP)",
        min_value=0,
        step=1000,
        format="%d"
    )

if st.button("Guardar nuevo registro"):
    if cliente == "":
        st.error("El cliente es obligatorio")
    else:
        df.loc[len(df)] = [
            len(df) + 1,
            cliente,
            fecha,
            valor,
            False
        ]
        save_and_push(df)
        st.success("Registro guardado")
        st.rerun()

# ---------------------------------------------------------
# FILTRO
# ---------------------------------------------------------
st.subheader("🔎 Filtro por cliente")
clientes = ["Todos"] + sorted(df["Cliente"].unique().tolist())
filtro = st.selectbox("Cliente", clientes)

df_view = df if filtro == "Todos" else df[df["Cliente"] == filtro]

# ---------------------------------------------------------
# TABLA EDITABLE
# ---------------------------------------------------------
st.subheader("✏️ Editar / Marcar como pagado")

edited = st.data_editor(
    df_view,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Pagado": st.column_config.CheckboxColumn("Pagado"),
        "Fecha": st.column_config.DateColumn("Fecha", max_value=date.today()),
        "Valor": st.column_config.NumberColumn(
            "Valor",
            min_value=0,
            step=1000,
            format="%d"
        )
    },
    disabled=["Consecutivo"]
)

if st.button("💾 Guardar cambios"):
    for _, row in edited.iterrows():
        idx = df[df["Consecutivo"] == row["Consecutivo"]].index
        if len(idx):
            i = idx[0]
            df.at[i, "Cliente"] = row["Cliente"].strip().upper()
            df.at[i, "Fecha"] = row["Fecha"]
            df.at[i, "Valor"] = int(row["Valor"])
            df.at[i, "Pagado"] = bool(row["Pagado"])

    df = df[df["Pagado"] != True]
    df = df.sort_values(by="Cliente").reset_index(drop=True)
    df["Consecutivo"] = df.index + 1

    save_and_push(df)
    st.success("Cambios guardados")
    st.rerun()

# ---------------------------------------------------------
# TOTALES
# ---------------------------------------------------------
st.subheader("📊 Total por cliente")

totales = df.groupby("Cliente")["Valor"].sum().reset_index()
totales["Valor"] = totales["Valor"].apply(lambda x: f"${x:,.0f}")

st.dataframe(totales, use_container_width=True)

gran_total = df["Valor"].sum()
st.subheader(f"💰 Gran total: **${gran_total:,.0f}**")

# ---------------------------------------------------------
# IMAGEN
# ---------------------------------------------------------
st.subheader("🖼️ Descargar imagen")

fig, ax = plt.subplots(figsize=(6, len(totales) * 0.5 + 1))
ax.axis("off")
ax.table(
    cellText=totales.values,
    colLabels=totales.columns,
    cellLoc="center",
    loc="center"
)

buf = io.BytesIO()
plt.savefig(buf, format="png", bbox_inches="tight", dpi=300)
buf.seek(0)

st.image(buf)
st.download_button("Descargar PNG", buf, "total_por_cliente.png", "image/png")
