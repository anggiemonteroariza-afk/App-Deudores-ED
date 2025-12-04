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

# 🔥 Normalizar nombres para agrupar correctamente
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
    """Guardar dataframe (por defecto guarda df global)."""
    if dataframe is None:
        dataframe = df
    dataframe.to_excel(FILE_PATH, index=False)

# ---------------------------------------------------------
# UI: título y descripción compacta (móvil-friendly)
# ---------------------------------------------------------
st.markdown("<h2 style='margin:0 0 6px 0'>💸 App de Registro de Deudores</h2>", unsafe_allow_html=True)
st.markdown("<div style='margin-bottom:10px'>Registro rápido · edición en la tabla · totales · descargar</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# SECCIÓN: Registrar (expander para móvil)
# ---------------------------------------------------------
with st.expander("➕ Registrar nuevo deudor", expanded=True):
    col1, col2, col3 = st.columns([3,2,2], gap="small")
    with col1:
        cliente = st.text_input("Cliente", placeholder="Nombre completo")
    with col2:
        # key único y max_value para evitar fechas futuras
        fecha = st.date_input("Fecha", value=date.today(), max_value=date.today(), key="fecha_nuevo")
    with col3:
        valor = st.number_input("Valor (COP)", min_value=0.0, format="%.0f", step=1000)

    # Botón grande estilo móvil
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
            # re-normalizar y reindexar
            df["Cliente"] = df["Cliente"].astype(str).str.strip().str.upper()
            df = df.sort_values(by="Cliente").reset_index(drop=True)
            df["Consecutivo"] = df.index + 1
            save(df)
            st.success("Registro guardado exitosamente.")
            st.experimental_rerun()

# ---------------------------------------------------------
# SECCIÓN: Filtro y tabla editable (expander)
# ---------------------------------------------------------
with st.expander("📋 Deudores activos (tocar para desplegar)", expanded=True):
    # Filtro de clientes
    clientes_unicos = sorted(df["Cliente"].dropna().unique())
    filtro_cliente = st.selectbox("Filtrar por cliente (opcional)", ["Todos"] + list(clientes_unicos), key="filtro_cliente")

    df_display = df if filtro_cliente == "Todos" else df[df["Cliente"] == filtro_cliente]

    # Mostrar y permitir edición en tabla
    st.markdown("**Lista (edita directamente aquí):**")
    editable_df = df_display.copy()
    # Asegurarnos que Valor sea numérico
    editable_df["Valor"] = pd.to_numeric(editable_df["Valor"], errors="coerce").fillna(0.0)

    # Editor
    edited_df = st.data_editor(
        editable_df,
        use_container_width=True,
        hide_index=True,
        key="editor_activos",
        column_config={
            "Consecutivo": st.column_config.NumberColumn("Consecutivo", disabled=True),
            "Cliente": st.column_config.TextColumn("Cliente"),
            "Fecha": st.column_config.DateColumn("Fecha", max_value=date.today()),
            "Valor": st.column_config.NumberColumn("Valor", min_value=0, step=1000, format="%.0f"),
            "Pagado": st.column_config.CheckboxColumn("Pagado")
        },
        num_rows="dynamic"
    )

    st.write("")  # espacio
    if st.button("💾 Guardar cambios en registros", key="guardar_tabla"):
        # Normalizar clientes
        edited_df["Cliente"] = edited_df["Cliente"].astype(str).str.strip().str.upper()
        # Remover pagados
        edited_df = edited_df[edited_df["Pagado"] != True]
        # Reordenar
        edited_df = edited_df.sort_values(by="Cliente", ascending=True)
        # Reindexar consecutivos
        edited_df = edited_df.reset_index(drop=True)
        edited_df["Consecutivo"] = edited_df.index + 1
        # Guardar sobre df (sobrescribe global)
        df = edited_df.copy()
        save(df)
        st.success("Cambios guardados correctamente.")
        st.experimental_rerun()

# ---------------------------------------------------------
# SECCIÓN: Totales y imagen (expander)
# ---------------------------------------------------------
with st.expander("📊 Totales y imagen", expanded=False):
    st.markdown("**Total por cliente (agrupado y ordenado):**")
    if df.empty:
        st.info("No hay deudores activos.")
    else:
        # totales sin formatear para cálculos
        totales_raw = df.groupby("Cliente", as_index=False)["Valor"].sum().sort_values("Cliente")
        # para vista formateada
        totales_display = totales_raw.copy()
        totales_display["Valor"] = totales_display["Valor"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(totales_display, use_container_width=True)

        # Gran total
        gran_total = df["Valor"].sum()
        st.markdown(f"**💰 Gran total de todos los deudores:** ${gran_total:,.0f}")

        st.markdown("---")
        st.markdown("**📥 Imagen del total por cliente**")
        # Generar imagen PNG de la tabla de totales
        fig, ax = plt.subplots(figsize=(6, max(2, len(totales_raw)*0.5)))
        ax.axis('off')
        tabla = ax.table(cellText=totales_raw.values, colLabels=totales_raw.columns, cellLoc='center', loc='center')
        tabla.auto_set_font_size(False)
        tabla.set_fontsize(10)
        tabla.scale(1, 1.5)
        buffer_img = io.BytesIO()
        plt.savefig(buffer_img, format='png', bbox_inches='tight', dpi=300)
        buffer_img.seek(0)
        st.image(buffer_img, caption="Total por cliente")
        st.download_button(label="⬇️ Descargar imagen (PNG)", data=buffer_img, file_name="Total_por_cliente.png", mime="image/png")

# ---------------------------------------------------------
# SECCIÓN: Descargar Excel (expander)
# ---------------------------------------------------------
with st.expander("⬇️ Descargar Excel actualizado", expanded=False):
    # Guardar copia actual por seguridad
    save(df)
    with open(FILE_PATH, "rb") as f:
        st.download_button(
            label="Descargar archivo .xlsx",
            data=f,
            file_name="DeudoresPrueba.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ---------------------------------------------------------
# FOOTER (pequeño, útil en móvil)
# ---------------------------------------------------------
st.markdown("<div style='margin-top:12px; font-size:12px; color:gray'>Tip: usa el botón 'Guardar cambios en registros' luego de editar la tabla para que los registros marcados como pagado desaparezcan.</div>", unsafe_allow_html=True)
