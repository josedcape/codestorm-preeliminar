import requests
import json
import os

BASE_URL = "http://0.0.0.0:5000"

def test_execute_command():
    """Prueba la funcionalidad de ejecución de comandos en la API principal"""
    
    payload = {
        "command": "ls -la"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/execute_command",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print("\n=== Test de ejecución de comandos ===")
    print(f"Código de respuesta: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        return response.status_code == 200
    except:
        print("Respuesta no es JSON:", response.text[:200])
        return False

def test_create_file():
    """Prueba la funcionalidad de creación de archivos en la API principal"""
    
    # Crear un archivo HTML de prueba
    payload = {
        "file_path": "test_api_main.html",
        "content": """<!DOCTYPE html>
<html>
<head>
    <title>Prueba de API principal</title>
    <meta charset="UTF-8">
</head>
<body>
    <h1>Prueba exitosa de API</h1>
    <p>Este archivo fue creado desde la API principal del sistema</p>
    <ul>
        <li>Fecha: 21 de abril de 2025</li>
        <li>Formato: HTML</li>
    </ul>
</body>
</html>"""
    }
    
    response = requests.post(
        f"{BASE_URL}/api/create_file",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print("\n=== Test de creación de archivos ===")
    print(f"Código de respuesta: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        return response.status_code == 200
    except:
        print("Respuesta no es JSON:", response.text[:200])
        return False

def test_list_files():
    """Prueba la funcionalidad de listar archivos en la API principal"""
    
    response = requests.get(f"{BASE_URL}/api/list_files")
    
    print("\n=== Test de listar archivos ===")
    print(f"Código de respuesta: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        return response.status_code == 200
    except:
        print("Respuesta no es JSON:", response.text[:200])
        return False

if __name__ == "__main__":
    # Ejecutar las pruebas
    results = []
    results.append(("Ejecución de comandos", test_execute_command()))
    results.append(("Creación de archivos", test_create_file()))
    results.append(("Listado de archivos", test_list_files()))
    
    # Mostrar resumen
    print("\n=== Resumen de pruebas ===")
    all_passed = True
    for name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status} - {name}")
        if not result:
            all_passed = False
            
    # Salir con código apropiado
    exit(0 if all_passed else 1)