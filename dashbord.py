import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import random

import openrouteservice
from openrouteservice import distance_matrix, geocode, directions
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from openrouteservice import optimization
import networkx as nx
from shapely.geometry import LineString
import geopandas as gpd
import osmnx as ox


# API base URL
BASE_URL = "http://localhost:8000"


HUB_LATITUDE = 19.078810
HUB_LONGITUDE = 73.004064
HUB_COORDINATES = [HUB_LONGITUDE, HUB_LATITUDE]
DELIVERY_LOCATIONS = [
    [72.988493, 19.201999]  # Delivery Point 1 (longitude, latitude)
]
# ORS API Key
ORS_API_KEY = "5b3ce3597851110001cf6248b249d3ae95bc40bb877f4bc41b497fd3"
client = openrouteservice.Client(key=ORS_API_KEY)


# Streamlit app
st.title("Delivery Optimization Dashboard")

# Sidebar for navigation
menu = st.sidebar.selectbox("Menu", ["Home", "Submit Order", "Routes", "Metrics"])

# Predefined delivery locations
delivery_locations = {
    "Pune": {"latitude": 18.702718, "longitude": 73.883572},
    "Thane": {"latitude": 19.201999, "longitude": 72.988493},
    "Delhi": {"latitude": 30.422202, "longitude": 78.127151},
}



# Home Section
if menu == "Home":
    st.header("Welcome to the Delivery Optimization Dashboard")
    st.write("""
    - Visualize optimized delivery routes.
    - Monitor real-time delivery metrics.
    - Submit new orders for optimization and prediction.
    """)


# Submit Order Section
elif menu == "Submit Order":
    st.header("Submit a New Order")
    
    # Create two columns for Submit Order and Predict Delivery Time
    col1, col2 = st.columns(2)

    # Section for submitting a new order
    with col1:
        st.subheader("🚚 New Order Details")
        with st.form("order_form"):
            order_id = st.text_input("Order ID")
            delivery_lat = st.number_input("Delivery Latitude", step=0.0001, format="%.4f")
            delivery_lon = st.number_input("Delivery Longitude", step=0.0001, format="%.4f")
            delivery_location = st.selectbox("Select Delivery Location", list(delivery_locations.keys()))
            weight = st.number_input("Order Weight", min_value=1, step=1)
            submit_order = st.form_submit_button("Submit Order")

            if submit_order:
                selected_location = delivery_locations[delivery_location]
                order_data = {
                    "id": int(order_id),
                    "delivery_latitude": selected_location["latitude"] if delivery_lat == 0.0 else delivery_lat,
                    "delivery_longitude": selected_location["longitude"] if delivery_lon == 0.0 else delivery_lon,
                    "weight": int(weight)
                }
                st.write("Order Data:", order_data)  # Display the data being posted
                
                response = requests.post(f"{BASE_URL}/submit_order/", json=order_data)
                if response.status_code == 200:
                    st.success("Order submitted successfully!")
                else:
                    st.error("Failed to submit order.")
                

    # Section for predicting delivery time
    with col2:
        st.subheader("Predict Delivery Time")
        with st.form("predict_form"):
            delivery_lat = st.number_input("Delivery Latitude", step=0.0001, format="%.4f", key="predict_lat")
            delivery_lon = st.number_input("Delivery Longitude", step=0.0001, format="%.4f", key="predict_lon")
            delivery_location = st.selectbox("Select Delivery Location", list(delivery_locations.keys()))
            order_priority = st.selectbox("Order Priority", ["Low", "Medium", "High"])
            weight = st.number_input("Order Weight", min_value=1.0, step=1.0, format="%.2f")
            traffic_impact = st.number_input("Traffic Impact", min_value=0.0, step=0.1, format="%.1f")
            traffic_impact_1 = st.radio("Traffic Impact", ["Low", "Medium", "High"])
            weather_impact = st.select_slider("Weather Impact", options=[i * 0.10 for i in range(11)],
            format_func=lambda x: "Low" if x == 0 else ("High" if x == 1.0 else f"{x:.1f}"))
            predict_time = st.form_submit_button("Predict Delivery Time")

            if predict_time:
                selected_location = delivery_locations[delivery_location]
                order_priority_low = 1 if order_priority == "Low" else 0
                order_priority_medium = 1 if order_priority == "Medium" else 0
                traffic_impact_value = (random.uniform(0.14, 0.75)  if traffic_impact_1 == "Low" else 
                                        random.uniform(0.75,1.24) if traffic_impact_1 == "Medium" else 
                                        random.uniform(1.24, 2.09))

                predict_data = {
                    "delivery_latitude": selected_location["latitude"] if delivery_lat == 0.0 else delivery_lat,
                    "delivery_longitude": selected_location["longitude"] if delivery_lon == 0.0 else delivery_lon,
                    "order_priority_Low": order_priority_low,
                    "order_priority_Medium": order_priority_medium,
                    "order_weight": float(weight),
                    "traffic_impact": (traffic_impact if traffic_impact != 0.0 else traffic_impact_value),
                    "weather_impact": weather_impact
                }
                #st.write(predict_data)
                response = requests.post("http://127.0.0.1:8000/predict_delivery_time/", json=predict_data)
                if response.status_code == 200:
                    #predicted_time = response.json().get("predicted_delivery_time")
                    #st.success(f"Predicted Delivery Time: {predicted_time} minutes")
                    result = response.json()
                    predicted_time = result["predicted_delivery_time"]
                    st.markdown(f"""
                        ### Prediction Results
                        - **Order ID:** {result['order_id']}
                        - **Distance (km):** {result['distance_km']:.2f}
                        - **Congestion Level:** {result['congestion_level']}
                        - **Travel Time (minutes):** {result['travel_time_minute']:.2f} hrs
                        - **Predicted Delivery Time:** {predicted_time:.2f} hrs
                    """)
                    st.snow()
                else:
                    st.error("Failed to predict delivery time.")




