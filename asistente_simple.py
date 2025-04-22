import re
import json
import requests
import os
import argparse
from pathlib import Path

BASE_URL = "http://0.0.0.0:5000"
USER_WORKSPACE = Path("user_workspaces/default")

def ejecutar_comando(comando):
    """Ejecuta un comando a través de la API."""
    print(f"Ejecutando comando: {comando}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/execute_command",
            json={"command": comando},
            headers={"Content-Type": "application/json"},
            timeout=5  # Timeout reducido para evitar bloqueos
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'comando': comando,
                'salida': result.get('stdout', ''),
                'errores': result.get('stderr', ''),
                'estado': result.get('status', -1)
            }
        else:
            # Si la API falla pero podemos ejecutar el comando localmente
            import subprocess
            if not USER_WORKSPACE.exists():
                USER_WORKSPACE.mkdir(parents=True, exist_ok=True)
                
            process = subprocess.Popen(
                comando,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(USER_WORKSPACE)
            )
            
            stdout, stderr = process.communicate(timeout=30)
            status = process.returncode
            
            return {
                'success': status == 0,
                'comando': comando,
                'salida': stdout.decode('utf-8', errors='replace'),
                'errores': stderr.decode('utf-8', errors='replace'),
                'estado': status
            }
    except requests.exceptions.RequestException as e:
        # Ejecutar de manera local si la API falla
        import subprocess
        
        if not USER_WORKSPACE.exists():
            USER_WORKSPACE.mkdir(parents=True, exist_ok=True)
            
        process = subprocess.Popen(
            comando,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(USER_WORKSPACE)
        )
        
        stdout, stderr = process.communicate(timeout=30)
        status = process.returncode
        
        return {
            'success': status == 0,
            'comando': comando,
            'salida': stdout.decode('utf-8', errors='replace'),
            'errores': stderr.decode('utf-8', errors='replace'),
            'estado': status,
            'metodo': 'local'
        }
    except Exception as e:
        return {
            'success': False,
            'comando': comando,
            'error': str(e)
        }

def crear_archivo(ruta, contenido):
    """Crea un archivo con el contenido especificado."""
    print(f"Creando archivo: {ruta}")
    
    # Verificar si el contenido es demasiado grande
    contenido_large = len(contenido) > 10000
    temp_file = None
    
    if contenido_large:
        print("Contenido extenso detectado, usando archivo temporal...")
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(text=True)
        with os.fdopen(temp_fd, 'w') as tmp:
            tmp.write(contenido)
        temp_file = temp_path
    
    try:
        if not contenido_large:
            response = requests.post(
                f"{BASE_URL}/api/create_file",
                json={"file_path": ruta, "content": contenido},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'archivo': ruta,
                    'mensaje': f"Archivo {ruta} creado correctamente"
                }
        
        # Método local (ya sea porque la API falló o el contenido es muy grande)
        if not USER_WORKSPACE.exists():
            USER_WORKSPACE.mkdir(parents=True, exist_ok=True)
            
        target_file = (USER_WORKSPACE / ruta).resolve()
        
        # Verificar path traversal
        if not str(target_file).startswith(str(USER_WORKSPACE.resolve())):
            return {
                'success': False,
                'archivo': ruta,
                'error': 'Acceso denegado: No se puede acceder a archivos fuera del workspace'
            }
            
        # Crear directorios si no existen
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Escribir el archivo
        if contenido_large and temp_file:
            # Copiar desde archivo temporal
            import shutil
            shutil.copy2(temp_file, target_file)
        else:
            # Escribir directamente
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(contenido)
                
        return {
            'success': True,
            'archivo': ruta,
            'tamaño': target_file.stat().st_size,
            'mensaje': f"Archivo {ruta} creado correctamente (método local)"
        }
    except Exception as e:
        return {
            'success': False,
            'archivo': ruta,
            'error': str(e)
        }
    finally:
        # Limpiar archivo temporal si existe
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)

