"""
Asistente Codestorm - Versión completa con múltiples agentes y modelos.
Este script proporciona una interfaz de línea de comandos para interactuar
con los diferentes agentes de Codestorm.
"""
import os
import re
import sys
import json
import logging
import argparse
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Importar módulos de agentes
try:
    from agents_utils import (
        get_agent_name,
        get_agent_system_prompt,
        create_file_with_agent,
        generate_response,
        analyze_code,
        process_natural_language_command
    )
except ImportError:
    logger.error("No se pudo importar el módulo agents_utils. Asegúrate de que existe.")
    sys.exit(1)

def get_workspace_path(workspace_id='default'):
    """
    Obtiene la ruta del workspace del usuario.
    
    Args:
        workspace_id: ID del workspace (por defecto 'default')
        
    Returns:
        str: Ruta absoluta al workspace
    """
    workspace_dir = os.path.join(os.getcwd(), 'user_workspaces', workspace_id)
    os.makedirs(workspace_dir, exist_ok=True)
    return workspace_dir

def list_files(directory='.'):
    """
    Lista archivos y directorios en una ruta especificada.
    
    Args:
        directory: Ruta relativa al workspace del usuario
        
    Returns:
        list: Lista de archivos y directorios
    """
    workspace = get_workspace_path()
    target_dir = os.path.join(workspace, directory)
    
    if not os.path.exists(target_dir):
        logger.error(f"La ruta {directory} no existe en el workspace")
        return []
    
    try:
        entries = []
        for entry in os.listdir(target_dir):
            entry_path = os.path.join(target_dir, entry)
            entry_type = 'directory' if os.path.isdir(entry_path) else 'file'
            entries.append({
                'name': entry,
                'type': entry_type,
                'path': os.path.join(directory, entry) if directory != '.' else entry
            })
        
        return entries
    except Exception as e:
        logger.error(f"Error al listar archivos: {str(e)}")
        return []

def read_file(file_path):
    """
    Lee el contenido de un archivo.
    
    Args:
        file_path: Ruta relativa al workspace del usuario
        
    Returns:
        str: Contenido del archivo o mensaje de error
    """
    workspace = get_workspace_path()
    full_path = os.path.join(workspace, file_path)
    
    if not os.path.exists(full_path):
        return f"Error: El archivo {file_path} no existe"
    
    if not os.path.isfile(full_path):
        return f"Error: {file_path} no es un archivo"
    
    try:
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error al leer archivo {file_path}: {str(e)}")
        return f"Error al leer archivo: {str(e)}"

def create_file(file_path, content):
    """
    Crea un archivo con el contenido especificado.
    
    Args:
        file_path: Ruta relativa al workspace del usuario
        content: Contenido del archivo
        
    Returns:
        str: Mensaje de éxito o error
    """
    workspace = get_workspace_path()
    full_path = os.path.join(workspace, file_path)
    
    try:
        # Crear directorios intermedios si es necesario
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Archivo creado correctamente: {file_path}"
    except Exception as e:
        logger.error(f"Error al crear archivo {file_path}: {str(e)}")
        return f"Error al crear archivo: {str(e)}"

def execute_command(command):
    """
    Ejecuta un comando en el terminal.
    
    Args:
        command: Comando a ejecutar
        
    Returns:
        dict: Resultado con stdout, stderr y estado
    """
    try:
        import subprocess
        workspace = get_workspace_path()
        
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=workspace
        )
        
        stdout, stderr = process.communicate(timeout=30)
        status = process.returncode
        
        return {
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
            'status': status
        }
    except subprocess.TimeoutExpired:
        logger.error("Tiempo de espera agotado para el comando")
        return {
            'stdout': '',
            'stderr': 'Tiempo de espera agotado (30s)',
            'status': -1
        }
    except Exception as e:
        logger.error(f"Error al ejecutar comando: {str(e)}")
        return {
            'stdout': '',
            'stderr': str(e),
            'status': -1
        }

