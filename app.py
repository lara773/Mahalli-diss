import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="MAHALLI | Decision Support", page_icon="🛍️", layout="wide")

ROOT = Path(__file__).parent

# Accept CSV files either in the repository root (current GitHub upload)
# or in a /data folder (the intended project structure).
def data_file(filename):
    root_file = ROOT / filename
    data_folder_file = ROOT / "data" / filename
    if root_file.exists():
        return root_file
    if data_folder_file.exists():
        return data_folder_file
    raise FileNotFoundError(
        f"Missing {filename}. Upload it to the repository root or the data/ folder."
    )

@st.cache_data
def load_data():
    products = pd.read_csv(data_file("products.csv"))
    sales = pd.read_csv(data_file("sales.csv"))
    inventory = pd.read_csv(data_file("inventory.csv"))
    agencies = pd.read_csv(data_file("marketing_agencies.csv"))
    return products, sales, inventory, agencies

products, sales, inventory, agencies = load_data()

st.title("🛍️ MAHALLI")
st.caption("Saudi Small Business Marketplace · Decision Support System")
st.info("Prototype using synthetic course-project data. Recommendations support human decisions; they do not execute actions.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview", "Marketing", "Pricing", "Inventory", "Agency Trust"
])

with tab1:
    st.subheader("Business overview")
    total_sales = int(sales["units_sold"].sum())
    revenue = float(sales["revenue_sar"].sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Units sold", f"{total_sales:,}")
    c2.metric("Revenue", f"SAR {revenue:,.0f}")
    c3.metric("Products", f"{len(products):,}")
    st.subheader("Sales by product")
    by_product = sales.groupby("product_id", as_index=False)["revenue_sar"].sum()
    by_product = by_product.merge(products[["product_id", "product_name"]], on="product_id")
    st.bar_chart(by_product.set_index("product_name")["revenue_sar"])
    st.caption("All figures are generated for demonstration and are not real marketplace results.")

with tab2:
    st.subheader("Marketing decision support")
    marketing = sales.groupby("product_id", as_index=False).agg(
        units=("units_sold", "sum"), revenue=("revenue_sar", "sum")
    ).merge(products, on="product_id")
    marketing["margin_pct"] = ((marketing["selling_price_sar"] - marketing["unit_cost_sar"]) /
                               marketing["selling_price_sar"] * 100).round(1)
    marketing["marketing_score"] = (
        marketing["units"].rank(pct=True) * 0.45 +
        marketing["margin_pct"].rank(pct=True) * 0.35 +
        marketing["rating"].rank(pct=True) * 0.20
    ).round(3)
    marketing = marketing.sort_values("marketing_score", ascending=False)
    st.write("Products ranked using sales volume (45%), margin percentage (35%), and rating (20%). This is a transparent prototype heuristic, not a trained predictive model.")
    st.dataframe(marketing[["product_name","units","revenue","margin_pct","rating","marketing_score"]], use_container_width=True)
    st.success(f"First product to review for promotion: {marketing.iloc[0]['product_name']}")
    st.warning("Check available inventory and approve the campaign budget before launching any promotion.")

with tab3:
    st.subheader("Pricing decision support")
    chosen = st.selectbox("Choose a product", products["product_name"].tolist(), key="price_product")
    p = products.loc[products["product_name"] == chosen].iloc[0]
    suggested = float(p["unit_cost_sar"]) / (1 - 0.30)
    a, b, c = st.columns(3)
    a.metric("Current price", f"SAR {p['selling_price_sar']:.2f}")
    b.metric("Unit cost", f"SAR {p['unit_cost_sar']:.2f}")
    c.metric("Price for 30% gross margin", f"SAR {suggested:.2f}")
    st.caption("Formula: minimum price = unit cost ÷ (1 − target gross margin). Excludes platform fees, shipping, tax and other costs.")

with tab4:
    st.subheader("Inventory decision support")
    inv = inventory.merge(products[["product_id","product_name"]], on="product_id")
    inv["estimated_daily_demand"] = inv["avg_daily_units"]
    inv["suggested_reorder"] = (inv["estimated_daily_demand"] * inv["lead_time_days"] +
                                inv["safety_stock_units"] - inv["current_stock"]).clip(lower=0).round().astype(int)
    st.write("Reorder suggestion = average daily demand × lead time + safety stock − current stock.")
    st.dataframe(inv[["product_name","current_stock","avg_daily_units","lead_time_days",
                      "safety_stock_units","suggested_reorder"]], use_container_width=True)
    st.caption("This is a simple baseline. Validate demand assumptions and supplier lead times before ordering.")

with tab5:
    st.subheader("Marketing Agency Trust & Performance Advisor")
    st.write("Assess whether an agency's sales promises are measurable and supported by evidence.")
    agency_name = st.selectbox("Choose a sample agency", agencies["agency_name"].tolist())
    agency = agencies.loc[agencies["agency_name"] == agency_name].iloc[0]
    st.write(f"**Claim:** {agency['sales_claim']}")
    st.write(f"**Evidence supplied:** {agency['performance_evidence']}")
    st.write(f"**Portfolio:** {agency['portfolio_evidence']}")
    st.write(f"**Contract:** {agency['contract_evidence']}")
    st.write(f"**Payment terms:** {agency['payment_terms']}")
    st.warning("Initial review: request independently verifiable baseline sales, campaign dates, attribution method and source-platform evidence. Missing evidence is not proof of fraud.")
    st.caption("Sample agencies are fictional. This tool is a screening aid, not a fraud detector or legal opinion.")

st.divider()
st.caption("MAHALLI BAIS 400 prototype · Human approval required for pricing, marketing, purchasing and contracting decisions.")
