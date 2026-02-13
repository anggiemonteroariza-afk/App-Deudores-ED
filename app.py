import streamlit as st
import pandas as pd
import os
from datetime import date
import matplotlib.pyplot as plt
import io
from supabase import create_client
from dotenv import load_dotenv

# ---------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------
st.set_page_config(
    page_title="Mini App Deudores",
    page_icon="💸",
    layout="wide"
)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLE_NAME = "deudores"

# ---------------------------------------------------------
# CARGAR DATOS DESDE SUPABASE
# ---------------------------------------------------------
@st.cache_data(ttl=5)
def cargar_datos():
    response = supabase.table(TABLE_NAME).select("*").execute()
    data = response.data
    if data:
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(columns=["id", "cliente", "fecha", "valor", "pagado"])
    return df

df = cargar_datos()

if not df.empty:
    df["cliente"] = df["cliente"].astype(str).str.strip().str.upper()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    df["pagado"] = df["pagado"].astype(bool)

    df = df[df["pagado"] != True]
    df = df.sort_values(by="cliente").reset_index(drop=True)

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
        max_value=date.today()
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
        supabase.table(TABLE_NAME).insert({
            "cliente": cliente,
            "fecha": str(fecha),
            "valor": valor,
            "pagado": False
        }).execute()

        st.success("Registro guardado.")
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------
# FILTRO
# ---------------------------------------------------------
st.subheader("🔎 Filtro por cliente")

if not df.empty:
    clientes = sorted(df["cliente"].unique())
else:
    clientes = []

filtro = st.selectbox("Cliente", ["Todos"] + clientes)

df_view = df if filtro == "Todos" else df[df["cliente"] == filtro]

# ---------------------------------------------------------
# TABLA EDITABLE
# ---------------------------------------------------------
st.subheader("✏️ Editar / Marcar como pagado")

if not df_view.empty:

    df_edit = df_view.copy()

    edited = st.data_editor(
        df_edit,
        use_container_width=True,
        hide_index=True,
        disabled=["id"],
        column_config={
            "fecha": st.column_config.DateColumn(
                "Fecha",
                max_value=date.today()
            ),
            "valor": st.column_config.NumberColumn(
                "Valor (COP)",
                min_value=0,
                step=1000,
                format="%.0f"
            ),
            "pagado": st.column_config.CheckboxColumn("Pagado")
        }
    )

    if st.button("💾 Guardar cambios"):

        for _, row in edited.iterrows():
            supabase.table(TABLE_NAME).update({
                "cliente": row["cliente"].strip().upper(),
                "fecha": str(row["fecha"].date()),
                "valor": float(row["valor"]),
                "pagado": bool(row["pagado"])
            }).eq("id", row["id"]).execute()

        st.success("Cambios guardados correctamente.")
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------
# TOTALES
# ---------------------------------------------------------
st.subheader("📊 Total por cliente")

if not df.empty:

    totales = df.groupby("cliente")["valor"].sum().reset_index()

    st.dataframe(totales, use_container_width=True)

    gran_total = df["valor"].sum()
    st.subheader(f"💰 Gran total: **${gran_total:,.0f}**")

else:
    st.info("No hay deudores activos.")

# ---------------------------------------------------------
# IMAGEN
# ---------------------------------------------------------
st.subheader("🖼️ Descargar imagen del total por cliente")

if not df.empty:

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

if not df.empty:

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        "Descargar Excel",
        data=output,
        file_name="Deudores.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
