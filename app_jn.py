import os
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Calculadora de Compras Preescolar", layout="wide")
st.title("🍎 Calculadora de Compras Semanales")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "recetario_jn.db")

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
DECIMALES = 4

CONFIG_CANTIDAD = {
    "Cantidad": st.column_config.NumberColumn("Cantidad", format="%.4f")
}


# --- REGLAS DE CONVERSIÓN COMERCIALES ---
def convertir(insumo, total, unidad):
    """Devuelve (cantidad, unidad_final) aplicando las reglas comerciales."""
    insumo = str(insumo).upper().strip()
    unidad_limpia = str(unidad).strip()
    unidad_upper = unidad_limpia.upper()

    # 1. Agua natural: de mililitros a garrafones de 20 L
    if "AGUA NATURAL" in insumo:
        return total / 20000.0, "Garrafon(es)"

    # 2. Líquidos: unidades que empiezan con 'L' (L, Lt, Litros...)
    if unidad_upper.startswith("L"):
        return total / 1000.0, "L"

    # 3. Sólidos: unidades que empiezan con 'K' o 'G' (Kg, g, gramos...)
    if unidad_upper.startswith("K") or unidad_upper.startswith("G"):
        return total / 1000.0, "Kg"

    # 4. Pan integral: de piezas a paquetes de 20 unidades
    if "PAN INTEGRAL" in insumo:
        return total / 20.0, "Paquete(s)"

    # Piezas y demás empaques se mantienen igual
    return total, unidad_limpia


def tabla_por_dia(df_dia):
    """Agrupa los ingredientes de un día y devuelve la tabla lista para mostrar."""
    out = (
        df_dia.groupby(["Insumo", "Unidad Final"])["Cantidad"]
        .sum()
        .reset_index()
        .rename(columns={"Unidad Final": "Unidad"})
        .sort_values(by="Insumo")
    )
    out["Cantidad"] = out["Cantidad"].round(DECIMALES)
    return out[["Insumo", "Cantidad", "Unidad"]]


# 1. Obtener semanas disponibles
conn = sqlite3.connect(DATABASE)
try:
    semanas_df = pd.read_sql_query(
        "SELECT DISTINCT semana FROM recetario_diario ORDER BY semana", conn
    )
    semanas_disponibles = semanas_df["semana"].tolist()
except Exception:
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
            value=100,
        )

    st.markdown("---")
    st.subheader("📅 3. Selecciona los días laborables para el cálculo:")
    st.write(
        "Verás una tabla por cada día seleccionado y una pestaña con el"
        " consolidado de todos los días marcados."
    )

    columnas = st.columns(5)
    dias_activos = []
    for col, dia in zip(columnas, DIAS_SEMANA):
        with col:
            if st.checkbox(dia, value=True):
                dias_activos.append(dia)

    if st.button("📊 Calcular Lista de Compras"):
        if not dias_activos:
            st.error("Debes seleccionar al menos un día activo.")
        else:
            conn = sqlite3.connect(DATABASE)
            placeholders = ",".join("?" for _ in dias_activos)
            query = f"""
                SELECT dia AS Dia, ingrediente AS Insumo,
                       cantidad_base, unidad AS Unidad
                FROM recetario_diario
                WHERE semana = ? AND dia IN ({placeholders})
            """
            params = [semana_sel] + dias_activos
            df_recetas = pd.read_sql_query(query, conn, params=params)
            conn.close()

            if df_recetas.empty:
                st.warning("No hay ingredientes registrados para los días activos.")
            else:
                # Cantidad total por fila = cantidad base * matrícula
                df_recetas["Total_Por_Fila"] = (
                    df_recetas["cantidad_base"] * matricula
                )

                # Conversión comercial fila por fila (antes de agrupar)
                convertidos = df_recetas.apply(
                    lambda r: pd.Series(
                        convertir(r["Insumo"], r["Total_Por_Fila"], r["Unidad"]),
                        index=["Cantidad", "Unidad Final"],
                    ),
                    axis=1,
                )
                df_recetas[["Cantidad", "Unidad Final"]] = convertidos

                # Tablas por día (en orden de la semana)
                dias_con_datos = [
                    d for d in DIAS_SEMANA
                    if d in dias_activos and d in df_recetas["Dia"].values
                ]
                tablas_dia = {
                    d: tabla_por_dia(df_recetas[df_recetas["Dia"] == d])
                    for d in dias_con_datos
                }

                # Consolidado de todos los días seleccionados
                df_final = tabla_por_dia(df_recetas)

                st.subheader(
                    f"📋 Lista de Surtido para {semana_sel} (Matrícula: {matricula})"
                )

                nombres_tabs = ["📦 Consolidado"] + [
                    f"📅 {d}" for d in dias_con_datos
                ]
                tabs = st.tabs(nombres_tabs)

                # --- Pestaña consolidada ---
                with tabs[0]:
                    st.markdown(f"**Suma de:** {', '.join(dias_con_datos)}")
                    st.dataframe(
                        df_final,
                        use_container_width=True,
                        hide_index=True,
                        column_config=CONFIG_CANTIDAD,
                    )

                    # Matriz Insumo x Día (para ver de dónde sale cada total)
                    with st.expander("🔎 Ver desglose por día (matriz)"):
                        matriz = df_recetas.pivot_table(
                            index=["Insumo", "Unidad Final"],
                            columns="Dia",
                            values="Cantidad",
                            aggfunc="sum",
                            fill_value=0,
                        )
                        matriz = matriz[
                            [d for d in DIAS_SEMANA if d in matriz.columns]
                        ]
                        matriz["TOTAL"] = matriz.sum(axis=1)
                        matriz = matriz.round(DECIMALES).reset_index().rename(
                            columns={"Unidad Final": "Unidad"}
                        )
                        st.dataframe(
                            matriz, use_container_width=True, hide_index=True
                        )

                    st.download_button(
                        label="📥 Descargar Consolidado (CSV)",
                        data=df_final.to_csv(index=False).encode("utf-8"),
                        file_name=f"Compras_{semana_sel}_M{matricula}_consolidado.csv",
                        mime="text/csv",
                        key="dl_consolidado",
                    )

                # --- Una pestaña por día ---
                for tab, dia in zip(tabs[1:], dias_con_datos):
                    with tab:
                        st.markdown(f"**Surtido para el {dia}**")
                        st.dataframe(
                            tablas_dia[dia],
                            use_container_width=True,
                            hide_index=True,
                            column_config=CONFIG_CANTIDAD,
                        )
                        st.download_button(
                            label=f"📥 Descargar {dia} (CSV)",
                            data=tablas_dia[dia]
                            .to_csv(index=False)
                            .encode("utf-8"),
                            file_name=f"Compras_{semana_sel}_M{matricula}_{dia}.csv",
                            mime="text/csv",
                            key=f"dl_{dia}",
                        )
else:
    st.info("Ejecuta 'python inicializar_sistema.py' en tu terminal.")
