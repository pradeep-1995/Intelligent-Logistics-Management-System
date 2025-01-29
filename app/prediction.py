import joblib
import pandas as pd
import numpy as np
import requests

# Load the logistic regression model
model_path = "model\Logistic_model.pkl"
with open(model_path, "rb") as model_file:
    logistic_model = joblib.load(model_file)

# Prediction function
GRAPH_HOPPER_API_KEY = "3812daea-815d-4f8c-bb9f-25888711467e"
BASE_URL = "https://graphhopper.com/api/1/route"

def fetch_graphhopper_features(hub_lat, hub_lon, delivery_lat, delivery_lon):
    """
    Fetch Distance_km and Congestion Level using GraphHopper API.
    """
    try:
        response = requests.get(
            BASE_URL,
            params={
                "point": [f"{hub_lat},{hub_lon}", f"{delivery_lat},{delivery_lon}"],
                "profile": "car",
                "locale": "en",
                "calc_points": True,
                "key": GRAPH_HOPPER_API_KEY
            }
        )
        if response.status_code == 200:
            result = response.json()
            distance = result["paths"][0]["distance"] / 1000  # Convert to km
            congestion_level = "Medium"  # Example logic; replace with actual mapping
            return distance, congestion_level
        else:
            raise Exception(f"GraphHopper API error: {response.status_code} {response.text}")
    except Exception as e:
        raise Exception(f"Error fetching GraphHopper data: {e}")

def predict_delivery_time(input_data):
    """
    Predict delivery time using the logistic regression model and additional features.
    """
    # Fetch GraphHopper features
    distance_km, congestion_level = fetch_graphhopper_features(
        input_data["hub_latitude"],
        input_data["hub_longitude"],
        input_data["delivery_latitude"],
        input_data["delivery_longitude"]
    )

    # Combine user input with fetched features
    features = [
        input_data["order_weight"],
        input_data["order_priority_Low"],
        input_data["order_priority_Medium"],
        input_data["traffic_impact"],
        input_data["weather_impact"],
        distance_km
    ]
    # Predict delivery time
    prediction = logistic_model.predict([features])
    return prediction[0]