def leer_archivo(ruta):
    """Lee el contenido de un archivo."""
    print(f"Leyendo archivo: {ruta}")
    
    try:
        target_file = (USER_WORKSPACE / ruta).resolve()
        
        # Verificar path traversal
        if not str(target_file).startswith(str(USER_WORKSPACE.resolve())):
            return {
                'success': False,
                'archivo': ruta,
                'error': 'Acceso denegado: No se puede acceder a archivos fuera del workspace'
            }
            
        # Verificar que el archivo existe
        if not target_file.exists():
            return {
                'success': False,
                'archivo': ruta,
                'error': f'El archivo {ruta} no existe'
            }
            
        # Leer el archivo
        with open(target_file, 'r') as f:
            contenido = f.read()
            
        return {
            'success': True,
            'archivo': ruta,
            'contenido': contenido,
            'tamaño': target_file.stat().st_size
        }
    except Exception as e:
        return {
            'success': False,
            'archivo': ruta,
            'error': str(e)
        }

def listar_archivos(directorio='.'):
    """Lista los archivos en un directorio."""
    print(f"Listando archivos en: {directorio}")
    
    try:
        target_dir = (USER_WORKSPACE / directorio).resolve()
        
        # Verificar path traversal
        if not str(target_dir).startswith(str(USER_WORKSPACE.resolve())):
            return {
                'success': False,
                'directorio': directorio,
                'error': 'Acceso denegado: No se puede acceder a directorios fuera del workspace'
            }
            
        # Verificar que el directorio existe
        if not target_dir.exists() or not target_dir.is_dir():
            return {
                'success': False,
                'directorio': directorio,
                'error': f'El directorio {directorio} no existe'
            }
            
        # Listar archivos
        archivos = []
        directorios = []
        
        for item in target_dir.iterdir():
            if item.is_file():
                archivos.append({
                    'nombre': item.name,
                    'tamaño': item.stat().st_size,
                    'modificado': item.stat().st_mtime
                })
            elif item.is_dir():
                directorios.append({
                    'nombre': item.name,
                    'modificado': item.stat().st_mtime
                })
                
        return {
            'success': True,
            'directorio': directorio,
            'archivos': archivos,
            'directorios': directorios
        }
    except Exception as e:
        return {
            'success': False,
            'directorio': directorio,
            'error': str(e)
        }