def generate_file(description, file_type, filename, agent_id):
    """
    Genera un archivo complejo con un agente especializado.
    
    Args:
        description: Descripción del archivo a generar
        file_type: Tipo de archivo (html, css, js, py, etc.)
        filename: Nombre del archivo (opcional)
        agent_id: ID del agente especializado (developer, architect, advanced, general)
        
    Returns:
        dict: Resultado con éxito/error y detalles
    """
    workspace = get_workspace_path()
    
    # Si no se proporciona filename, generarlo a partir de la descripción
    if not filename:
        # Extraer palabras clave de la descripción
        words = re.sub(r'[^\w\s]', '', description.lower()).split()
        # Usar las primeras 3 palabras para el nombre
        filename = '_'.join(words[:3])[:30]
        # Añadir extensión
        filename += f'.{file_type}'
    
    # Asegurar que el archivo tenga la extensión correcta
    if not filename.endswith(f'.{file_type}'):
        filename += f'.{file_type}'
    
    result = create_file_with_agent(
        description=description,
        file_type=file_type,
        filename=filename,
        agent_id=agent_id,
        workspace_path=workspace,
        model="openai"  # Por defecto usar OpenAI
    )
    
    return result

def chat_with_agent(message, agent_id="general", context=None):
    """
    Interactúa con un agente especializado en modo chat.
    
    Args:
        message: Mensaje del usuario
        agent_id: ID del agente especializado
        context: Contexto previo de la conversación (opcional)
        
    Returns:
        dict: Resultado con la respuesta del agente
    """
    result = generate_response(
        user_message=message,
        agent_id=agent_id,
        context=context,
        model="openai"  # Por defecto usar OpenAI
    )
    
    return result

