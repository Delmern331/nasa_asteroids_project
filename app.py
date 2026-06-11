import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os


API_KEY = "DEMO_KEY"
BASE_URL = "https://api.nasa.gov/neo/rest/v1/feed"
CSV_FILENAME = "asteroids.csv"

def fetch_nasa_data(start_date, end_date):
    """Отримує дані з NASA API, розбиваючи запити на 7-денні проміжки."""
    all_asteroids = []
    current_start = start_date
    
    
    while current_start <= end_date:
        current_end = current_start + timedelta(days=6)
        if current_end > end_date:
            current_end = end_date
            
        params = {
            "start_date": current_start.strftime("%Y-%m-%d"),
            "end_date": current_end.strftime("%Y-%m-%d"),
            "api_key": API_KEY
        }
        
        response = requests.get(BASE_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            near_earth_objects = data.get("near_earth_objects", {})
            for date_key, asteroids in near_earth_objects.items():
                all_asteroids.extend(asteroids)
        else:
            st.error(f"Помилка отримання даних: {response.status_code}")
            return None
            
        current_start = current_end + timedelta(days=1)
        
    return all_asteroids

def process_data(raw_data):
    """Перетворює список JSON-словників у Pandas DataFrame та обчислює потрібні поля."""
    if not raw_data:
        return pd.DataFrame()
        
    processed_list = []
    for ast in raw_data:
        try:
            
            name = ast.get("name", "Unknown")
            is_hazardous = ast.get("is_potentially_hazardous_asteroid", False)
            
            
            d_min = ast["estimated_diameter"]["meters"]["estimated_diameter_min"]
            d_max = ast["estimated_diameter"]["meters"]["estimated_diameter_max"]
            d_avg = (d_min + d_max) / 2
            
            
            approach_data = ast.get("close_approach_data", [])
            if approach_data:
                date = approach_data[0]["close_approach_date"]
                
                velocity = float(approach_data[0]["relative_velocity"]["kilometers_per_hour"])
                miss_distance = float(approach_data[0]["miss_distance"]["kilometers"])
                orbiting_body = approach_data[0]["orbiting_body"]
            else:
                continue 
                
            processed_list.append({
                "name": name,
                "date": date,
                "is_hazardous": is_hazardous,
                "diameter_min_m": d_min,
                "diameter_max_m": d_max,
                "diameter_avg_m": d_avg,
                "velocity_kmh": velocity,
                "miss_distance_km": miss_distance,
                "orbiting_body": orbiting_body
            })
        except KeyError as e:
            continue
            
    df = pd.DataFrame(processed_list)
    return df

def main():
    st.set_page_config(page_title="Аналіз Астероїдів NASA", layout="wide")
    st.title("Аналіз навколоземних астероїдів (NASA NEO API)")
    
    
    st.sidebar.header("Налаштування пошуку")
    mode = st.sidebar.radio(
        "Оберіть період:",
        ["Попередні 7 днів", "Наступні 7 днів", "Власний діапазон"]
    )
    
    today = datetime.today()
    
    if mode == "Попередні 7 днів":
        start_date = today - timedelta(days=7)
        end_date = today
    elif mode == "Наступні 7 днів":
        start_date = today
        end_date = today + timedelta(days=7)
    else:
        start_date = st.sidebar.date_input("Початкова дата", today - timedelta(days=3))
        end_date = st.sidebar.date_input("Кінцева дата", today)
        
        start_date = datetime.combine(start_date, datetime.min.time())
        end_date = datetime.combine(end_date, datetime.min.time())

    if start_date > end_date:
        st.sidebar.error("Початкова дата не може бути більшою за кінцеву!")
        return

    
    if st.sidebar.button("Отримати дані"):
        with st.spinner("Завантаження даних з NASA... Це може зайняти певний час."):
            raw_data = fetch_nasa_data(start_date, end_date)
            
            if raw_data:
                df = process_data(raw_data)
                
                if df.empty:
                    st.warning("За обраний період астероїдів не знайдено.")
                    return
                
                
                df.to_csv(CSV_FILENAME, index=False)
                st.success(f"Дані успішно завантажено та збережено у файл {CSV_FILENAME}!")
                
                
                st.header("Зведена статистика")
                col1, col2, col3, col4, col5 = st.columns(5)
                
                total_asteroids = len(df)
                hazardous_count = df["is_hazardous"].sum()
                closest_ast = df.loc[df["miss_distance_km"].idxmin()]
                largest_ast = df.loc[df["diameter_max_m"].idxmax()]
                fastest_ast = df.loc[df["velocity_kmh"].idxmax()]
                
                col1.metric("Загальна кількість", total_asteroids)
                col2.metric("Небезпечних", hazardous_count)
                col3.metric("Найближчий (км)", f"{closest_ast['miss_distance_km']:,.0f}", help=closest_ast["name"])
                col4.metric("Найбільший (м)", f"{largest_ast['diameter_max_m']:,.0f}", help=largest_ast["name"])
                col5.metric("Найшвидший (км/год)", f"{fastest_ast['velocity_kmh']:,.0f}", help=fastest_ast["name"])
                
                st.subheader("Таблиця даних")
                st.dataframe(df)
                
                
                st.header("Графічний аналіз")
                
                # Графік 1: Кількість за днями
                st.subheader("Кількість астероїдів за днями")
                count_by_date = df.groupby("date").size().reset_index(name="count")
                fig1 = px.bar(count_by_date, x="date", y="count", text="count", color="count", color_continuous_scale="Viridis")
                st.plotly_chart(fig1, use_container_width=True)
                
                col_chart1, col_chart2 = st.columns(2)
                
                
                with col_chart1:
                    st.subheader("Небезпечні vs Безпечні")
                    fig2 = px.pie(df, names="is_hazardous", hole=0.4, color="is_hazardous", 
                                  color_discrete_map={True: "red", False: "green"})
                    st.plotly_chart(fig2, use_container_width=True)
                    
                
                with col_chart2:
                    st.subheader("Топ-10 найближчих астероїдів")
                    top10_closest = df.nsmallest(10, "miss_distance_km").sort_values("miss_distance_km", ascending=False)
                    fig3 = px.bar(top10_closest, x="miss_distance_km", y="name", orientation="h", text_auto=".2s")
                    st.plotly_chart(fig3, use_container_width=True)
                
                
                st.subheader("Залежність: Розмір астероїда та Відстань до Землі")
                fig4 = px.scatter(df, x="miss_distance_km", y="diameter_avg_m", color="is_hazardous", 
                                  hover_name="name", size="velocity_kmh", 
                                  labels={"miss_distance_km": "Відстань до Землі (км)", "diameter_avg_m": "Середній діаметр (м)"})
                st.plotly_chart(fig4, use_container_width=True)

if __name__ == "__main__":
    main()