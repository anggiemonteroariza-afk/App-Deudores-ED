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

# Normalizar clientes
df["Cliente"] = df["Cliente"].astype(str).str.strip().str.upper()

# Eliminar filas vacías
df = df.dropna(how="all")

# Eliminar registros pagados
df = df[df["Pagado"] != True]

# Orden alfabético
df = df.sort_values(by="Cliente", ascending=True, na_position='last')

# Reset consecutivos
df = df.reset_index(drop=True)
df["Consecutivo"] = df.index + 1

def save(dataframe=None):
    if dataframe is None:
        dataframe = df
    dataframe.to_excel(FILE_PATH, index=False)


# ---------------------------------------------------------
# TÍTULO
# ---------------------------------------------------------
st.markdown("<h2 style='margin:0 0 6px 0'>💸 App de Registro de Deudores</h2>", unsafe_allow_html=True)
st.markdown("<div style='margin-bottom:10px'>Registro rápido · edición en tabla · totales · descarga</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# SECCIÓN 1 — REGISTRAR NUEVO
# ---------------------------------------------------------
with st.expander("➕ Registrar nuevo deudor", expanded=True):
    col1, col2, col3 = st.columns([3,2,2])

    with col1:
        cliente = st.text_input("Cliente", placeholder="Nombre del cliente")

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
            step=1000.0,     # CORREGIDO
            format="%.0f"
        )

    if st.button("Guardar nuevo registro", key="guardar_nuevo"):
        if cliente.strip() == "":
            st.error("El nombre del cliente es obligatorio.")
        else:
            new_row = {
                "Consecutivo": len(df) + 1,
                "Cliente": cliente.strip().upper(),
                "Fecha": fecha,
                "Valor": float(valor),
                "Pagado": False
            }

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            df["Cliente"] = df["Cliente"].astype(str).str.strip().str.upper()
            df = df.sort_values(by="Cliente").reset_index(drop=True)
            df["Consecutivo"] = df.index + 1

            save(df)
            st.success("Registro guardado exitosamente.")
            st.rerun()   # CORREGIDO


# ---------------------------------------------------------
# SECCIÓN 2 — FILTRO Y TABLA EDITABLE
# ---------------------------------------------------------
with st.expander("📋 Deudores activos (editar directamente aquí)", expanded=True):

    clientes_unicos = sorted(df["Cliente"].dropna().unique())
    filtro_cliente = st.selectbox(
        "Filtrar por cliente",
        ["Todos"] + list(clientes_unicos),
        key="filtro_cliente"
    )

    df_display = df if filtro_cliente == "Todos" else df[df["Cliente"] == filtro_cliente]

    df_editable = df_display.copy()
    df_editable["Valor"] = pd.to_numeric(df_editable["Valor"], errors="coerce").fillna(0.0)

    edited_df = st.data_editor(
        df_editable,
        hide_index=True,
        use_container_width=True,
        key="editor_activos",
        column_config={
            "Consecutivo": st.column_config.NumberColumn(disabled=True),
            "Cliente": st.column_config.TextColumn("Cliente"),
            "Fecha": st.column_config.DateColumn("Fecha", max_value=date.today()),
            "Valor": st.column_config.NumberColumn("Valor", min_value=0.0, step=1000.0, format="%.0f"),
            "Pagado": st.column_config.CheckboxColumn("Pagado")
        },
        num_rows="dynamic"
    )

    if st.button("💾 Guardar cambios", key="guardar_tabla"):
        edited_df["Cliente"] = edited_df["Cliente"].astype(str).str.strip().str.upper()
        edited_df = edited_df[edited_df["Pagado"] != True]
        edited_df = edited_df.sort_values("Cliente")
        edited_df = edited_df.reset_index(drop=True)
        edited_df["Consecutivo"] = edited_df.index + 1

        df = edited_df.copy()
        save(df)
        st.success("Cambios guardados.")
        st.rerun()   # CORREGIDO


# ---------------------------------------------------------
# SECCIÓN 3 — TOTALES + IMAGEN
# ---------------------------------------------------------
with st.expander("📊 Totales y descarga de imagen", expanded=False):
    if df.empty:
        st.info("No hay deudores.")
    else:
        totales_raw = df.groupby("Cliente", as_index=False)["Valor"].sum().sort_values("Cliente")

        totales_display = totales_raw.copy()
        totales_display["Valor"] = totales_display["Valor"].apply(lambda x: f"${x:,.0f}")

        st.dataframe(totales_display, use_container_width=True)

        gran_total = df["Valor"].sum()
        st.markdown(f"**💰 Gran total:** ${gran_total:,.0f}")

        fig, ax = plt.subplots(figsize=(6, max(2, len(totales_raw)*0.5)))
        ax.axis('off')
        tabla = ax.table(
            cellText=totales_raw.values,
            colLabels=totales_raw.columns,
            cellLoc='center',
            loc='center'
        )
        tabla.auto_set_font_size(False)
        tabla.set_fontsize(10)
        tabla.scale(1, 1.5)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches="tight")
        buf.seek(0)

        st.image(buf, caption="Total por cliente")

        st.download_button(
            "⬇️ Descargar imagen",
            data=buf,
            file_name="total_por_cliente.png",
            mime="image/png"
        )


# ---------------------------------------------------------
# SECCIÓN 4 — DESCARGAR EXCEL
# ---------------------------------------------------------
with st.expander("⬇️ Descargar Excel actualizado", expanded=False):
    save(df)
    with open(FILE_PATH, "rb") as f:
        st.download_button(
            "Descargar archivo Excel",
            f,
            file_name="DeudoresPrueba.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
