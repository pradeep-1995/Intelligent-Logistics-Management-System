from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.responses import HTMLResponse
from app.database import orders, routes, metrics
from app.vrp_solver import solve_vrp, create_distance_matrix
from app.models import Order, Route
#from app.prediction import predict_delivery_time
from pydantic import BaseModel
from joblib import load
import requests
import numpy as np
import folium
import os
import math
import openrouteservice
from openrouteservice import convert

app = FastAPI()
router = APIRouter()
# Constants
HUB_LATITUDE = 19.078810
HUB_LONGITUDE = 73.004064
HUB_COORDINATES = [HUB_LONGITUDE, HUB_LATITUDE]
DELIVERY_LOCATIONS = [
    [72.988493, 19.201999],  # Delivery Point 1 (longitude, latitude)
    [73.883572, 18.702718],  # Delivery Point 2
]

GRAPH_HOPPER_API_KEY = "3812daea-815d-4f8c-bb9f-25888711467e"
# ORS API key and client
ORS_API_KEY = "5b3ce3597851110001cf6248b249d3ae95bc40bb877f4bc41b497fd3"
client = openrouteservice.Client(key=ORS_API_KEY)



@app.post("/submit_order/")
def submit_order(order: Order):
    try:
        # Add the order to the database
        orders.clear()
        orders.append(order.dict())
        return {"message": "Order submitted successfully!", "order": order.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


'''
@router.get("/get_routes/")
def get_routes():
    """
    Fetch and generate delivery routes using ORS Optimization and Directions APIs.
    """
    try:
        # Payload for Optimization API
        payload = {
            "jobs": [
                {"id": 1, "location": [72.988493, 19.201999]},
                {"id": 2, "location": [73.883572, 18.702718]}
            ],
            "vehicles": [
                {
                    "id": 1,
                    "profile": "driving-car",
                    "start": [HUB_LONGITUDE, HUB_LATITUDE],
                    "end": [HUB_LONGITUDE, HUB_LATITUDE]
                }
            ]
        }

        # Call Optimization API
        optimization_response = client.request("/optimization", post_json=payload)

        # Check if routes exist in the response
        if "routes" not in optimization_response:
            raise HTTPException(status_code=500, detail="Routes missing in ORS response")

        routes = optimization_response["routes"]
        route_maps = []

        # Process each route
        for route in routes:
            steps = route["steps"]

            # Extract coordinates for directions
            coordinates = [step["location"] for step in steps if "location" in step]

            # Fetch directions for the full route geometry
            directions_response = client.directions(
                coordinates=coordinates,
                profile="driving-car",
                format="geojson"
            )
            geometry = directions_response["routes"][0]["geometry"]["coordinates"]

            # Create a folium map
            m = folium.Map(location=[HUB_LATITUDE, HUB_LONGITUDE], zoom_start=10)

            # Add the route geometry as a polyline
            folium.PolyLine(
                [(coord[1], coord[0]) for coord in geometry],
                color="blue", weight=2.5
            ).add_to(m)

            # Add markers for each step
            for idx, coord in enumerate(coordinates):
                folium.Marker(
                    location=[coord[1], coord[0]],
                    popup=f"Step {idx + 1}: {steps[idx]['type']}",
                    icon=folium.Icon(color="red" if idx > 0 else "green")
                ).add_to(m)

            # Save map to HTML file
            map_file = f"route_vehicle_{route['vehicle']}.html"
            m.save(map_file)
            route_maps.append(map_file)

        return {"routes": route_maps}

    except openrouteservice.exceptions.ApiError as e:
        raise HTTPException(status_code=500, detail=f"ORS API Error: {e}")
    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"Missing key in ORS response: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
'''

@app.get("/get_metrics/")
def get_metrics():
    return metrics

'''
@app.post("/predict_delivery_time/")
def predict_delivery(order: dict):
    try:
        prediction = predict_delivery_time(order)
        return {"delivery_time_prediction": prediction}
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing feature: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''    
# Load the trained logistic regression model
with open("model\Logistic_model.pkl", "rb") as f:
    logistic_model = load(f)

# GraphHopper API details
GRAPH_HOPPER_API_KEY = "3812daea-815d-4f8c-bb9f-25888711467e"
BASE_URL = "https://graphhopper.com/api/1/route"

# Input model for prediction
class DeliveryPredictionRequest(BaseModel):
    order_weight: float
    order_priority_Low: int
    order_priority_Medium: int
    traffic_impact: float
    weather_impact: float
    delivery_latitude: float
    delivery_longitude: float

@app.post("/predict_delivery_time/")
def predict_delivery_time(request: DeliveryPredictionRequest):
    # Fetch travel details using GraphHopper API
    try:
        response = requests.get(
            BASE_URL,
            params={
                "point": [f"{HUB_LATITUDE},{HUB_LONGITUDE}",
                          f"{request.delivery_latitude},{request.delivery_longitude}"],
                "profile": "car",
                "locale": "en",
                "calc_points": True,
                "key": GRAPH_HOPPER_API_KEY,
            }
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch data from GraphHopper API")
        
        travel_data = response.json()
        distance = travel_data["paths"][0]["distance"]  # Distance in meters
        travel_time = travel_data["paths"][0]["time"]   # Time in milliseconds

        # Convert distance to kilometers
        distance_km = distance / 1000

        # Determine congestion level based on travel time and distance
        avg_speed_kmh = distance_km / (travel_time / (1000 * 60 * 60))
        if avg_speed_kmh < 30:
            congestion_level = 3  # High
        elif avg_speed_kmh < 60:
            congestion_level = 2  # Medium
        else:
            congestion_level = 1  # Low

        # Prepare features for prediction
        features = np.array([[
            request.order_weight,
            request.order_priority_Low,
            request.order_priority_Medium,
            request.traffic_impact,
            request.weather_impact,
            distance_km,
            congestion_level
        ]])

        try:
            # Predict delivery time
            predicted_delivery_time = logistic_model.predict(features)

            return {
                "order_id": int(np.random.randint(1000, 9999)),
                "distance_km": distance_km,
                "congestion_level": ["High", "Medium", "Low"][congestion_level - 1],
                "travel_time_minute": travel_time / (1000 * 60 * 60),
                "predicted_delivery_time": predicted_delivery_time[0]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data from GraphHopper API: {str(e)}")



@app.get("/get_orders/")
def get_orders():
    return orders