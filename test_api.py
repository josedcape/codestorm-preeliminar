import requests
import json

# Prueba básica de la API de chat
url = "http://0.0.0.0:5000/api/chat"

payload = {
    "message": "ejecuta comando: ls -l",
    "agent_id": "developer",
    "model": "openai"
}

headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    print(f"Status code: {response.status_code}")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")