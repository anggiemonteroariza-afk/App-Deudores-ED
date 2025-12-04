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
# CARGA DE BASE DE DATOS
# ---------------------------------------------------------
if os.path.exists(FILE_PATH):
    df = pd.read_excel(FILE_PATH)
else:
    df = pd.DataFrame(columns=["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"])

# Asegurar estructura correcta
for col in ["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"]:
    if col not in df.columns:
        df[col] = None

# Convertir fecha sin hora
df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date

# Normalizar nombres de clientes
df["Cliente"] = df["Cliente"].astype(str).str.strip().str.upper()

# Eliminar filas vacías
df = df.dropna(how="all")

# Eliminar registros pagados
df = df[df["Pagado"] != True]

# Orden alfabético
df = df.sort_values(by="Cliente", ascending=True, na_position='last')

# Reset de consecutivos
df = df.reset_index(drop=True)
df["Consecutivo"] = df.index + 1

def save(dataframe=None):
    if dataframe is None:
        dataframe = df
    dataframe.to_excel(FILE_PATH, index=False)

# ---------------------------------------------------------
# TÍTULO
# ---------------------------------------------------------
st.title("💸 App de Registro de Deudores")

# ---------------------------------------------------------
# SECCIÓN 1: REGISTRAR NUEVO DEUDOR
# ---------------------------------------------------------
st.subheader("➕ Registrar nuevo deudor")

col1, col2, col3 = st.columns(3)

with col1:
    cliente = st.text_input("Cliente")
with col2:
    fecha = st.date_input(
        "Fecha",
        value=date.today(),
        max_value=date.today(), 
        key="fecha_nuevo"
    )
with col3:
    valor = st.number_input("Valor de la deuda (COP)", min_value=0.0, format="%.0f")

if st.button("Guardar nuevo registro"):
    if cliente.strip() == "":
        st.error("El nombre del cliente es obligatorio.")
    else:
        new_row = {
            "Consecutivo": len(df) + 1,
            "Cliente": cliente.strip().upper(),
            "Fecha": fecha,
            "Valor": valor,
            "Pagado": False
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save(df)
        st.success("Registro guardado exitosamente.")
        st.rerun()

# ---------------------------------------------------------
# SECCIÓN 2: FILTRO DE CLIENTES
# ---------------------------------------------------------
st.subheader("🔎 Filtro por cliente")

clientes_unicos = sorted(df["Cliente"].dropna().unique())
filtro_cliente = st.selectbox("Selecciona un cliente (opcional)", ["Todos"] + list(clientes_unicos))

df_display = df if filtro_cliente == "Todos" else df[df["Cliente"] == filtro_cliente]

# ---------------------------------------------------------
# SECCIÓN 3: TABLA EDITABLE (DEUDORES ACTIVOS)
# ---------------------------------------------------------
st.subheader("📋 Deudores activos (editable)")

editable_df = df_display.copy()

# Formato para mostrar
editable_df["Valor"] = editable_df["Valor"].astype(float)

# Editor de tabla
edited_df = st.data_editor(
    editable_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Fecha": st.column_config.DateColumn(
            "Fecha",
            max_value=date.today(),
        ),
        "Valor": st.column_config.NumberColumn(
            "Valor",
            min_value=0,
            step=1000,
            format="%.0f"
        ),
        "Pagado": st.column_config.CheckboxColumn("Pagado")
    }
)

# BOTÓN PARA GUARDAR CAMBIOS HECHOS EN LA TABLA
if st.button("💾 Guardar cambios"):
    # Actualizar df original
    df.update(edited_df)

    # Normalizar clientes
    df["Cliente"] = df["Cliente"].astype(str).str.strip().str.upper()

    # Eliminar pagados
    df = df[df["Pagado"] != True]

    # Ordenar
    df = df.sort_values(by="Cliente", ascending=True)

    # Reset consecutivos
    df = df.reset_index(drop=True)
    df["Consecutivo"] = df.index + 1

    save(df)
    st.success("Cambios guardados correctamente.")
    st.rerun()

# ---------------------------------------------------------
# SECCIÓN 4: TOTAL POR CLIENTE
# ---------------------------------------------------------
st.subheader("📊 Total por cliente")

if len(df) == 0:
    st.info("No hay deudores activos.")
else:
    totales = df.groupby(df["Cliente"].str.strip().str.upper())["Valor"].sum().reset_index()
    totales["Valor"] = totales["Valor"].apply(lambda x: f"${x:,.0f}")

    st.dataframe(totales, use_container_width=True)

# Gran total
if len(df) > 0:
    gran_total = df["Valor"].sum()
    st.subheader(f"💰 Gran total de todos los deudores: **${gran_total:,.0f}**")

# ---------------------------------------------------------
# SECCIÓN 5: DESCARGAR IMAGEN
# ---------------------------------------------------------
st.subheader("🖼️ Descargar imagen del total por cliente")

if len(df) > 0:
    fig, ax = plt.subplots(figsize=(6, len(totales) * 0.5 + 1))
    ax.axis('off')

    tabla = ax.table(
        cellText=totales.values,
        colLabels=totales.columns,
        cellLoc='center',
        loc='center'
    )
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    tabla.scale(1, 1.5)

    buffer_img = io.BytesIO()
    plt.savefig(buffer_img, format='png', bbox_inches='tight', dpi=300)
    buffer_img.seek(0)

    st.image(buffer_img, caption="Total por cliente")

    st.download_button(
        label="⬇️ Descargar imagen (PNG)",
        data=buffer_img,
        file_name="Total_por_cliente.png",
        mime="image/png"
    )

# ---------------------------------------------------------
# SECCIÓN 6: DESCARGAR EXCEL
# ---------------------------------------------------------
st.subheader("⬇️ Descargar Excel actualizado")

df.to_excel("DeudoresPrueba.xlsx", index=False)

with open("DeudoresPrueba.xlsx", "rb") as f:
    st.download_button(
        label="Descargar archivo",
        data=f,
        file_name="DeudoresPrueba.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
