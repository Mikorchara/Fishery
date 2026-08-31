import requests

url = "http://127.0.0.1:5000/update_sensor"
headers = {"Authorization": "Bearer fishery2026"}
data = {
    "temp": "10.0",
    "ph": "7.5",
    "oxygen": "6.2"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
  
   