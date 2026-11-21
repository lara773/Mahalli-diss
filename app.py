import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
import zipfile
import math

st.set_page_config(page_title="MAHALLI | Real Retail Data DSS", page_icon="🛍️", layout="wide")

UCI_ZIP = "https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip"
UCI_PAGE = "https://archive.ics.uci.edu/dataset/352/online-retail"


@st.cache_data(show_spinner="Loading original UCI retail transactions...")
def load_data():
    try:
        r = requests.get(UCI_ZIP, timeout=120)
        r.raise_for_status()
        with zipfile.ZipFile(BytesIO(r.content)) as z:
            name = [n for n in z.namelist() if n.lower().endswith(".xlsx")][0]
            with z.open(name) as f:
                df = pd.read_excel(f, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        required = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "Country"]
        for col in required:
            if col not in df.columns:
                st.error(f"Missing required column: {col}")
                st.stop()
        df["InvoiceNo"] = df["InvoiceNo"].astype(str)
        df["Description"] = df["Description"].fillna("Unknown product").astype(str).str.strip()
        df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
        df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
        df["RevenueGBP"] = df["Quantity"] * df["UnitPrice"]
        df["Cancel"] = df["InvoiceNo"].str.upper().str.startswith("C") | (df["Quantity"] &lt;= 0)
        df = df.dropna(subset=["InvoiceDate", "Quantity", "UnitPrice"])
        df = df[(df["Quantity"] &gt; 0) & (df["UnitPrice"] &gt; 0) & (~df["Cancel"])].copy()
        df["Date"] = df["InvoiceDate"].dt.date
        return df
    except Exception as e:
        st.error(f"Failed to load dataset from UCI: {e}")
        st.stop()


df = load_data()

st.title("MAHALLI")
st.caption("Saudi Small Business Marketplace · Decision Support System")
st.info(
    "This application analyzes **historical UK retail transaction data** "
    "from the UCI Online Retail dataset (Dec 2010 - Dec 2011) to support "
    "business intelligence for Saudi small-business retailers. "
    "All metrics below are derived from **real, published transactions**; "
    "they reflect the UK market of the study period and are provided as "
    "reference signals only. Human approval and local-market validation "
    "must precede any operational decision."
)

# ---------- SIDEBAR FILTERS ----------
st.sidebar.header("Filters")
countries = sorted(df["Country"].unique().tolist())
country_list = ["All countries"] + countries
selected_country = st.sidebar.selectbox(
    "Country", country_list,
    index=country_list.index("United Kingdom") if "United Kingdom" in country_list else 1
)
date_min = df["InvoiceDate"].min()
date_max = df["InvoiceDate"].max()
date_range = st.sidebar.date_input(
    "Date range",
    value=(date_min.date(), date_max.date()),
    min_value=date_min.date(),
    max_value=date_max.date(),
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range[0]

# ---------- FILTER DATA ----------
mask = (
    (df["Country"] == selected_country)
    & (df["InvoiceDate"].dt.date &gt;= start_date)
    & (df["InvoiceDate"].dt.date &lt;= end_date)
)
filtered = df[mask].copy()

if filtered.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

# ---------- INFO BAR ----------
st.markdown("---")
st.markdown(
    f"**Source:** {UCI_PAGE} | "
    f"**Period:** {date_min.date()} - {date_max.date()} | "
    f"**Currency:** GBP | "
    "*This is historical UK data (2010-2011), not current Saudi market data.*"
)
st.markdown("---")

# ---------- TABS ----------
tab_overview, tab_product, tab_pricing, tab_inventory, tab_agency = st.tabs(
    ["Overview", "Product Analysis", "Pricing", "Inventory", "Agency Trust"]
)

# ===== OVERVIEW =====
with tab_overview:
    total_rev = filtered["RevenueGBP"].sum()
    total_units = int(filtered["Quantity"].sum())
    total_invoices = filtered["InvoiceNo"].nunique()
    col1, col2, col3 = st.columns(3)
    col1.metric("Revenue (GBP)", f"GBP {total_rev:,.2f}")
    col2.metric("Units Sold", f"{total_units:,}")
    col3.metric("Invoices", f"{total_invoices:,}")

    st.subheader("Monthly Revenue")
    filtered["Month"] = filtered["InvoiceDate"].dt.to_period("M").astype(str)
    monthly = filtered.groupby("Month")["RevenueGBP"].sum().reset_index()
    st.line_chart(monthly.set_index("Month"), y="RevenueGBP")

    st.subheader("Top 10 Countries")
    top10 = filtered.groupby("Country")["RevenueGBP"].sum().nlargest(10).reset_index()
    st.bar_chart(top10.set_index("Country"), y="RevenueGBP")

# ===== PRODUCT ANALYSIS =====
with tab_product:
    st.subheader("Top 30 Products by Revenue")
    prod = filtered.groupby(["StockCode", "Description"]).agg(
        units_sold=("Quantity", "sum"),
        revenue_gbp=("RevenueGBP", "sum"),
        unique_invoices=("InvoiceNo", "nunique"),
    ).reset_index()
    prod = prod.sort_values("revenue_gbp", ascending=False).head(30)
    st.dataframe(prod, use_container_width=True)
    csv = prod.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV", data=csv, file_name="top_products.csv", mime="text/csv"
    )

