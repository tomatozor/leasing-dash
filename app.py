import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from streamlit_autorefresh import st_autorefresh

# ⚙️ Doit être le premier st.* appelé
st.set_page_config(page_title="Dashboard Captive Leasing", layout="wide")

# ⏱ Rafraîchit l'app toutes les X minutes (ici : 5)
REFRESH_EVERY_MIN = 5
st_autorefresh(interval=REFRESH_EVERY_MIN * 60 * 1000, key="datarefresh")

# 🔐 Authentification Google Sheets (via les secrets)
scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(st.secrets["sheet"]["url"])

# 🔄 Chargement sécurisé des données (feuilles 'Mensuel' et 'Résumé')
@st.cache_data(ttl=REFRESH_EVERY_MIN*60)
def load_sheet(name: str) -> pd.DataFrame:
    ws = sheet.worksheet(name)
    values = ws.get_all_values()
    headers_raw = [h.strip() if h else f"col_{i}" for i, h in enumerate(values[0])]
    headers, seen = [], {}
    for h in headers_raw:
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 0
        headers.append(h)
    df = pd.DataFrame(values[1:], columns=headers)
    df = df.replace(",", ".", regex=True).apply(pd.to_numeric, errors="ignore")
    return df

mensuel = load_sheet("Mensuel")
resume  = load_sheet("Résumé")

# 🔢 Sélecteur de période annuelle
years = sorted(resume["Period"].unique())
selected_year = st.sidebar.selectbox("📅 Période à afficher", years, index=len(years)-1)

# 📊 Calculs KPI
mensuel = mensuel.dropna(subset=["Lease_Revenue"])  # ou "Mois" si toujours rempli
last = mensuel.iloc[-1]
ca_mois   = float(last["Lease_Revenue"])
res_mois  = float(last["Net_Cashflow"])
cash_cum  = float(last["Cum_Cashflow"])
leas_enc  = float(last["Encours_Leasing"])
debt_enc  = float(last["Encours_Debt"])
spread_m  = leas_enc - debt_enc
marge_m   = res_mois / ca_mois if ca_mois else 0

# 🔎 KPI annuel sélectionné
res_sel = resume[resume["Period"] == selected_year].iloc[0]
ca_an   = float(res_sel["Lease_Revenue"])
res_an  = float(res_sel["Net_Cashflow"])
renew   = float(res_sel.get("New_Finance_Renewal", 0))
pct_renew = renew / ca_an if ca_an else 0

# 📈 Affichage des KPI
st.title("📊 Dashboard Captive Leasing")

k1, k2, k3, k4 = st.columns(4)
k1.metric("CA (mois)", f"{ca_mois:,.0f} MF")
k2.metric("Cash cumulé", f"{cash_cum:,.0f} MF")
k3.metric("Spread L/D", f"{spread_m:,.0f} MF")
k4.metric("Marge nette", f"{marge_m:.1%}")

k5, k6, k7 = st.columns(3)
k5.metric(f"CA {selected_year}", f"{ca_an:,.0f} MF")
k6.metric(f"Résultat {selected_year}", f"{res_an:,.0f} MF")
k7.metric("Renouvellement", f"{pct_renew:.1%}")

st.divider()

# 🗂️ Tabs d'affichage
tab1, tab2 = st.tabs(["📆 Vue mensuelle", "🧾 Vue annuelle"])

with tab1:
    fig1 = px.line(mensuel, x="Mois", y=["Lease_Revenue", "Net_Cashflow"],
                   title="Revenus et Résultat mensuel")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(mensuel, x="Mois",
                   y=["Encours_Leasing", "Encours_Debt", "Cum_Cashflow"],
                   title="Encours & Cash cumulé")
    st.plotly_chart(fig2, use_container_width=True)

with tab2:
    fig3 = px.bar(resume, x="Period", y=["Lease_Revenue", "Net_Cashflow"],
                  barmode="group", title="CA vs Résultat annuel")
    st.plotly_chart(fig3, use_container_width=True)

    fig4 = px.line(resume, x="Period", y=["Encours_Leasing", "Encours_Debt"],
                   title="Encours Leasing vs Debt")
    st.plotly_chart(fig4, use_container_width=True)

# 📥 Bouton d’export CSV
csv = mensuel.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Télécharger les données mensuelles", csv, "mensuel.csv", "text/csv")

st.caption(f"🕒 Données live Google Sheets • Auto-refresh toutes les {REFRESH_EVERY_MIN} min")
