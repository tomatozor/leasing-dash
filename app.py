import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Dashboard Captive Leasing", layout="wide")

# -------- Paramètres modifiables -------- #
REFRESH_EVERY_MIN = 5      # minutes entre deux rafraîchissements auto
SCOPE = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

# -------- Connexion Google Sheets -------- #
creds = Credentials.from_service_account_file("service_account.json",
                                              scopes=SCOPE)
client = gspread.authorize(creds)
spreadsheet = client.open_by_url(st.secrets["sheet"]["url"])

@st.cache_data(ttl=REFRESH_EVERY_MIN*60)
def load_sheet(name: str) -> pd.DataFrame:
    """Lit la feuille `name` et renvoie un DataFrame propre."""
    ws = spreadsheet.worksheet(name)
    vals = ws.get_all_values()
    hdr_raw = [h.strip() if h else f"col_{i}" for i, h in enumerate(vals[0])]
    hdr = []
    seen = {}
    for h in hdr_raw:
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 0
        hdr.append(h)
    df = pd.DataFrame(vals[1:], columns=hdr)
    df = df.replace(r",", ".", regex=True).apply(pd.to_numeric, errors="ignore")
    return df

# -------- Rafraîchissement auto -------- #
st_autorefresh(interval=REFRESH_EVERY_MIN*60*1000, key="datarefresh")

# -------- Chargement des données -------- #
mensuel = load_sheet("Mensuel")
resume  = load_sheet("Résumé")

# -------- Sélecteur d’année -------- #
years = sorted(resume["Period"].unique())
year_choice = st.sidebar.selectbox("Période à afficher", years, index=len(years)-1)

# -------- KPI -------- #
last = mensuel.iloc[-1]
ca_mois   = float(last["Lease_Revenue"])
cash_tot  = float(last["Cum_Cashflow"])
enc_leas  = float(last["Encours_Leasing"])
enc_debt  = float(last["Encours_Debt"])
spread_m  = enc_leas - enc_debt
marge_m   = float(last["Net_Cashflow"]) / ca_mois if ca_mois else 0

res_sel = resume[resume["Period"] == year_choice].iloc[0]
ca_an   = float(res_sel["Lease_Revenue"])
res_an  = float(res_sel["Net_Cashflow"])
renouv  = float(res_sel.get("New_Finance_Renewal", 0))
pct_ren = renouv / ca_an if ca_an else 0

# -------- Mise en page -------- #
st.title("📊 Dashboard Captive Leasing")

k1, k2, k3, k4 = st.columns(4)
k1.metric("CA (mois)",     f"{ca_mois:,.0f} MF")
k2.metric("Cash cumulé",   f"{cash_tot:,.0f} MF")
k3.metric("Spread L/D",    f"{spread_m:,.0f} MF")
k4.metric("Marge nette",   f"{marge_m:.1%}")

k5, k6, k7 = st.columns(3)
k5.metric(f"CA {year_choice}",      f"{ca_an:,.0f} MF")
k6.metric(f"Résultat {year_choice}", f"{res_an:,.0f} MF")
k7.metric("Renouvellement %",       f"{pct_ren:.1%}")

st.divider()

tab1, tab2 = st.tabs(["Mensuel", f"Annuel – {year_choice}"])

with tab1:
    c1, c2 = st.columns(2)
    fig1 = px.line(mensuel, x="Mois", y=["Lease_Revenue", "Net_Cashflow"],
                   title="Revenus & Résultat mensuels")
    c1.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(mensuel, x="Mois",
                   y=["Encours_Leasing", "Encours_Debt", "Cum_Cashflow"],
                   title="Encours & Cash cumulé")
    c2.plotly_chart(fig2, use_container_width=True)

with tab2:
    fig3 = px.bar(resume, x="Period",
                  y=["Lease_Revenue", "Net_Cashflow"],
                  barmode="group",
                  title="CA vs Résultat par période")
    st.plotly_chart(fig3, use_container_width=True)

    fig4 = px.line(resume, x="Period",
                   y=["Encours_Leasing", "Encours_Debt"],
                   title="Encours Leasing vs Debt")
    st.plotly_chart(fig4, use_container_width=True)

# -------- Export CSV -------- #
csv = mensuel.to_csv(index=False).encode()
st.download_button("📥 Télécharger données mensuelles", csv, "mensuel.csv", "text/csv")

st.caption(f"⏱ Rafraîchissement auto : {REFRESH_EVERY_MIN} min • Données live Google Sheets")