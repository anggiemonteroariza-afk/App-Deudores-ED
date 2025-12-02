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

# Eliminar filas completamente vacías
df = df.dropna(how="all")

# Eliminar registros pagados
df = df[df["Pagado"] != True]

# Orden alfabético de clientes
df = df.sort_values(by="Cliente", ascending=True, na_position='last')

# Reset consecutivos
df = df.reset_index(drop=True)
df["Consecutivo"] = df.index + 1

# Función para guardar
def save():
    df.to_excel(FILE_PATH, index=False)

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
    fecha = st.date_input("Fecha", value=date.today())
with col3:
    valor = st.number_input("Valor de la deuda (COP)", min_value=0.0, format="%.0f")

if st.button("Guardar nuevo registro"):
    if cliente.strip() == "":
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
        save()
        st.success("Registro guardado exitosamente.")
        st.rerun()

# ---------------------------------------------------------
# SECCIÓN 2: FILTRO DE CLIENTES
# ---------------------------------------------------------
st.subheader("🔎 Filtro por cliente")

clientes_unicos = sorted(df["Cliente"].dropna().unique())
filtro_cliente = st.selectbox("Selecciona un cliente (opcional)", ["Todos"] + list(clientes_unicos))

if filtro_cliente != "Todos":
    df_display = df[df["Cliente"] == filtro_cliente]
else:
    df_display = df.copy()

# ---------------------------------------------------------
# SECCIÓN 3: DEUDORES ACTIVOS
# ---------------------------------------------------------
st.subheader("📋 Deudores activos")

df_display_formateado = df_display.copy()
df_display_formateado["Valor"] = df_display_formateado["Valor"].apply(lambda x: f"${x:,.0f}")

st.dataframe(df_display_formateado, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# SECCIÓN 4: EDITAR REGISTRO
# ---------------------------------------------------------
st.subheader("✏️ Editar un registro")

if len(df) == 0:
    st.info("No hay registros para editar.")
else:
    consecutivos = df["Consecutivo"].tolist()
    seleccionado = st.selectbox("Selecciona el consecutivo", consecutivos)

    row = df[df["Consecutivo"] == seleccionado].iloc[0]
    idx = df[df["Consecutivo"] == seleccionado].index[0]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        cliente_edit = st.text_input("Cliente", value=row["Cliente"])
    with col2:
        fecha_edit = st.date_input("Fecha", value=row["Fecha"])
    with col3:
        valor_edit = st.number_input("Valor (COP)", min_value=0.0, value=float(row["Valor"]), format="%.0f")
    with col4:
        pagado_edit = st.checkbox("Pagado", value=row["Pagado"])

    if st.button("Guardar cambios"):
        df.at[idx, "Cliente"] = cliente_edit
        df.at[idx, "Fecha"] = fecha_edit
        df.at[idx, "Valor"] = valor_edit
        df.at[idx, "Pagado"] = pagado_edit

        # Si se marcó como pagado → eliminar
        df = df[df["Pagado"] != True]

        # Reordenar alfabéticamente
        df = df.sort_values(by="Cliente", ascending=True)

        # Reindexar consecutivos
        df = df.reset_index(drop=True)
        df["Consecutivo"] = df.index + 1

        save()
        st.success("Cambios guardados correctamente.")
        st.rerun()

# ---------------------------------------------------------
# SECCIÓN 5: TOTAL POR CLIENTE
# ---------------------------------------------------------
st.subheader("📊 Total por cliente")

if len(df) == 0:
    st.info("No hay deudores activos.")
else:
    totales = df.groupby("Cliente")["Valor"].sum().reset_index()
    totales["Valor"] = totales["Valor"].apply(lambda x: f"${x:,.0f}")

    st.dataframe(totales, use_container_width=True)

# Gran total
if len(df) > 0:
    gran_total = df["Valor"].sum()
    st.subheader(f"💰 Gran total de todos los deudores: **${gran_total:,.0f}**")

# ---------------------------------------------------------
# SECCIÓN 6: DESCARGAR TOTAL POR CLIENTE COMO IMAGEN
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
# SECCIÓN 7: DESCARGAR EXCEL ACTUALIZADO
# ---------------------------------------------------------
st.subheader("⬇️ Descargar Excel actualizado")

buffer = df.copy()
buffer.to_excel("DeudoresPrueba.xlsx", index=False)

with open("DeudoresPrueba.xlsx", "rb") as f:
    st.download_button(
        label="Descargar archivo",
        data=f,
        file_name="DeudoresPrueba.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

