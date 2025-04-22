import requests
import json
import subprocess
import time
import sys
from pathlib import Path

# Primero, iniciamos nuestra aplicación simple en segundo plano
def start_api_server():
    print("Iniciando servidor de API simplificada...")
    # Iniciar el servidor en un proceso separado
    process = subprocess.Popen(
        ["python", "api_simple.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Esperar un momento para que el servidor se inicie
    time.sleep(2)
    return process

def test_execute_command():
    """Prueba la funcionalidad de ejecución de comandos directamente"""
    print("\n=== Test de ejecución de comandos ===")
    
    payload = {
        "command": "ls -la"
    }
    
    response = requests.post(
        "http://0.0.0.0:5001/api/execute_command",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Código de respuesta: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        return response.status_code == 200
    except:
        print("Respuesta no es JSON:", response.text[:200])  # Mostrar los primeros 200 caracteres
        return False

def test_create_file():
    """Prueba la funcionalidad de creación de archivos"""
    print("\n=== Test de creación de archivos ===")
    
    payload = {
        "file_path": "test_file.html",
        "content": """<!DOCTYPE html>
<html>
<head>
    <title>Página de prueba</title>
</head>
<body>
    <h1>Esta es una página de prueba</h1>
    <p>Creada mediante API simplificada</p>
</body>
</html>"""
    }
    
    response = requests.post(
        "http://0.0.0.0:5001/api/create_file",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Código de respuesta: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        return response.status_code == 200
    except:
        print("Respuesta no es JSON:", response.text[:200])  # Mostrar los primeros 200 caracteres
        return False

def test_list_files():
    """Prueba la funcionalidad de listar archivos"""
    print("\n=== Test de listar archivos ===")
    
    response = requests.get("http://0.0.0.0:5001/api/list_files")
    
    print(f"Código de respuesta: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        return response.status_code == 200
    except:
        print("Respuesta no es JSON:", response.text[:200])  # Mostrar los primeros 200 caracteres
        return False

if __name__ == "__main__":
    # Iniciar el servidor 
    api_process = start_api_server()
    
    try:
        # Ejecutar pruebas
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
        sys.exit(0 if all_passed else 1)
    finally:
        # Detener el servidor
        print("Deteniendo servidor...")
        api_process.terminate()
        stdout, stderr = api_process.communicate()
        
        if stdout:
            print("Salida del servidor:")
            print(stdout.decode())
        
        if stderr:
            print("Errores del servidor:")
            print(stderr.decode())