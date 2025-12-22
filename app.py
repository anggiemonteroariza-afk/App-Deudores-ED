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
# CARGA DE DATOS
# ---------------------------------------------------------
if os.path.exists(FILE_PATH):
    try:
        df = pd.read_excel(FILE_PATH)
    except Exception:
        df = pd.DataFrame(columns=["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"])
else:
    df = pd.DataFrame(columns=["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"])

# Asegurar columnas
for col in ["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"]:
    if col not in df.columns:
        df[col] = None

# Limpieza básica
df["Cliente"] = df["Cliente"].astype(str).str.strip().str.upper()
df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)

df["Pagado"] = df["Pagado"].astype(bool)

# Eliminar filas completamente vacías
df = df.dropna(how="all")

# Eliminar pagados
df = df[df["Pagado"] != True]

# Ordenar
df = df.sort_values(by="Cliente")

# Reindexar consecutivo
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
        st.error("El cliente es obligatorio.")
    else:
        nuevo = {
            "Consecutivo": len(df) + 1,
            "Cliente": cliente,
            "Fecha": fecha,
            "Valor": valor,
            "Pagado": False
        }
        df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
        df.to_excel(FILE_PATH, index=False)
        st.success("Registro guardado.")
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

df_edit = df_view.copy()
df_edit["Fecha"] = pd.to_datetime(df_edit["Fecha"])

edited = st.data_editor(
    df_edit,
    use_container_width=True,
    hide_index=True,
    disabled=["Consecutivo"],
    column_config={
        "Fecha": st.column_config.DateColumn(
            "Fecha",
            max_value=date.today()
        ),
        "Valor": st.column_config.NumberColumn(
            "Valor (COP)",
            min_value=0,
            step=1000,
            format="%.0f"
        ),
        "Pagado": st.column_config.CheckboxColumn("Pagado")
    }
)

if st.button("💾 Guardar cambios"):
    df_new = df.copy()

    for _, row in edited.iterrows():
        idx = df_new[df_new["Consecutivo"] == row["Consecutivo"]].index
        if len(idx) > 0:
            i = idx[0]
            df_new.at[i, "Cliente"] = row["Cliente"].strip().upper()
            df_new.at[i, "Fecha"] = row["Fecha"].date()
            df_new.at[i, "Valor"] = float(row["Valor"])
            df_new.at[i, "Pagado"] = bool(row["Pagado"])

    df_new = df_new[df_new["Pagado"] != True]
    df_new = df_new.sort_values(by="Cliente")
    df_new = df_new.reset_index(drop=True)
    df_new["Consecutivo"] = df_new.index + 1

    df_new.to_excel(FILE_PATH, index=False)
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

    ax.table(
        cellText=totales.values,
        colLabels=totales.columns,
        cellLoc="center",
        loc="center"
    )

    buffer_img = io.BytesIO()
    plt.savefig(buffer_img, format="png", bbox_inches="tight", dpi=300)
    buffer_img.seek(0)

    st.image(buffer_img)
    st.download_button(
        "⬇️ Descargar imagen",
        data=buffer_img,
        file_name="Total_por_cliente.png",
        mime="image/png"
    )

# ---------------------------------------------------------
# DESCARGAR EXCEL
# ---------------------------------------------------------
st.subheader("⬇️ Descargar Excel actualizado")

output = io.BytesIO()
df.to_excel(output, index=False)
output.seek(0)

st.download_button(
    "Descargar Excel",
    data=output,
    file_name="DeudoresPrueba.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