# Routes Section
elif menu == "Routes":
    st.title("Optimized Delivery Routes")

    # Constants
    HUB_LATITUDE = 19.078810
    HUB_LONGITUDE = 73.004064
    HUB_COORDINATES = [HUB_LONGITUDE, HUB_LATITUDE]
    
    # Fetch orders from backend
    try:
        response = requests.get(f"{BASE_URL}/get_orders/")
        if response.status_code == 200:
            orders = response.json()
            DELIVERY_LOCATIONS = [
                [order['delivery_longitude'], order['delivery_latitude']] 
                for order in orders
            ]
        else:
            st.error("Failed to fetch orders. Using default locations.")
            DELIVERY_LOCATIONS = [[72.988493, 19.201999]]  # Default location
    except Exception as e:
        st.error(f"Error fetching orders: {e}")
        DELIVERY_LOCATIONS = [[72.988493, 19.201999]]

    # ORS API Key
    ORS_API_KEY = "5b3ce3597851110001cf6248b249d3ae95bc40bb877f4bc41b497fd3"
    client = openrouteservice.Client(key=ORS_API_KEY)

    # Function to fetch directions from OpenRouteService
    def get_route(client, start_point, end_point):
        try:
            route = client.directions(
                coordinates=[start_point, end_point],
                profile="driving-hgv",
                format="geojson",
            )
            return route
        except openrouteservice.exceptions.ApiError as e:
            st.error(f"OpenRouteService API Error: {e}")
            return None

    # Function to display routes on the map
    def display_routes_on_map(routes, hub_coordinates):
        m = folium.Map(location=[HUB_LATITUDE, HUB_LONGITUDE], zoom_start=12)

        # Add hub marker
        folium.Marker(
            location=[HUB_LATITUDE, HUB_LONGITUDE],
            popup="Hub",
            icon=folium.Icon(color="green", icon="home"),
        ).add_to(m)

        # Plot routes for each delivery location
        for idx, route in enumerate(routes):
            if route and 'features' in route:
                coordinates = route["features"][0]["geometry"]["coordinates"]
                route_coords = [(coord[1], coord[0]) for coord in coordinates]

                # Add route polyline
                folium.PolyLine(route_coords, color="red", weight=4, opacity=0.7).add_to(m)

                # Add delivery point markers
                folium.Marker(
                    route_coords[-1],
                    popup=f"Delivery Point {idx+1}",
                    icon=folium.Icon(color="blue")
                ).add_to(m)

        st_folium(m, width=700, height=500)

    # Main logic
    st.header("Live Delivery Routes")
    
    if DELIVERY_LOCATIONS:
        # Generate routes from hub to each delivery point
        routes = []
        for delivery_point in DELIVERY_LOCATIONS:
            route = get_route(client, HUB_COORDINATES, delivery_point)
            if route:
                routes.append(route)
        
        if routes:
            display_routes_on_map(routes, HUB_COORDINATES)
        else:
            st.warning("No routes could be generated for current orders.")
    else:
        st.info("No delivery orders found. Submit orders to see routes.")

