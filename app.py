import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="MAHALLI | Real Retail Data DSS", page_icon="🛍️", layout="wide")
UCI_ZIP = "https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip"
UCI_PAGE = "https://archive.ics.uci.edu/dataset/352/online-retail"

@st.cache_data(show_spinner="Loading original UCI retail transactions…")
def load_data():
    import requests, zipfile
    r = requests.get(UCI_ZIP, timeout=120)
    r.raise_for_status()
    with zipfile.ZipFile(BytesIO(r.content)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".xlsx"))
        with z.open(name) as f:
            d = pd.read_excel(f, engine="openpyxl")
    d.columns = [str(c).strip() for c in d.columns]
    d["InvoiceNo"] = d["InvoiceNo"].astype(str)
    d["Description"] = d["Description"].fillna("Unknown product").astype(str).str.strip()
    d["InvoiceDate"] = pd.to_datetime(d["InvoiceDate"], errors="coerce")
    d["Quantity"] = pd.to_numeric(d["Quantity"], errors="coerce")
    d["UnitPrice"] = pd.to_numeric(d["UnitPrice"], errors="coerce")
    d["RevenueGBP"] = d["Quantity"] * d["UnitPrice"]
    d["Cancel"] = d["InvoiceNo"].str.upper().str.startswith("C") | (d["Quantity"]
