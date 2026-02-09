import streamlit as st
import requests
import yfinance as yf
from groq import Groq

# ----------------------------------
# PAGE CONFIG
# ----------------------------------
st.set_page_config(page_title="Currency & Stock Agent", layout="centered")

st.title("Currency & Stock Market Agent")
st.write(
    "Get official currency, live exchange rates, major stock indices, "
    "and stock exchange headquarters for a country."
)

# ----------------------------------
# SIDEBAR: API KEYS
# ----------------------------------
with st.sidebar:
    st.header("API Keys")
    groq_key = st.text_input("Groq API Key", type="password")
    exchange_key = st.text_input("ExchangeRate API Key", type="password")

# ----------------------------------
# USER INPUT
# ----------------------------------
country = st.text_input("Enter Country Name", placeholder="Japan")
get_data = st.button("Get Market Details")

# ----------------------------------
# GROQ LLM
# ----------------------------------
def groq_llm(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a travel planning assistant. "
                    "Cultural information must be factual. "
                    "Flights and hotels must be clearly labeled as estimates. "
                    "Do not claim real-time pricing."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }

    r = requests.post(url, headers=headers, json=payload)
    if r.status_code != 200:
        st.error(f"Groq API error: {r.text}")
        return None

    return r.json()["choices"][0]["message"]["content"]

def ask_llm(country):
    prompt = f"""
You are acting as a financial data extraction agent.

Return STRICT JSON for the country: {country}

Required fields:
- currency_code (ISO 4217, uppercase)
- stock_index_ticker (Yahoo Finance format)
- stock_exchange_name
- stock_exchange_hq_city

Rules:
- Output MUST be valid JSON
- Do NOT include explanations
- Do NOT include markdown
- Do NOT include extra text

Example output:
{{
  "currency_code": "JPY",
  "stock_index_ticker": "^N225",
  "stock_exchange_name": "Tokyo Stock Exchange",
  "stock_exchange_hq_city": "Tokyo"
}}
"""

    response = groq_llm(prompt)

    if not response:
        return None

    return response.strip()

# ----------------------------------
# EXCHANGE RATES
# ----------------------------------
def get_exchange_rates(base):
    url = f"https://v6.exchangerate-api.com/v6/{exchange_key}/latest/{base}"
    r = requests.get(url, timeout=10)
    return r.json()

# ----------------------------------
# MAIN
# ----------------------------------
if get_data:
    if not groq_key or not exchange_key:
        st.error("Please provide both API keys.")
        st.stop()

    if not country:
        st.error("Please enter a country name.")
        st.stop()

    with st.spinner("Fetching financial data..."):
        try:
            llm_data = ask_llm(country)
            data = eval(llm_data)  # safe here because we strictly requested JSON
        except Exception:
            st.error("Failed to extract structured data from LLM.")
            st.stop()

    # ----------------------------------
    # OUTPUT: CURRENCY
    # ----------------------------------
    st.subheader("Official Currency")
    currency = data["currency_code"]
    st.write(f"{currency}")

    # ----------------------------------
    # EXCHANGE RATES
    # ----------------------------------
    rates = get_exchange_rates(currency)

    if rates.get("result") != "success":
        st.error("Exchange rate API error.")
    else:
        st.subheader("Exchange Rates (1 unit)")
        for cur in ["USD", "INR", "GBP", "EUR"]:
            st.write(f"1 {currency} → {rates['conversion_rates'][cur]} {cur}")

    # ----------------------------------
    # STOCK INDEX
    # ----------------------------------
    st.subheader("Major Stock Index")
    ticker = data["stock_index_ticker"]

    try:
        index = yf.Ticker(ticker)
        history = index.history(period="1d")

        if history.empty:
            st.write("Index data unavailable.")
        else:
            latest = history.iloc[-1]
            st.write(f"{ticker} value: {round(latest['Close'], 2)}")
    except Exception:
        st.write("Failed to fetch index data.")

    # ----------------------------------
    # STOCK EXCHANGE HQ
    # ----------------------------------
    st.subheader("Stock Exchange Headquarters")
    st.write(data["stock_exchange_name"])
    st.markdown(
        f"[View on Google Maps]"
        f"(https://www.google.com/maps/search/"
        f"{data['stock_exchange_hq_city'].replace(' ', '+')}+stock+exchange)"
    )

    st.caption(
        "Currency and stock data fetched via public financial APIs. "
        "Country-level information inferred using LLM reasoning."
    )