# ===== PRICING =====
with tab_pricing:
    st.subheader("Product Pricing Analysis")
    pric = filtered.groupby("Description").agg(
        avg_unit_price=("UnitPrice", "mean"),
        median_unit_price=("UnitPrice", "median"),
        revenue_gbp=("RevenueGBP", "sum"),
        total_units=("Quantity", "sum"),
    ).reset_index()
    pric = pric.sort_values("revenue_gbp", ascending=False).head(200)
    st.dataframe(pric, use_container_width=True)

    desc_sel = st.selectbox("Select Description", pric["Description"].tolist())
    sel_pric = pric[pric["Description"] == desc_sel].iloc[0]
    st.write(f"**Average Unit Price:** GBP {sel_pric['avg_unit_price']:.4f}")
    st.write(f"**Median Unit Price:** GBP {sel_pric['median_unit_price']:.4f}")
    st.write(f"**Total Units Sold:** {int(sel_pric['total_units']):,}")

    st.subheader("Monthly Average Unit-Price Trend")
    filtered_temp = filtered[filtered["Description"] == desc_sel].copy()
    filtered_temp["Month"] = filtered_temp["InvoiceDate"].dt.to_period("M").astype(str)
    monthly_price = filtered_temp.groupby("Month")["UnitPrice"].mean().reset_index()
    if not monthly_price.empty:
        st.line_chart(monthly_price.set_index("Month"), y="UnitPrice")
    else:
        st.info("No data for this description in the filtered period.")

    st.warning(
        "**Important:** This dataset contains observed UK retail prices from 2010-2011. "
        "It does **not** include acquisition costs, platform fees, shipping charges, or "
        "current Saudi retail prices. **No profit margin or Saudi-price recommendation "
        "can be derived from these figures alone.**"
    )

# ===== INVENTORY =====
with tab_inventory:
    st.subheader("Product Inventory Estimates")
    inv = filtered.groupby(["StockCode", "Description"]).agg(
        total_quantity=("Quantity", "sum"),
        first_date=("InvoiceDate", "min"),
        last_date=("InvoiceDate", "max"),
    ).reset_index()
    inv["active_days"] = (inv["last_date"] - inv["first_date"]).dt.days.clip(lower=1) + 1
    inv["avg_daily_demand"] = inv["total_quantity"] / inv["active_days"]
    inv = inv.sort_values("total_quantity", ascending=False).head(200)

    st.dataframe(
        inv[["StockCode", "Description", "total_quantity", "avg_daily_demand", "first_date", "last_date", "active_days"]],
        use_container_width=True,
    )

 prod_sel = st.selectbox("Select Product", inv["Description"].tolist())
 sel_inv = inv[inv["Description"] == prod_sel].iloc[0]

 st.write(f"**StockCode:** {sel_inv['StockCode']}")
 st.write(f"**Total Quantity:** {int(sel_inv['total_quantity']):,}")
 st.write(f"**Estimated Daily Demand:** {sel_inv['avg_daily_demand']:.2f} units/day")
 st.write(f"**Active Days:** {int(sel_inv['active_days'])}")

 current_stock = st.number_input("Current Stock (units)", min_value=0, value=0, key="current_stock")
 lead_time = st.number_input("Supplier Lead Time (days)", min_value=1, value=7, key="lead_time")
 safety_stock = st.number_input("Safety Stock (units)", min_value=0, value=5, key="safety_stock")

 reorder_point = sel_inv["avg_daily_demand"] * lead_time + safety_stock
 suggested_qty = max(0, math.ceil(reorder_point - current_stock))

 st.metric("Reorder Point", f"{reorder_point:.1f} units")
 st.metric("Suggested Order Qty", f"{suggested_qty:,} units")

    if current_stock &lt;= reorder_point:
 st.warning("Stock is at or below the reorder point. Consider ordering soon.")
    else:
 st.success("Stock is above the reorder point. No immediate action needed.")

 st.info(
        "This is a **baseline estimate** based on historical average demand. "
        "It does not account for seasonality, promotions, supply-chain variability, "
        "or minimum order quantities (MOQ). Always validate with demand forecasting, "
        "stock-level review, lead-time reliability, and supplier MOQ constraints."
    )

# ===== AGENCY TRUST =====
with tab_agency:
 st.subheader("Marketing-Agency Screening Checklist")
 checks = [
        "1. Clear KPI / target defined with the agency",
        "2. Documented baseline sales and reporting dates",
        "3. Target period and reporting cadence established",
        "4. Attribution method agreed (first-touch, last-touch, etc.)",
        "5. Original analytics / data source verifiable independently",
        "6. Ad spend and platform fees tracked separately",
        "7. Returns, cancellations, and exclusion criteria defined",
        "8. Agency portfolio and client references verifiable",
        "9. Written scope, deliverables, payment terms, and cancellation policy",
    ]
 done = []
    for i, c in enumerate(checks, 1):
 done.append(st.checkbox(c, value=False, key=f"check_{i}"))

 unchecked = sum(1 for d in done if not d)
 st.write(f"**Checks completed:** {sum(done)} / {len(checks)}")
    if unchecked:
 st.warning(f"{unchecked} unchecked item(s) means **unconfirmed**, not proof of fraud.")
 st.info(
        "This checklist is a **screening aid**, not a fraud detector. "
        "Always conduct independent verification and legal review before engagement."
    )

# ---------- FOOTER ----------
st.markdown("---")
st.caption(
    "Chen, M. (2015). UCI Online Retail Dataset. "
    "DOI: 10.24432/C5BW33. Licensed under CC BY 4.0. "
    "Prices are in GBP. This dataset reflects historical UK transactions "
    "(Dec 2010 - Dec 2011) and is not current Saudi market data. "
    f"[Dataset Link]({UCI_PAGE})"
)
