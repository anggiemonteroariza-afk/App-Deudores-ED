import streamlit as st
import pandas as pd
import os
from datetime import date
import matplotlib.pyplot as plt
import io
from git import Repo
import tempfile
import shutil

# ---------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------------
st.set_page_config(page_title="Mini App Deudores", page_icon="💸", layout="wide")

FILE_PATH = "DeudoresPrueba.xlsx"
REPO_URL = "https://github.com/anggiemonteroariza-afk/App-Deudores-ED.git"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# ---------------------------------------------------------
# FUNCIÓN: GUARDAR Y SUBIR A GITHUB
# ---------------------------------------------------------
def save_and_push(data):
    temp_dir = tempfile.mkdtemp()

    try:
        repo = Repo.clone_from(
            REPO_URL,
            temp_dir,
            env={"GIT_ASKPASS": "echo", "GIT_USERNAME": GITHUB_TOKEN}
        )

        excel_path = os.path.join(temp_dir, FILE_PATH)
        data.to_excel(excel_path, index=False)

        repo.git.add(FILE_PATH)
        repo.index.commit("Actualización automática desde Streamlit")
        repo.remote().push()

    finally:
        shutil.rmtree(temp_dir)

# ---------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------
if os.path.exists(FILE_PATH):
    df = pd.read_excel(FILE_PATH)
else:
    df = pd.DataFrame(columns=["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"])

# Normalización
df["Cliente"] = df["Cliente"].astype(str).str.strip().str.upper()
df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)

def normalize_paid(x):
    return str(x).upper() in ["TRUE", "1", "SI", "SÍ", "PAGADO"]

df["Pagado"] = df["Pagado"].apply(normalize_paid)

# Eliminar pagados
df = df[df["Pagado"] != True]

# Ordenar y reindexar
df = df.sort_values("Cliente").reset_index(drop=True)
df["Consecutivo"] = df.index + 1

# ---------------------------------------------------------
# TÍTULO
# ---------------------------------------------------------
st.title("💸 App de Registro de Deudores")

# ---------------------------------------------------------
# REGISTRO NUEVO
# ---------------------------------------------------------
st.subheader("➕ Registrar nuevo deudor")

c1, c2, c3 = st.columns(3)

with c1:
    cliente = st.text_input("Cliente").strip().upper()

with c2:
    fecha = st.date_input(
        "Fecha",
        value=date.today(),
        max_value=date.today(),
        key="fecha_nuevo"
    )

with c3:
    valor = st.number_input(
        "Valor (COP)",
        min_value=0.0,
        step=1000.0,
        format="%.0f"
    )

if st.button("Guardar nuevo registro"):
    if cliente == "":
        st.error("El cliente es obligatorio")
    else:
        new = {
            "Consecutivo": len(df) + 1,
            "Cliente": cliente,
            "Fecha": fecha,
            "Valor": valor,
            "Pagado": False
        }
        df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
        save_and_push(df)
        st.success("Registro guardado y sincronizado")
        st.rerun()

# ---------------------------------------------------------
# FILTRO
# ---------------------------------------------------------
st.subheader("🔎 Filtro por cliente")
clientes = ["Todos"] + sorted(df["Cliente"].unique())
filtro = st.selectbox("Cliente", clientes)

df_view = df if filtro == "Todos" else df[df["Cliente"] == filtro]

# ---------------------------------------------------------
# TABLA EDITABLE
# ---------------------------------------------------------
st.subheader("✏️ Editar directamente en la tabla")

df_edit = df_view.copy()
df_edit["Fecha"] = pd.to_datetime(df_edit["Fecha"])

edited = st.data_editor(
    df_edit,
    use_container_width=True,
    hide_index=True,
    disabled=["Consecutivo"],
    column_config={
        "Pagado": st.column_config.CheckboxColumn("Pagado"),
        "Fecha": st.column_config.DateColumn("Fecha", max_value=date.today()),
        "Valor": st.column_config.NumberColumn(
            "Valor", min_value=0.0, step=1000.0, format="%.0f"
        )
    }
)

if st.button("💾 Guardar cambios"):
    df_new = df.copy()

    for _, r in edited.iterrows():
        idx = df_new[df_new["Consecutivo"] == r["Consecutivo"]].index
        if len(idx) > 0:
            i = idx[0]
            df_new.at[i, "Cliente"] = r["Cliente"]
            df_new.at[i, "Fecha"] = r["Fecha"].date()
            df_new.at[i, "Valor"] = float(r["Valor"])
            df_new.at[i, "Pagado"] = bool(r["Pagado"])

    df_new = df_new[df_new["Pagado"] != True]
    df_new = df_new.sort_values("Cliente").reset_index(drop=True)
    df_new["Consecutivo"] = df_new.index + 1

    save_and_push(df_new)
    st.success("Cambios guardados y sincronizados")
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
st.subheader("🖼️ Imagen del total por cliente")

fig, ax = plt.subplots(figsize=(6, len(totales) * 0.5 + 1))
ax.axis("off")

table = ax.table(
    cellText=totales.values,
    colLabels=totales.columns,
    cellLoc="center",
    loc="center"
)
table.scale(1, 1.5)

buf = io.BytesIO()
plt.savefig(buf, format="png", dpi=300, bbox_inches="tight")
buf.seek(0)

st.image(buf)
st.download_button(
    "⬇️ Descargar imagen",
    data=buf,
    file_name="total_por_cliente.png",
    mime="image/png"
)
