# MAHALLI — Real Retail Data DSS

Streamlit decision-support prototype using the UCI Online Retail dataset.

## Data source
Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33. Licensed CC BY 4.0.

The dataset contains 541,909 transaction records from a UK-based online retailer between 1 December 2010 and 9 December 2011. Prices are in GBP.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

The app downloads the original UCI ZIP at runtime and caches processed data. It excludes cancellations and negative-quantity returns from sales calculations. The source does not contain stock-on-hand, supplier lead times, acquisition costs, ad spend, or agency contracts. The app therefore asks the user to enter inventory inputs, reports historical selling prices rather than profit margins, and uses a manually completed agency evidence checklist rather than fictional agency records.
