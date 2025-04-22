"""
Codestorm Assistant - Aplicación principal simplificada
Este archivo crea un blueprint de Flask con las rutas básicas para el asistente.
"""
import os
import re
import json
import logging
import subprocess
from pathlib import Path
from flask import Blueprint, render_template, jsonify, request, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Crear el blueprint de Flask
app = Blueprint('codestorm', __name__,
               static_folder="static",
               template_folder="templates")

# Funciones auxiliares para el manejo de archivos y directorios
def get_user_workspace(user_id='default'):
    """Obtiene o crea un espacio de trabajo para el usuario."""
    workspace_dir = os.path.join(os.getcwd(), 'user_workspaces', user_id)
    os.makedirs(workspace_dir, exist_ok=True)
    return workspace_dir

def list_files(directory='.', user_id='default'):
    """Lista archivos y directorios en una ruta especificada."""
    workspace = get_user_workspace(user_id)
    target_dir = os.path.join(workspace, directory)
    
    if not os.path.exists(target_dir):
        return []
    
    try:
        entries = []
        for entry in os.listdir(target_dir):
            entry_path = os.path.join(target_dir, entry)
            entry_type = 'directory' if os.path.isdir(entry_path) else 'file'
            
            if entry_type == 'file':
                file_size = os.path.getsize(entry_path)
                file_extension = os.path.splitext(entry)[1].lower()[1:] if '.' in entry else ''
                
                entries.append({
                    'name': entry,
                    'type': entry_type,
                    'path': os.path.join(directory, entry) if directory != '.' else entry,
                    'size': file_size,
                    'extension': file_extension
                })
            else:
                entries.append({
                    'name': entry,
                    'type': entry_type,
                    'path': os.path.join(directory, entry) if directory != '.' else entry
                })
        
        return entries
    except Exception as e:
        logger.error(f"Error al listar archivos: {str(e)}")
        return []