def procesar_instruccion(texto):
    """Procesa una instrucción en lenguaje natural para ejecutar comandos o crear archivos."""
    
    # Patrones para detección de comandos
    comando_pattern = re.compile(r'(?:ejecuta|corre|run|ejecutar)[:\s]+(?:comando[:\s]+)?[\'"`]?([\w\s\.\-\$\{\}\/\\\|\&\>\<\;\:\*\?\[\]\(\)\=\+\,\_\!]+)[\'"`]?', re.IGNORECASE)
    comando_match = comando_pattern.search(texto)
    
    # Patrón para detección de creación de archivos
    archivo_pattern = re.compile(r'(?:crea|genera|crear|crear archivo)[:\s]+(?:archivo[:\s]+)?[\'"`]?([\w\s\.\-\/]+\.\w+)[\'"`]?', re.IGNORECASE)
    archivo_match = archivo_pattern.search(texto)
    
    # Patrón para leer archivos
    leer_pattern = re.compile(r'(?:lee|leer|mostrar|muestra|ver|cat)[:\s]+(?:archivo[:\s]+)?[\'"`]?([\w\s\.\-\/]+\.\w+)[\'"`]?', re.IGNORECASE)
    leer_match = leer_pattern.search(texto)
    
    # Patrón para listar archivos
    listar_pattern = re.compile(r'(?:lista|listar|ls|dir)[:\s]+(?:archivos|carpeta|directorio)[:\s]*(?:en[:\s]+)?[\'"`]?([\w\s\.\-\/]*)[\'"`]?', re.IGNORECASE)
    listar_match = listar_pattern.search(texto)
    
    # Patrón para extraer contenido
    contenido_pattern = re.compile(r'contenido[:\s]+[\'"`](.+?)[\'"`]|```(?:\w+)?\s*(.+?)```|<code>(.+?)</code>', re.IGNORECASE | re.DOTALL)
    contenido_match = contenido_pattern.search(texto)
    
    contenido = None
    if contenido_match:
        # Obtener el primer grupo no nulo
        for i in range(1, 4):  # Tenemos hasta 3 grupos de captura
            if contenido_match and contenido_match.group(i):
                contenido = contenido_match.group(i)
                break
    
    # Procesar según el tipo de instrucción detectada
    if comando_match:
        # Ejecutar comando
        comando = comando_match.group(1).strip()
        return ejecutar_comando(comando)
    elif archivo_match and contenido:
        # Crear archivo
        archivo = archivo_match.group(1).strip()
        return crear_archivo(archivo, contenido)
    elif leer_match:
        # Leer archivo
        archivo = leer_match.group(1).strip()
        return leer_archivo(archivo)
    elif listar_match:
        # Listar archivos
        directorio = listar_match.group(1).strip() if listar_match.group(1) else '.'
        return listar_archivos(directorio)
    else:
        # Detección más avanzada de intenciones
        if re.search(r'(?:mostrar|ver|listar|ls|dir|lista).*(?:archivos|carpetas|directorios)', texto, re.IGNORECASE):
            return listar_archivos('.')
        elif re.search(r'qué hay en', texto, re.IGNORECASE):
            return listar_archivos('.')
        elif re.search(r'contenido del directorio', texto, re.IGNORECASE):
            return listar_archivos('.')
        
        return {
            'success': False,
            'error': 'No se pudo determinar la acción a realizar. Por favor, sé más específico.'
        }

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description='Asistente de línea de comandos para Codestorm')
    parser.add_argument('instruccion', nargs='?', help='Instrucción a procesar')
    parser.add_argument('-f', '--file', help='Archivo con la instrucción')
    
    args = parser.parse_args()
    
    if args.file:
        # Leer instrucción desde un archivo
        try:
            with open(args.file, 'r') as f:
                instruccion = f.read()
        except Exception as e:
            print(f"Error leyendo archivo: {e}")
            return
    elif args.instruccion:
        # Usar instrucción de la línea de comandos
        instruccion = args.instruccion
    else:
        # Leer instrucción desde entrada estándar
        print("Introduce tu instrucción (Ctrl+D para finalizar):")
        instruccion = ""
        try:
            while True:
                line = input()
                instruccion += line + "\n"
        except EOFError:
            pass
    
    resultado = procesar_instruccion(instruccion)
    
    # Mostrar resultado
    if resultado.get('success'):
        print("\n✅ Operación exitosa")
        
        if 'comando' in resultado:
            print(f"\nComando: {resultado['comando']}")
            
            if resultado.get('salida'):
                print("\nSalida:")
                print(resultado['salida'])
                
            if resultado.get('errores'):
                print("\nErrores/Advertencias:")
                print(resultado['errores'])
                
            print(f"\nEstado de salida: {resultado.get('estado', 'N/A')}")
            
        elif 'archivo' in resultado and 'contenido' in resultado:
            # Mostrar contenido de archivo leído
            print(f"\nArchivo: {resultado['archivo']}")
            print(f"Tamaño: {resultado.get('tamaño', 0)} bytes")
            print("\nContenido:")
            print("=" * 50)
            print(resultado['contenido'])
            print("=" * 50)
            
        elif 'archivo' in resultado:
            # Mostrar información sobre archivo creado
            print(f"\nArchivo: {resultado['archivo']}")
            print(resultado.get('mensaje', ''))
            
            # Verificar si el archivo existe
            archivo_path = USER_WORKSPACE / resultado['archivo']
            if archivo_path.exists():
                print(f"Tamaño: {archivo_path.stat().st_size} bytes")
                
        elif 'directorio' in resultado and 'archivos' in resultado:
            # Mostrar contenido de directorio
            print(f"\nDirectorio: {resultado['directorio']}")
            
            if not resultado.get('directorios') and not resultado.get('archivos'):
                print("\nEl directorio está vacío.")
            else:
                if resultado.get('directorios'):
                    print("\nCarpetas:")
                    for dir_info in resultado['directorios']:
                        print(f"  📁 {dir_info['nombre']}")
                
                if resultado.get('archivos'):
                    print("\nArchivos:")
                    for file_info in resultado['archivos']:
                        size_str = f"{file_info['tamaño']} bytes"
                        if file_info['tamaño'] > 1024:
                            size_str = f"{file_info['tamaño'] / 1024:.1f} KB"
                        if file_info['tamaño'] > 1024 * 1024:
                            size_str = f"{file_info['tamaño'] / (1024 * 1024):.1f} MB"
                        print(f"  📄 {file_info['nombre']} ({size_str})")
    else:
        print("\n❌ Error en la operación")
        print(resultado.get('error', 'Error desconocido'))

if __name__ == "__main__":
    main()