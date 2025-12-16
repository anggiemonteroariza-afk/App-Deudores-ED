import streamlit as st
import pandas as pd
import os
from datetime import date
import matplotlib.pyplot as plt
import io

# ---------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------------
st.set_page_config(
    page_title="Mini App Deudores",
    page_icon="💸",
    layout="wide"
)

FILE_PATH = "DeudoresPrueba.xlsx"

# ---------------------------------------------------------
# CARGA DEL ARCHIVO
# ---------------------------------------------------------
if os.path.exists(FILE_PATH):
    df = pd.read_excel(FILE_PATH)
else:
    df = pd.DataFrame(
        columns=["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"]
    )

# Asegurar columnas
for col in ["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"]:
    if col not in df.columns:
        df[col] = None

# Normalizar cliente
df["Cliente"] = (
    df["Cliente"]
    .astype(str)
    .str.strip()
    .str.upper()
)

# Fecha
df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date

# Valor
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)

# Pagado
df["Pagado"] = df["Pagado"].astype(bool)

# Eliminar vacíos
df = df.dropna(how="all")

# Eliminar pagados
df = df[df["Pagado"] != True]

# Ordenar
df = df.sort_values(by="Cliente")

# Reset consecutivo
df = df.reset_index(drop=True)
df["Consecutivo"] = df.index + 1

# Guardar
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
        st.error("El nombre del cliente es obligatorio.")
    else:
        nuevo = {
            "Consecutivo": len(df) + 1,
            "Cliente": cliente,
            "Fecha": fecha,
            "Valor": valor,
            "Pagado": False
        }
        df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
        save(df)
        st.success("Registro guardado correctamente.")
        st.rerun()

# ---------------------------------------------------------
# FILTRO CLIENTE
# ---------------------------------------------------------
st.subheader("🔎 Filtro por cliente")

clientes = sorted(df["Cliente"].unique())
filtro = st.selectbox(
    "Selecciona un cliente (opcional)",
    ["Todos"] + clientes
)

df_view = df if filtro == "Todos" else df[df["Cliente"] == filtro]

# ---------------------------------------------------------
# TABLA EDITABLE
# ---------------------------------------------------------
st.subheader("✏️ Editar y marcar pagos en la tabla")

df_edit = df_view.copy()
df_edit["Fecha"] = pd.to_datetime(df_edit["Fecha"])

edited = st.data_editor(
    df_edit,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Pagado": st.column_config.CheckboxColumn("Pagado"),
        "Fecha": st.column_config.DateColumn(
            "Fecha", max_value=date.today()
        ),
        "Valor": st.column_config.NumberColumn(
            "Valor",
            min_value=0,
            step=1000,
            format="$%,.0f"
        )
    },
    disabled=["Consecutivo"]
)

# ---------------------------------------------------------
# GUARDAR CAMBIOS
# ---------------------------------------------------------
if st.button("💾 Guardar cambios de la tabla"):
    df_updated = df.copy()

    for _, row in edited.iterrows():
        idx = df_updated[
            df_updated["Consecutivo"] == row["Consecutivo"]
        ].index

        if len(idx) > 0:
            i = idx[0]
            df_updated.at[i, "Cliente"] = row["Cliente"].strip().upper()
            df_updated.at[i, "Fecha"] = row["Fecha"].date()
            df_updated.at[i, "Valor"] = float(row["Valor"])
            df_updated.at[i, "Pagado"] = bool(row["Pagado"])

    # Eliminar pagados
    df_updated = df_updated[df_updated["Pagado"] != True]

    # Reordenar
    df_updated = df_updated.sort_values(by="Cliente")
    df_updated = df_updated.reset_index(drop=True)
    df_updated["Consecutivo"] = df_updated.index + 1

    save(df_updated)
    st.success("Cambios guardados correctamente.")
    st.rerun()

# ---------------------------------------------------------
# TOTALES
# ---------------------------------------------------------
st.subheader("📊 Total por cliente")

if len(df) == 0:
    st.info("No hay deudores activos.")
else:
    totales = (
        df.groupby("Cliente", as_index=False)["Valor"]
        .sum()
    )
    totales["Valor"] = totales["Valor"].apply(
        lambda x: f"${x:,.0f}"
    )
    st.dataframe(totales, use_container_width=True)

    gran_total = df["Valor"].sum()
    st.subheader(
        f"💰 Gran total de todos los deudores: **${gran_total:,.0f}**"
    )

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

    st.image(buffer_img, caption="Total por cliente")

    st.download_button(
        "⬇️ Descargar imagen (PNG)",
        buffer_img,
        file_name="Total_por_cliente.png",
        mime="image/png"
    )

# ---------------------------------------------------------
# DESCARGAR EXCEL
# ---------------------------------------------------------
st.subheader("⬇️ Descargar Excel actualizado")

with open(FILE_PATH, "rb") as f:
    st.download_button(
        "Descargar archivo",
        f,
        file_name="DeudoresPrueba.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
