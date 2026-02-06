import streamlit as st
import requests
import json
from datetime import datetime, timedelta

# ----------------------------------
# PAGE CONFIG
# ----------------------------------
st.set_page_config(
    page_title="AI Travel Planner",
    layout="wide"
)
st.title("AI Travel Planning Agent")
st.write(
    "An agent-based travel planner using real-time weather data "
    "and LLM-powered estimates for flights, hotels, and itineraries."
)

# ----------------------------------
# SIDEBAR: API KEYS
# ----------------------------------
with st.sidebar:
    st.header("API Keys")
    weather_key = st.text_input("OpenWeather API Key", type="password")
    groq_key = st.text_input("Groq API Key", type="password")

# ----------------------------------
# USER INPUT (NO PARSING)
# ----------------------------------
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    city = st.text_input("Destination City", placeholder="Tokyo")

with col2:
    days = st.number_input("Trip Duration (days)", min_value=1, max_value=14, value=3)

with col3:
    month = st.text_input("Travel Month", placeholder="May")

generate = st.button("Generate Trip Plan")

# ----------------------------------
# WEATHER FUNCTIONS (AS REQUESTED)
# ----------------------------------
def get_current_weather(city):
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={weather_key}&units=metric"
    )
    return requests.get(url).json()


def get_forecast(city):
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?q={city}&appid={weather_key}&units=metric"
    )
    return requests.get(url).json()

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

# ----------------------------------
# MAIN EXECUTION
# ----------------------------------
if generate:
    if not weather_key or not groq_key:
        st.error("Please provide both OpenWeather and Groq API keys.")
        st.stop()

    if not city or not month:
        st.error("Please fill in all trip details.")
        st.stop()

    with st.spinner("Planning your trip..."):
        weather_data = get_current_weather(city)
        forecast_data = get_forecast(city)

        if weather_data.get("cod") != 200:
            st.error(f"Weather error: {weather_data.get('message')}")
            st.stop()

        llm_prompt = f"""
        Plan a {days}-day trip to {city} in {month}.

        Include:
        - One paragraph on cultural and historical significance
        - Expected weather conditions for {month} (climatological, not real-time)
        - Estimated flight options with price ranges (label as estimates)
        - Estimated hotel options with price ranges
        - Day-wise itinerary
        """

        trip_plan = groq_llm(llm_prompt)

    # ----------------------------------
    # OUTPUT
    # ----------------------------------
    st.subheader(f"{city}: Travel Overview")
    st.write(trip_plan if trip_plan else "Trip plan unavailable.")

    st.subheader("Current Weather (Real-Time)")
    st.write(
        f"{weather_data['main']['temp']}°C, "
        f"{weather_data['weather'][0]['description']}, "
        f"Humidity: {weather_data['main']['humidity']}%"
    )

    st.subheader("Short-Term Forecast (Next Few Days)")
    shown = 0
    for item in forecast_data.get("list", []):
        if "12:00:00" in item["dt_txt"]:
            st.write(
                f"{item['dt_txt'].split()[0]}: "
                f"{item['weather'][0]['description']}, "
                f"{item['main']['temp']}°C"
            )
            shown += 1
            if shown >= days:
                break

    st.caption(
        "Weather data is fetched from OpenWeather Free API (current + 5-day forecast). "
        "Flights, hotels, and itineraries are AI-generated estimates using Groq."
    )
