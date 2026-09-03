import os
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Calculadora de Compras", layout="wide")
st.title("🍎 Calculadora de Compras Semanales del Recetario Cíclico")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "recetario_flexible.db")

# 1. Obtener semanas disponibles
conn = sqlite3.connect(DATABASE)
try:
  semanas_df = pd.read_sql_query(
      "SELECT DISTINCT semana FROM recetario_diario ORDER BY semana", conn
  )
  semanas_disponibles = semanas_df["semana"].tolist()
except:
  semanas_disponibles = []
finally:
  conn.close()

if semanas_disponibles:
  col_sem, col_mat = st.columns(2)
  with col_sem:
    semana_sel = st.selectbox(
        "1. Selecciona la semana a planificar:", semanas_disponibles
    )
  with col_mat:
    matricula = st.number_input(
        "2. Ingresa la matrícula de alumnos (Multiplicador):",
        min_value=1,
        value=80,
    )

  st.markdown("---")
  st.subheader("📅 3. Selecciona los días laborables para el cálculo:")
  st.write(
      "Si desmarcas un día, sus ingredientes se restarán automáticamente del"
      " total semanal."
  )

  col_l, col_m, col_mi, col_j, col_v = st.columns(5)
  dias_activos = []

  with col_l:
    if st.checkbox("Lunes", value=True):
      dias_activos.append("Lunes")
  with col_m:
    if st.checkbox("Martes", value=True):
      dias_activos.append("Martes")
  with col_mi:
    if st.checkbox("Miércoles", value=True):
      dias_activos.append("Miércoles")
  with col_j:
    if st.checkbox("Jueves", value=True):
      dias_activos.append("Jueves")
  with col_v:
    if st.checkbox("Viernes", value=True):
      dias_activos.append("Viernes")

  if st.button("📊 Calcular Lista de Compras Consolidada"):
    if not dias_activos:
      st.error("Debes seleccionar al menos un día activo.")
    else:
      conn = sqlite3.connect(DATABASE)
      placeholders = ",".join("?" for _ in dias_activos)
      query = f"""
                SELECT ingrediente AS Insumo, cantidad_base, unidad AS Unidad
                FROM recetario_diario
                WHERE semana = ? AND dia IN ({placeholders})
            """
      params = [semana_sel] + dias_activos
      df_recetas = pd.read_sql_query(query, conn, params=params)
      conn.close()

      if not df_recetas.empty:
        # Multiplicación pura de la cantidad base unitaria de la fila por la matrícula introducida
        df_recetas["Total_Por_Fila"] = (
            df_recetas["cantidad_base"] * matricula
        )

        # CONSOLIDACIÓN SEMANAL: Agrupa los ingredientes duplicados entre días y suma sus totales
        df_consolidado = (
            df_recetas.groupby(["Insumo", "Unidad"])["Total_Por_Fila"]
            .sum()
            .reset_index()
        )

        # --- REGLAS DE CONVERSIÓN COMERCIALES BLINDADAS ---
        def aplicar_conversiones(row):
          insumo = str(row["Insumo"]).upper().strip()
          total = row["Total_Por_Fila"]
          # Limpiamos por completo la unidad eliminando espacios raros
          unidad_limpia = str(row["Unidad"]).strip()
          unidad_upper = unidad_limpia.upper()

          # 1. Ajuste especial para el Agua Natural (de mililitros a Garrafones de 20L)
          if "AGUA NATURAL" in insumo:
            return pd.Series([total / 20000.0, "Garrafones"])

          # 2. REGLA PARA LÍQUIDOS: Si empieza con la letra 'L' (L, Lt, l, lt, Litros, Litro)
          if unidad_upper.startswith("L"):
            return pd.Series([total / 1000.0, "L"])

          # 3. REGLA NUEVA PARA SÓLIDOS: Si empieza con 'K' (Kg, KG, kg, Kilogramos) o 'G' (g, gramos)
          # Se divide entre 1000 para transformar los gramos de tu archivo a Kilogramos comerciales
          if unidad_upper.startswith("K") or unidad_upper.startswith("G"):
            return pd.Series([total / 1000.0, "Kg"])

          # Para el resto de empaques o piezas independientes (como Pzas) se mantiene su cálculo directo
          return pd.Series([total, unidad_limpia])

        df_consolidado[["Cantidad", "Unidad Final"]] = df_consolidado.apply(
            aplicar_conversiones, axis=1
          )

        # Redondear el surtido final a 2 decimales para la orden de compra
        df_consolidado["Cantidad"] = df_consolidado["Cantidad"].round(2)

        df_final = df_consolidado[
            ["Insumo", "Cantidad", "Unidad Final"]
        ].rename(columns={"Unidad Final": "Unidad"})
        df_final = df_final.sort_values(by="Insumo")

        st.subheader(
            f"📋 Lista de Surtido para {semana_sel} (Matrícula: {matricula})"
        )
        st.dataframe(df_final, use_container_width=True, hide_index=True)

        st.download_button(
            label="📥 Descargar Lista de Compras (CSV)",
            data=df_final.to_csv(index=False).encode("utf-8"),
            file_name=f"Compras_{semana_sel}_M{matricula}.csv",
            mime="text/csv",
          )
      else:
        st.warning("No hay ingredientes registrados para los días activos.")
else:
  st.info("Ejecuta 'python inicializar_sistema.py' en tu terminal.")

