import streamlit as st
import pandas as pd
import os
from datetime import date
import matplotlib.pyplot as plt
import io

# ---------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------------
st.set_page_config(page_title="Mini App Deudores", page_icon="💸", layout="wide")

FILE_PATH = "DeudoresPrueba.xlsx"

# ---------------------------------------------------------
# CARGA SEGURA DEL ARCHIVO (ANTI-CORRUPCIÓN)
# ---------------------------------------------------------
def load_data():
    try:
        return pd.read_excel(FILE_PATH)
    except Exception:
        # Respaldar archivo dañado si existe
        if os.path.exists(FILE_PATH):
            os.rename(FILE_PATH, "DeudoresPrueba_CORRUPTO.xlsx")

        # Crear DataFrame limpio
        return pd.DataFrame(
            columns=["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"]
        )

df = load_data()

# ---------------------------------------------------------
# NORMALIZACIÓN DE DATOS
# ---------------------------------------------------------
for col in ["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"]:
    if col not in df.columns:
        df[col] = None

df["Cliente"] = (
    df["Cliente"]
    .astype(str)
    .str.strip()
    .str.upper()
)

df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

def normalize_paid(x):
    return str(x).upper() in ["1", "TRUE", "PAGADO", "SI", "SÍ", "YES"]

df["Pagado"] = df["Pagado"].apply(normalize_paid)

df = df.dropna(how="all")
df = df[df["Pagado"] != True]
df = df.sort_values(by="Cliente")
df = df.reset_index(drop=True)
df["Consecutivo"] = df.index + 1

def save(data):
    data.to_excel(FILE_PATH, index=False)

# ---------------------------------------------------------
# TÍTULO
# ---------------------------------------------------------
st.title("💸 App de Registro de Deudores")

# ---------------------------------------------------------
# REGISTRAR NUEVO DEUDOR
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
        df = pd.concat(
            [df, pd.DataFrame([{
                "Consecutivo": len(df) + 1,
                "Cliente": cliente,
                "Fecha": fecha,
                "Valor": valor,
                "Pagado": False
            }])],
            ignore_index=True
        )
        save(df)
        st.success("Registro guardado")
        st.rerun()

# ---------------------------------------------------------
# FILTRO
# ---------------------------------------------------------
st.subheader("🔎 Filtro por cliente")

clientes = sorted(df["Cliente"].unique())
filtro = st.selectbox("Cliente", ["Todos"] + clientes)

df_view = df if filtro == "Todos" else df[df["Cliente"] == filtro]

# ---------------------------------------------------------
# TABLA EDITABLE
# ---------------------------------------------------------
st.subheader("✏️ Editar / Marcar como pagado")

df_temp = df_view.copy()
df_temp["Fecha"] = pd.to_datetime(df_temp["Fecha"])

edited = st.data_editor(
    df_temp,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Pagado": st.column_config.CheckboxColumn("Pagado"),
        "Fecha": st.column_config.DateColumn(
            "Fecha", max_value=date.today()
        ),
        "Valor": st.column_config.NumberColumn(
            "Valor (COP)", min_value=0.0, step=1000.0, format="%.0f"
        )
    },
    disabled=["Consecutivo"]
)

if st.button("💾 Guardar cambios"):
    df_updated = df.copy()

    for _, row in edited.iterrows():
        idx = df_updated[df_updated["Consecutivo"] == row["Consecutivo"]].index
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

    save(df_updated)
    st.success("Cambios guardados correctamente")
    st.rerun()

# ---------------------------------------------------------
# TOTALES
# ---------------------------------------------------------
st.subheader("📊 Total por cliente")

if len(df) > 0:
    totales = df.groupby("Cliente", as_index=False)["Valor"].sum()
    totales["Valor"] = totales["Valor"].apply(lambda x: f"${x:,.0f}")
    st.dataframe(totales, use_container_width=True)

    gran_total = df["Valor"].sum()
    st.subheader(f"💰 Gran total: **${gran_total:,.0f}**")
else:
    st.info("No hay deudores activos")

# ---------------------------------------------------------
# IMAGEN
# ---------------------------------------------------------
st.subheader("🖼️ Descargar imagen")

if len(df) > 0:
    fig, ax = plt.subplots(figsize=(6, len(totales) * 0.5 + 1))
    ax.axis("off")

    tabla = ax.table(
        cellText=totales.values,
        colLabels=totales.columns,
        loc="center",
        cellLoc="center"
    )

    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    tabla.scale(1, 1.5)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=300, bbox_inches="tight")
    buf.seek(0)

    st.image(buf)
    st.download_button(
        "⬇️ Descargar imagen",
        buf,
        "Total_por_cliente.png",
        "image/png"
    )

# ---------------------------------------------------------
# DESCARGA EXCEL
# ---------------------------------------------------------
st.subheader("⬇️ Descargar Excel")

buffer = io.BytesIO()
df.to_excel(buffer, index=False)
buffer.seek(0)

st.download_button(
    "Descargar archivo",
    buffer,
    "DeudoresPrueba.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