# Rutas principales
@app.route('/')
def index():
    """Ruta principal que sirve la página index.html."""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Ruta al panel de control."""
    return render_template('dashboard.html')

@app.route('/chat')
def chat():
    """Ruta a la página de chat."""
    agent_id = request.args.get('agent', 'general')
    return render_template('chat.html', agent_id=agent_id)

# APIs para manejo de archivos
@app.route('/api/files', methods=['GET'])
def api_list_files():
    """API para listar archivos del workspace."""
    try:
        user_id = request.args.get('user_id', 'default')
        directory = request.args.get('directory', '.')
        
        files = list_files(directory, user_id)
        
        return jsonify({
            'success': True,
            'files': files,
            'directory': directory
        })
    except Exception as e:
        logger.error(f"Error al listar archivos: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/files/read', methods=['GET'])
def api_read_file():
    """API para leer el contenido de un archivo."""
    try:
        user_id = request.args.get('user_id', 'default')
        file_path = request.args.get('file_path')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'Se requiere ruta de archivo'
            }), 400
        
        workspace = get_user_workspace(user_id)
        full_path = os.path.join(workspace, file_path)
        
        # Verificar path traversal
        if not os.path.normpath(full_path).startswith(os.path.normpath(workspace)):
            return jsonify({
                'success': False,
                'error': 'Ruta de archivo inválida'
            }), 400
        
        # Verificar que el archivo existe
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            return jsonify({
                'success': False,
                'error': 'El archivo no existe'
            }), 404
        
        # Leer el archivo
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'file_path': file_path,
            'content': content
        })
    except Exception as e:
        logger.error(f"Error al leer archivo: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/files/create', methods=['POST'])
def api_create_file():
    """API para crear o actualizar un archivo."""
    try:
        data = request.json
        user_id = data.get('user_id', 'default')
        file_path = data.get('file_path')
        content = data.get('content', '')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'Se requiere ruta de archivo'
            }), 400
        
        workspace = get_user_workspace(user_id)
        full_path = os.path.join(workspace, file_path)
        
        # Verificar path traversal
        if not os.path.normpath(full_path).startswith(os.path.normpath(workspace)):
            return jsonify({
                'success': False,
                'error': 'Ruta de archivo inválida'
            }), 400
        
        # Crear directorios si no existen
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Escribir contenido al archivo
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            'success': True,
            'file_path': file_path
        })
    except Exception as e:
        logger.error(f"Error al crear archivo: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/files/delete', methods=['DELETE'])
def api_delete_file():
    """API para eliminar un archivo o directorio."""
    try:
        data = request.json
        user_id = data.get('user_id', 'default')
        file_path = data.get('file_path')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'Se requiere ruta de archivo'
            }), 400
        
        workspace = get_user_workspace(user_id)
        full_path = os.path.join(workspace, file_path)
        
        # Verificar path traversal
        if not os.path.normpath(full_path).startswith(os.path.normpath(workspace)):
            return jsonify({
                'success': False,
                'error': 'Ruta de archivo inválida'
            }), 400
        
        # Verificar que el archivo existe
        if not os.path.exists(full_path):
            return jsonify({
                'success': False,
                'error': 'El archivo o directorio no existe'
            }), 404
        
        # Eliminar
        if os.path.isdir(full_path):
            import shutil
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        
        return jsonify({
            'success': True,
            'file_path': file_path
        })
    except Exception as e:
        logger.error(f"Error al eliminar archivo: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API para ejecución de comandos
@app.route('/api/execute', methods=['POST'])
def api_execute_command():
    """API para ejecutar comandos directamente."""
    try:
        data = request.json
        user_id = data.get('user_id', 'default')
        command = data.get('command')
        
        if not command:
            return jsonify({
                'success': False,
                'error': 'Se requiere un comando'
            }), 400
        
        workspace = get_user_workspace(user_id)
        
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=workspace
        )
        
        stdout, stderr = process.communicate(timeout=30)
        status = process.returncode
        
        result = {
            'success': True,
            'command': command,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
            'status': status
        }
        
        return jsonify(result)
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Tiempo de ejecución agotado (30s)'
        }), 504
    except Exception as e:
        logger.error(f"Error al ejecutar comando: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# APIs para chat y generación de contenido
@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API para chat con agentes especializados."""
    try:
        data = request.json
        user_id = data.get('user_id', 'default')
        message = data.get('message')
        agent_id = data.get('agent_id', 'general')
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Se requiere un mensaje'
            }), 400
        
        # Respuesta simulada (en una implementación real, aquí se conectaría con el servicio de IA)
        agent_name = {
            'developer': "Desarrollador Experto",
            'architect': "Arquitecto de Software",
            'advanced': "Especialista Avanzado",
            'general': "Asistente General"
        }.get(agent_id, "Asistente General")
        
        response = f"Soy {agent_name}. He recibido tu mensaje: '{message}'. ¿En qué puedo ayudarte?"
        
        return jsonify({
            'success': True,
            'message': message,
            'response': response,
            'agent_id': agent_id
        })
    except Exception as e:
        logger.error(f"Error en el chat: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/process-instruction', methods=['POST'])
def api_process_instruction():
    """API para procesar instrucciones en lenguaje natural."""
    try:
        data = request.json
        user_id = data.get('user_id', 'default')
        instruction = data.get('instruction')
        
        if not instruction:
            return jsonify({
                'success': False,
                'error': 'Se requiere una instrucción'
            }), 400
        
        # Detectar si es un comando para ejecutar
        command_match = re.search(r'^ejecuta(?:r)?[:\s]+(.+)$', instruction, re.IGNORECASE)
        if command_match:
            command = command_match.group(1).strip()
            workspace = get_user_workspace(user_id)
            
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=workspace
            )
            
            stdout, stderr = process.communicate(timeout=30)
            status = process.returncode
            
            return jsonify({
                'success': True,
                'action': 'execute_command',
                'command': command,
                'stdout': stdout.decode('utf-8', errors='replace'),
                'stderr': stderr.decode('utf-8', errors='replace'),
                'status': status
            })
        
        # Detectar si es una instrucción para crear un archivo
        file_match = re.search(r'^crea(?:r)?[:\s]+([^\s]+)\s+(?:contenido|con)[:\s]+(.+)$', instruction, re.IGNORECASE | re.DOTALL)
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
                
            workspace = get_user_workspace(user_id)
            full_path = os.path.join(workspace, file_path)
            
            # Crear directorios si no existen
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return jsonify({
                'success': True,
                'action': 'create_file',
                'file_path': file_path,
                'content': content
            })
        
        # Respuesta genérica si no se reconoce la instrucción
        return jsonify({
            'success': True,
            'action': 'chat',
            'response': f"He recibido tu instrucción: '{instruction}'. ¿Podrías ser más específico sobre lo que necesitas?"
        })
    except Exception as e:
        logger.error(f"Error al procesar instrucción: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Servir archivos estáticos
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Servir archivos estáticos desde el directorio static."""
    return send_from_directory('static', filename)

# Ruta de salud para verificar el estado de la aplicación
@app.route('/health')
def health():
    """Verificar el estado de la aplicación."""
    return jsonify({
        'status': 'ok',
        'message': 'Aplicación funcionando correctamente'
    })

# Fin del blueprint de Codestorm