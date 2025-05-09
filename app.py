import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import plotly.express as px
from google.oauth2.service_account import Credentials
import gspread

# -----------------------------------------------------
# CONFIGURATION GÉNÉRALE
# -----------------------------------------------------
st.set_page_config("Dashboard Captive Leasing", layout="wide")
st_autorefresh(interval=30_000, key="data_refresh")

# -----------------------------------------------------
# AUTHENTIFICATION GOOGLE SHEETS
# -----------------------------------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)
client = gspread.authorize(creds)

# -----------------------------------------------------
# IMPORT DES DONNÉES GOOGLE SHEETS
# -----------------------------------------------------
spreadsheet = client.open_by_url(st.secrets["sheet"]["url"])
mensuel_sheet = spreadsheet.worksheet("Mensuel")
df = pd.DataFrame(mensuel_sheet.get_all_records())

# Nettoyage & conversion
df = df.replace(",", ".", regex=True).apply(pd.to_numeric, errors="coerce")

# Ajout colonne Année (pour filtrage dynamique)
df["Année"] = (df["Mois"] / 12).apply(lambda x: f"Year{int(x)+1 if x % 1 != 0 else int(x)}")

# -----------------------------------------------------
# INTERFACE UTILISATEUR
# -----------------------------------------------------
st.title("📊 Dashboard - Captive Leasing")

col1, col2 = st.columns([1, 5])
with col1:
    year_selected = st.selectbox("Période à afficher", options=sorted(df["Année"].unique()))

filtered_df = df[df["Année"] == year_selected]

# -----------------------------------------------------
# INDICATEURS CLÉS
# -----------------------------------------------------
kpi1, kpi2, kpi3 = st.columns(3)

with kpi1:
    st.metric("💸 Chiffre d'affaires (mois)", f"{filtered_df['Lease_Revenue'].iloc[-1]:,.0f} k€")

with kpi2:
    st.metric("📈 Résultat cumulé", f"{filtered_df['Cum_Cashflow'].iloc[-1]:,.0f} k€")

with kpi3:
    spread = filtered_df["Encours_Leasing"].iloc[-1] - filtered_df["Encours_Debt"].iloc[-1]
    st.metric("🔍 Écart Leasing / Dette", f"{spread:,.0f} k€")

# -----------------------------------------------------
# GRAPHIQUES
# -----------------------------------------------------
fig1 = px.line(filtered_df, x="Mois", y=["Encours_Leasing", "Encours_Debt"], title="Encours Leasing vs Dette")
fig2 = px.line(filtered_df, x="Mois", y="Cum_Cashflow", title="Résultat cumulé")
fig3 = px.line(filtered_df, x="Mois", y="Lease_Revenue", title="Chiffre d'affaires mensuel")

st.plotly_chart(fig1, use_container_width=True)
st.plotly_chart(fig2, use_container_width=True)
st.plotly_chart(fig3, use_container_width=True)
