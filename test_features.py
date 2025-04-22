import requests
import json
import time

BASE_URL = "http://0.0.0.0:5000"

def test_command_execution():
    """Prueba la funcionalidad de ejecución de comandos directamente"""
    
    payload = {
        "message": "ejecuta comando: ls -la",
        "agent_id": "developer",
        "model": "openai"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print("\n=== Test de ejecución de comandos ===")
    print(f"Código de respuesta: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print("Respuesta no es JSON:", response.text[:200])  # Mostrar los primeros 200 caracteres

def test_file_generation():
    """Prueba la funcionalidad de generación de archivos con agentes especializados"""
    
    payload = {
        "message": "crea una página HTML con un formulario de contacto simple",
        "agent_id": "developer",
        "model": "openai"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print("\n=== Test de generación de archivos ===")
    print(f"Código de respuesta: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print("Respuesta no es JSON:", response.text[:200])  # Mostrar los primeros 200 caracteres

if __name__ == "__main__":
    # Esperar a que el servidor esté completamente iniciado
    time.sleep(2)
    
    # Ejecutar pruebas
    test_command_execution()
    time.sleep(2)
    test_file_generation()