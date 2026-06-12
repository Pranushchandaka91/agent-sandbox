WEATHER_DATA = {
    "hyderabad": {"city": "Hyderabad", "temperature": "34°C", "condition": "Partly Cloudy", "humidity": "62%"},
    "mumbai":    {"city": "Mumbai",    "temperature": "31°C", "condition": "Humid",         "humidity": "78%"},
    "delhi":     {"city": "Delhi",     "temperature": "38°C", "condition": "Sunny",         "humidity": "45%"},
    "bangalore": {"city": "Bangalore", "temperature": "26°C", "condition": "Pleasant",      "humidity": "55%"},
}


def get_weather(city: str) -> dict:
    data = WEATHER_DATA.get(city.strip().lower())
    if data:
        return data
    return {"city": city, "temperature": "N/A", "condition": "Data unavailable", "humidity": "N/A"}