def process_instruction(text):
    """
    Procesa una instrucción en lenguaje natural y realiza la acción correspondiente.
    
    Args:
        text: Texto de la instrucción
        
    Returns:
        dict: Resultado de la acción realizada
    """
    workspace = get_workspace_path()
    
    # Verificar primero patrones comunes mediante regex para mayor eficiencia
    
    # Patrón para ejecutar comando
    command_match = re.search(r'^ejecuta(?:r)?[:\s]+(.+)$', text, re.IGNORECASE)
    if command_match:
        command = command_match.group(1).strip()
        result = execute_command(command)
        
        # Formatear resultado para mostrar
        output = f"Ejecutando: {command}\n\n"
        
        if result['stdout']:
            output += f"--- SALIDA ---\n{result['stdout']}\n\n"
            
        if result['stderr']:
            output += f"--- ERRORES ---\n{result['stderr']}\n\n"
            
        output += f"Estado: {result['status']}"
        
        return {
            'success': True,
            'action': 'execute_command',
            'result': output
        }
    
    # Patrón para crear archivo
    file_match = re.search(r'^crea(?:r)?[:\s]+([^\s]+)\s+(?:contenido|con)[:\s]+(.+)$', text, re.IGNORECASE | re.DOTALL)
    if file_match:
        file_path = file_match.group(1).strip()
        content = file_match.group(2).strip()
        
        # Limpiar comillas o triple comillas si están presentes
        if content.startswith('"""') and content.endswith('"""'):
            content = content[3:-3]
        elif content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        elif content.startswith("'") and content.endswith("'"):
            content = content[1:-1]
            
        result = create_file(file_path, content)
        
        return {
            'success': True,
            'action': 'create_file',
            'result': result
        }
    
    # Patrón para listar archivos
    list_match = re.search(r'^(?:lista|listar|ver|muestra)(?:r)?(?:\s+(?:los|las))?\s+(?:archivos|directorios|carpetas)(?:\s+(?:en|de))?\s+(.+)?$', text, re.IGNORECASE)
    if list_match:
        directory = list_match.group(1).strip() if list_match.group(1) else '.'
        files = list_files(directory)
        
        output = f"Contenido de {directory}:\n\n"
        
        if not files:
            output += "No hay archivos o directorios."
        else:
            for f in files:
                icon = "📁 " if f['type'] == 'directory' else "📄 "
                output += f"{icon} {f['name']}\n"
        
        return {
            'success': True,
            'action': 'list_files',
            'result': output
        }
    
    # Patrón para leer archivo
    read_match = re.search(r'^(?:lee|leer|muestra|mostrar|cat|ver)(?:r)?\s+(?:el\s+archivo|archivo|contenido\s+de)?\s+(.+)$', text, re.IGNORECASE)
    if read_match:
        file_path = read_match.group(1).strip()
        content = read_file(file_path)
        
        output = f"Contenido de {file_path}:\n\n{content}"
        
        return {
            'success': True,
            'action': 'read_file',
            'result': output
        }
    
    # Patrón para generar archivo
    generate_match = re.search(r'^(?:genera|generar|crea|crear)\s+(?:un|una)?\s+archivo\s+(?:de)?\s+([a-zA-Z0-9]+)(?:\s+(?:llamado|con\s+nombre))?\s+([a-zA-Z0-9._-]+)?\s+(?:que|con|para)?\s+(.+)$', text, re.IGNORECASE)
    if generate_match:
        file_type = generate_match.group(1).lower()
        filename = generate_match.group(2) if generate_match.group(2) else ""
        description = generate_match.group(3).strip() if generate_match.group(3) else text
        
        # Mapear tipos comunes
        type_mapping = {
            'python': 'py',
            'javascript': 'js',
            'html': 'html',
            'css': 'css',
            'texto': 'txt',
            'markdown': 'md',
            'json': 'json'
        }
        
        file_ext = type_mapping.get(file_type, file_type)
        
        result = generate_file(description, file_ext, filename, "developer")
        
        if result['success']:
            output = f"Archivo generado: {result['file_path']}\n\nVista previa del contenido:\n\n"
            preview = result['content'][:500] + "..." if len(result['content']) > 500 else result['content']
            output += preview
        else:
            output = f"Error al generar archivo: {result.get('error', 'Error desconocido')}"
        
        return {
            'success': True,
            'action': 'generate_file',
            'result': output
        }
    
    # Si no coincide con ningún patrón específico, usar procesamiento avanzado
    result = process_natural_language_command(text, workspace)
    
    if result['success']:
        action = result.get('action', 'unknown')
        
        if action == 'create_file':
            output = f"Archivo creado: {result['file_path']}\n\nVista previa del contenido:\n\n"
            preview = result['content'][:500] + "..." if len(result['content']) > 500 else result['content']
            output += preview
        elif action == 'execute_command':
            output = f"Ejecutando: {result['command']}\n\n"
            
            if result['stdout']:
                output += f"--- SALIDA ---\n{result['stdout']}\n\n"
                
            if result['stderr']:
                output += f"--- ERRORES ---\n{result['stderr']}\n\n"
                
            output += f"Estado: {result['status']}"
        elif action == 'answer_question':
            output = result['answer']
        else:
            output = "Acción procesada, pero el tipo de acción no está especificado."
            
        return {
            'success': True,
            'action': action,
            'result': output
        }
    else:
        # Si todo lo demás falla, tratar como una pregunta para el agente general
        chat_result = chat_with_agent(text)
        
        if chat_result['success']:
            return {
                'success': True,
                'action': 'chat',
                'result': chat_result['response']
            }
        else:
            return {
                'success': False,
                'error': f"No pude procesar esta instrucción: {chat_result.get('error', 'Error desconocido')}"
            }

