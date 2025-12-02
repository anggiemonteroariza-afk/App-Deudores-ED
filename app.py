import streamlit as st
import pandas as pd
import os
from datetime import date

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

# Eliminar registros marcados como pagados
df = df[df["Pagado"] != True]

# Reset consecutivo cada vez
df = df.reset_index(drop=True)
df["Consecutivo"] = df.index + 1

# Función para guardar
def save():
    df.to_excel(FILE_PATH, index=False)

# ---------------------------------------------------------
# TÍTULO
# ---------------------------------------------------------
st.title("💸 Mini App de Registro de Deudores")
st.write("Todo en una sola pantalla para que sea más rápido y fácil.")

# ---------------------------------------------------------
# SECCIÓN 1: REGISTRAR NUEVO DEUDOR
# ---------------------------------------------------------
st.subheader("➕ Registrar nuevo deudor")

col1, col2, col3 = st.columns(3)

with col1:
    cliente = st.text_input("Cliente")
with col2:
    fecha = st.date_input("Fecha", value=date.today(), key="fecha_registro")
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
# SECCIÓN 2: DEUDORES ACTIVOS
# ---------------------------------------------------------
st.subheader("📋 Deudores activos")

# 🔥 FILTRO DE CLIENTES (opcional)
clientes_unicos = sorted(df["Cliente"].unique())
cliente_filtro = st.selectbox("Filtrar por cliente", ["Todos"] + clientes_unicos, index=0)

df_display = df.copy()

if cliente_filtro != "Todos":
    df_display = df_display[df_display["Cliente"] == cliente_filtro]

# Orden alfabético
df_display = df_display.sort_values("Cliente")

# Formato COP
df_display["Valor"] = df_display["Valor"].apply(lambda x: f"${x:,.0f}")

st.dataframe(df_display, use_container_width=True, hide_index=True)

# 🔥 GRAN TOTAL GENERAL
gran_total = df["Valor"].sum()
st.subheader(f"💰 Gran total de todos los deudores: ${gran_total:,.0f}")

# ---------------------------------------------------------
# SECCIÓN 3: EDITAR REGISTRO
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
        fecha_edit = st.date_input("Fecha", value=row["Fecha"], key=f"fecha_edit_{seleccionado}")
    with col3:
        valor_edit = st.number_input(
            "Valor (COP)", 
            min_value=0.0, 
            value=float(row["Valor"]), 
            format="%.0f"
        )
    with col4:
        pagado_edit = st.checkbox("Pagado", value=row["Pagado"])

    if st.button("Guardar cambios"):
        df.at[idx, "Cliente"] = cliente_edit
        df.at[idx, "Fecha"] = fecha_edit
        df.at[idx, "Valor"] = valor_edit
        df.at[idx, "Pagado"] = pagado_edit

        df = df[df["Pagado"] != True]  # eliminar pagados

        df = df.reset_index(drop=True)
        df["Consecutivo"] = df.index + 1

        save()
        st.success("Cambios guardados correctamente.")
        st.rerun()

# ---------------------------------------------------------
# SECCIÓN 4: TOTAL POR CLIENTE
# ---------------------------------------------------------
st.subheader("📊 Total por cliente")

if len(df) == 0:
    st.info("No hay deudores activos.")
else:
    totales = df.groupby("Cliente")["Valor"].sum().reset_index()
    totales["Valor"] = totales["Valor"].apply(lambda x: f"${x:,.0f}")
    totales = totales.sort_values("Cliente")
    st.dataframe(totales, use_container_width=True)

# ---------------------------------------------------------
# SECCIÓN 5: DESCARGAR EXCEL
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