# Metrics Section
elif menu == "Metrics":
    st.header("Operational Metrics")
    
    # Constants
    HUB_LATITUDE = 19.078810
    HUB_LONGITUDE = 73.004064
    HUB_COORDINATES = [HUB_LONGITUDE, HUB_LATITUDE]
    ORS_API_KEY = "5b3ce3597851110001cf6248b249d3ae95bc40bb877f4bc41b497fd3"
    client = openrouteservice.Client(key=ORS_API_KEY)

    # Fetch orders from backend
    try:
        response = requests.get(f"{BASE_URL}/get_orders/")
        if response.status_code == 200:
            orders = response.json()
            DELIVERY_LOCATIONS = [
                [order['delivery_longitude'], order['delivery_latitude']]
                for order in orders
            ]
        else:
            st.error("Failed to fetch orders. Using sample data.")
            DELIVERY_LOCATIONS = [[72.988493, 19.201999]]  # Sample location
    except Exception as e:
        st.error(f"Error fetching orders: {e}")
        DELIVERY_LOCATIONS = [[72.988493, 19.201999]]

    # Function to fetch distance matrix
    def get_distance_matrix(hub_coordinates, delivery_points):
        try:
            if not delivery_points:
                return None
                
            locations = [hub_coordinates] + delivery_points
            response = client.distance_matrix(
                locations=locations,
                profile="driving-car",
                metrics=["distance", "duration"],
            )
            return response
        except Exception as e:
            st.error(f"Error fetching distance matrix: {e}")
            return None

    # Function to display metrics
    def display_metrics(matrix):
        if not matrix:
            st.warning("No metrics data available")
            return

        # Create DataFrames
        distances = matrix["distances"]
        durations = matrix["durations"]
        
        # Generate location labels
        location_labels = ["Hub"] + [f"Order {i+1}" for i in range(len(DELIVERY_LOCATIONS))]
        
        distance_df = pd.DataFrame(
            distances,
            index=location_labels,
            columns=location_labels
        )
        
        duration_df = pd.DataFrame(
            durations,
            index=location_labels,
            columns=location_labels
        )

        # Display matrices
        st.subheader("Live Distance Matrix (meters)")
        st.dataframe(distance_df.style.background_gradient(cmap="Blues"))

        st.subheader("Live Duration Matrix (seconds)")
        st.dataframe(duration_df.style.background_gradient(cmap="Greens"))

        # Visualization Section
        st.header("Data Visualizations")
        
        # Distance to Orders
        st.subheader("Distance from Hub to Orders")
        fig = px.bar(
            x=location_labels[1:],
            y=distance_df.iloc[0][1:],
            labels={'x': 'Order', 'y': 'Distance (meters)'},
            color=distance_df.iloc[0][1:],
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig)

        # Duration to Orders
        st.subheader("Delivery Duration from Hub to Orders")
        fig = px.line(
            x=location_labels[1:],
            y=duration_df.iloc[0][1:],
            labels={'x': 'Order', 'y': 'Duration (seconds)'},
            markers=True
        )
        st.plotly_chart(fig)

        # Combined Metrics
        st.subheader("Combined Order Metrics")
        metrics_df = pd.DataFrame({
            'Order': location_labels[1:],
            'Distance (km)': [d/1000 for d in distance_df.iloc[0][1:]],
            'Duration (hours)': [t/3600 for t in duration_df.iloc[0][1:]]
        })
        st.dataframe(metrics_df)

        # Scatter Plot: Distance vs Duration
        st.subheader("Distance vs Duration Correlation")
        fig = px.scatter(
            metrics_df,
            x='Distance (km)',
            y='Duration (hours)',
            size='Distance (km)',
            color='Order',
            trendline="ols"
        )
        st.plotly_chart(fig)

    # Main display logic
    if DELIVERY_LOCATIONS:
        matrix = get_distance_matrix(HUB_COORDINATES, DELIVERY_LOCATIONS)
        display_metrics(matrix)
        st.info("No delivery orders found. Submit orders to view metrics.")


# Add floating animation to the title
st.markdown("""
<script>
// Add floating animation to the title
const title = window.parent.document.querySelector('h1');
if (title) {
    title.style.animation = 'float 3s ease-in-out infinite';
}

// Add animation keyframes
const style = document.createElement('style');
style.textContent = `
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
`;
document.head.appendChild(style);
</script>
""", unsafe_allow_html=True)