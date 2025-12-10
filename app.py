import streamlit as st
import pandas as pd
import os
from datetime import date
import matplotlib.pyplot as plt
import io
import base64
import requests

# ---------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------------
st.set_page_config(page_title="Mini App Deudores", page_icon="💸", layout="wide")

FILE_PATH = "DeudoresPrueba.xlsx"

# ---------------------------------------------------------
#*** CONFIGURACIÓN DE GITHUB PARA SINCRONIZAR AUTOMÁTICAMENTE ***
# ---------------------------------------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # ✔ Token guardado en Streamlit Cloud
GITHUB_REPO = "anggiemontero/App-Deudores-ED"  # ✔ Tu repo
GITHUB_FILE_PATH = "DeudoresPrueba.xlsx"       # ✔ Nombre del archivo dentro del repo

def upload_to_github(local_file_path, repo_file_path):
    """Sube el Excel actualizado a GitHub automáticamente."""
    if not GITHUB_TOKEN:
        st.error("Falta el token de GitHub. Agrégalo en Streamlit → Settings → Secrets.")
        return
    
    with open(local_file_path, "rb") as f:
        content = f.read()
    encoded = base64.b64encode(content).decode()

    # Verificar si el archivo existe en GitHub
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_file_path}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        sha = r.json()["sha"]
    else:
        sha = None

    data = {
        "message": "Actualización automática desde Streamlit",
        "content": encoded,
        "sha": sha
    }

    result = requests.put(url, headers=headers, json=data)

    if result.status_code in [200, 201]:
        st.success("📤 Archivo sincronizado automáticamente con GitHub")
    else:
        st.error(f"Error al subir archivo a GitHub: {result.text}")


# ---------------------------------------------------------
# CARGA Y LIMPIEZA DEL ARCHIVO
# ---------------------------------------------------------
if os.path.exists(FILE_PATH):
    df = pd.read_excel(FILE_PATH)
else:
    df = pd.DataFrame(columns=["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"])

# Asegurar columnas
for col in ["Consecutivo", "Cliente", "Fecha", "Valor", "Pagado"]:
    if col not in df.columns:
        df[col] = None

# Normalizar Cliente
df["Cliente"] = (
    df["Cliente"]
    .astype(str)
    .str.strip()
    .str.upper()
)

# Convertir fecha
df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date

# Convertir valor
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

# Normalizar Pagado
def normalize_paid(x):
    if str(x).upper() in ["1", "TRUE", "PAGADO", "SI", "SÍ", "YES"]:
        return True
    return False

df["Pagado"] = df["Pagado"].apply(normalize_paid)

# Eliminar registros vacíos
df = df.dropna(how="all")

# Eliminar pagados
df = df[df["Pagado"] != True]

# Ordenar alfabéticamente
df = df.sort_values(by="Cliente", ascending=True)

# Reset consecutivo
df = df.reset_index(drop=True)
df["Consecutivo"] = df.index + 1

# Guardar
def save(data):
    data.to_excel(FILE_PATH, index=False)
    upload_to_github(FILE_PATH, GITHUB_FILE_PATH)  # ✔ Sincroniza automáticamente


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
    cliente = st.text_input("Cliente").strip().upper()

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
        format="%.0f",
        step=1000.0
    )

if st.button("Guardar nuevo registro"):
    if cliente == "":
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
        save(df)
        st.success("Registro guardado exitosamente.")
        st.rerun()

# ---------------------------------------------------------
# SECCIÓN 2: FILTRO DE CLIENTES
# ---------------------------------------------------------
st.subheader("🔎 Filtro por cliente")

clientes_unicos = sorted(df["Cliente"].dropna().unique())
filtro_cliente = st.selectbox(
    "Selecciona un cliente (opcional)",
    ["Todos"] + list(clientes_unicos)
)

df_editable = df if filtro_cliente == "Todos" else df[df["Cliente"] == filtro_cliente]

# ---------------------------------------------------------
# SECCIÓN 3: TABLA EDITABLE CON BOTÓN GUARDAR
# ---------------------------------------------------------
st.subheader("✏️ Editar directamente en la tabla")

df_temp = df_editable.copy()
df_temp["Fecha"] = pd.to_datetime(df_temp["Fecha"])

edited = st.data_editor(
    df_temp,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Pagado": st.column_config.CheckboxColumn("Pagado"),
        "Fecha": st.column_config.DateColumn("Fecha", max_value=date.today()),
        "Valor": st.column_config.NumberColumn("Valor", min_value=0.0, step=1000.0, format="%.0f")
    },
    disabled=["Consecutivo"]
)

# BOTÓN PARA GUARDAR CAMBIOS
if st.button("💾 Guardar cambios de la tabla"):
    df_updated = df.copy()

    for _, row in edited.iterrows():
        idx = df[df["Consecutivo"] == row["Consecutivo"]].index
        if len(idx) > 0:
            idx = idx[0]
            df_updated.at[idx, "Cliente"] = row["Cliente"].strip().upper()
            df_updated.at[idx, "Fecha"] = row["Fecha"].date()
            df_updated.at[idx, "Valor"] = float(row["Valor"])
            df_updated.at[idx, "Pagado"] = bool(row["Pagado"])

    df_updated = df_updated[df_updated["Pagado"] != True]
    df_updated = df_updated.sort_values(by="Cliente")
    df_updated = df_updated.reset_index(drop=True)
    df_updated["Consecutivo"] = df_updated.index + 1

    save(df_updated)
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
    st.dataframe(totales, use_container_width=True)

# Gran total
if len(df) > 0:
    gran_total = df["Valor"].sum()
    st.subheader(f"💰 Gran total de todos los deudores: **${gran_total:,.0f}**")

# ---------------------------------------------------------
# SECCIÓN 5: IMAGEN
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
# SECCIÓN 6: DESCARGA EXCEL
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
