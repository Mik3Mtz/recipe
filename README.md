# 🛒 Meal Supply Planner (Streamlit App)

Aplicación web desarrollada con **Streamlit** diseñada para calcular automáticamente la lista y cantidad de insumos de alimentos necesarios para compras semanales o diarias, optimizando presupuestos y reduciendo el desperdicio de comida.

---

## 🚀 Características

* **Cálculo flexible:** Estima los insumos por día específico o consolidado para la semana completa.
* **Consolidación de ingredientes:** Suma automáticamente ingredientes repetidos en distintas recetas o menús.
* **Ajuste por comensales:** Escala las porciones y cantidades requeridas según el número de personas.
* **Exportación y consulta rápida:** Vista clara y ordenada de la lista de compras lista para usar en el supermercado o mercado local.

---

## 🛠️ Tecnologías utilizadas

* [Python 3.10+](https://www.python.org/)
* [Streamlit](https://streamlit.io/)
* [Pandas](https://pandas.pydata.org/) (manejo de datos y recetas)

---

## 📁 Estructura del proyecto

```text
├── .streamlit/
│   └── config.toml          # Configuraciones visuales de Streamlit (opcional)
├── data/
│   └── recipes.json         # Base de datos o catálogo de recetas/ingredientes
├── src/
│   ├── calculator.py        # Lógica para cálculo y consolidación de insumos
│   └── ui_components.py     # Componentes reutilizables de UI
├── app.py                   # Punto de entrada principal de la app
├── requirements.txt         # Dependencias del proyecto
└── README.md