def interactive_mode():
    """
    Inicia el modo interactivo del asistente.
    """
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║             CODESTORM ASSISTANT - MODO INTERACTIVO        ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    print("Escribe 'salir' o 'exit' para terminar la sesión.\n")
    
    # Historial de conversación para contexto
    context = []
    current_agent = "general"
    
    while True:
        try:
            # Mostrar prompt según el agente actual
            agent_name = get_agent_name(current_agent)
            user_input = input(f"\n[{agent_name}] 🤔 > ").strip()
            
            # Verificar si el usuario quiere salir
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("\n¡Hasta luego! 👋\n")
                break
            
            # Verificar si el usuario quiere cambiar de agente
            agent_change = re.search(r'^(?:usar|cambiar\s+a|seleccionar)\s+(?:el\s+)?agente\s+([a-zA-Z]+)$', user_input, re.IGNORECASE)
            if agent_change:
                agent_id = agent_change.group(1).lower()
                if agent_id in ['developer', 'architect', 'advanced', 'general']:
                    current_agent = agent_id
                    print(f"\n✅ Cambiado al agente: {get_agent_name(current_agent)}")
                    continue
                else:
                    print(f"\n❌ Agente no reconocido. Agentes disponibles: developer, architect, advanced, general")
                    continue
            
            # Procesar la instrucción
            print("\nProcesando... ⚙️")
            result = process_instruction(user_input)
            
            # Actualizar contexto de conversación
            context.append({"role": "user", "content": user_input})
            
            if result['success']:
                print(f"\n{result['result']}")
                # Guardar la respuesta en el contexto
                context.append({"role": "assistant", "content": result['result']})
                
                # Limitar el tamaño del contexto para evitar tokens excesivos
                if len(context) > 10:
                    context = context[-10:]
            else:
                print(f"\n❌ {result.get('error', 'Ocurrió un error desconocido.')}")
        
        except KeyboardInterrupt:
            print("\n\n¡Hasta luego! 👋\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Asistente Codestorm - CLI')
    
    # Subparsers para diferentes comandos
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')
    
    # Comando: interact (modo interactivo)
    interact_parser = subparsers.add_parser('interact', help='Iniciar modo interactivo')
    
    # Comando: exec (ejecutar comando)
    exec_parser = subparsers.add_parser('exec', help='Ejecutar comando')
    exec_parser.add_argument('cmd', help='Comando a ejecutar')
    
    # Comando: create (crear archivo)
    create_parser = subparsers.add_parser('create', help='Crear archivo')
    create_parser.add_argument('file', help='Ruta del archivo')
    create_parser.add_argument('--content', '-c', help='Contenido del archivo')
    
    # Comando: generate (generar archivo con IA)
    generate_parser = subparsers.add_parser('generate', help='Generar archivo con IA')
    generate_parser.add_argument('description', help='Descripción del archivo a generar')
    generate_parser.add_argument('--type', '-t', default='py', help='Tipo de archivo (py, js, html, etc.)')
    generate_parser.add_argument('--filename', '-f', help='Nombre del archivo')
    generate_parser.add_argument('--agent', '-a', default='developer', help='Agente a utilizar (developer, architect, advanced, general)')
    
    # Comando: list (listar archivos)
    list_parser = subparsers.add_parser('list', help='Listar archivos')
    list_parser.add_argument('directory', nargs='?', default='.', help='Directorio a listar')
    
    # Comando: read (leer archivo)
    read_parser = subparsers.add_parser('read', help='Leer archivo')
    read_parser.add_argument('file', help='Archivo a leer')
    
    # Comando: process (procesar instrucción)
    process_parser = subparsers.add_parser('process', help='Procesar instrucción en lenguaje natural')
    process_parser.add_argument('instruction', help='Instrucción a procesar')
    
    args = parser.parse_args()
    
    # Ejecutar el comando correspondiente
    if args.command == 'interact' or not args.command:
        interactive_mode()
    elif args.command == 'exec':
        result = execute_command(args.cmd)
        print(f"SALIDA:\n{result['stdout']}")
        if result['stderr']:
            print(f"ERRORES:\n{result['stderr']}")
        print(f"Estado: {result['status']}")
    elif args.command == 'create':
        if not args.content:
            # Si no se proporciona contenido, leerlo de stdin
            print("Ingresa el contenido del archivo (Ctrl+D para finalizar):")
            content = sys.stdin.read()
        else:
            content = args.content
        
        result = create_file(args.file, content)
        print(result)
    elif args.command == 'generate':
        result = generate_file(args.description, args.type, args.filename, args.agent)
        if result['success']:
            print(f"Archivo generado: {result['file_path']}")
            print("\nVista previa del contenido:")
            preview = result['content'][:500] + "..." if len(result['content']) > 500 else result['content']
            print(preview)
        else:
            print(f"Error: {result.get('error', 'Error desconocido')}")
    elif args.command == 'list':
        files = list_files(args.directory)
        print(f"Contenido de {args.directory}:")
        if not files:
            print("  No hay archivos o directorios.")
        for f in files:
            icon = "📁" if f['type'] == 'directory' else "📄"
            print(f"  {icon} {f['name']}")
    elif args.command == 'read':
        content = read_file(args.file)
        print(content)
    elif args.command == 'process':
        result = process_instruction(args.instruction)
        if result['success']:
            print(result['result'])
        else:
            print(f"Error: {result.get('error', 'Error desconocido')}")

if __name__ == "__main__":
    main()