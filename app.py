# Flask application for Codestorm-Assistant
import os
import json
import logging
# Configurar logging con mayor detalle 
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
import subprocess
import shutil
import time
import re
import zipfile
import io
from pathlib import Path
from threading import Thread
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, send_file, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import openai
import anthropic
from anthropic import Anthropic
import eventlet
import requests
import google.generativeai as genai

# Force reload environment variables
load_dotenv(override=True)

# Get API keys with explicit path to .env
load_dotenv(dotenv_path=Path('.env'), override=True)

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Get and verify API keys
openai_api_key = os.getenv('OPENAI_API_KEY')
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
gemini_api_key = os.getenv('GEMINI_API_KEY')

# Log API key status (safely)
logging.info("=== API Keys Status ===")
logging.info(f"OpenAI API key: {'Configured' if openai_api_key else 'Missing'}")
logging.info(f"Anthropic API key: {'Configured' if anthropic_api_key else 'Missing'}")
logging.info(f"Gemini API key: {'Configured' if gemini_api_key else 'Missing'}")

# Importar utilidades para agentes con los prompts mejorados con emojis
from agents_utils import get_agent_system_prompt, get_agent_name, generate_content, explore_repository_files

# Importar rutas de diagnóstico
from diagnostic_routes import register_diagnostic_routes

# Comentamos el monkey patch para evitar conflictos con OpenAI y otras bibliotecas
# eventlet.monkey_patch(os=True, select=True, socket=True, thread=True, time=True)

# Load environment variables from .env file
load_dotenv(override=True)

# Logging ya está configurado con nivel DEBUG

# Configurar APIs de IA
try:
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if openai_api_key:
        # Solo mostrar los primeros caracteres por seguridad
        masked_key = openai_api_key[:5] + "..." + openai_api_key[-5:]
        logging.info(f"OpenAI API key configurada: {masked_key}")
except Exception as e:
    logging.error(f"Error al configurar OpenAI API: {str(e)}")

try:
    anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
    if anthropic_api_key:
        logging.info("Anthropic API key configured successfully.")
except Exception as e:
    logging.error(f"Error al configurar Anthropic API: {str(e)}")

try:
    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        logging.info("Gemini API key configured successfully.")
except Exception as e:
    logging.error(f"Error al configurar Gemini API: {str(e)}")

# Helper function to determine file type for syntax highlighting
def get_file_type(filename):
    extension = filename.split('.')[-1].lower() if '.' in filename else ''
    extension_map = {
        'py': 'python',
        'js': 'javascript',
        'html': 'html',
        'css': 'css',
        'json': 'json',
        'md': 'markdown',
        'txt': 'text',
        'sh': 'bash',
        'yml': 'yaml',
        'yaml': 'yaml',
    }
    return extension_map.get(extension, 'text')

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Registrar rutas de diagnóstico
register_diagnostic_routes(app)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Set session secret
app.secret_key = os.environ.get("SESSION_SECRET", os.urandom(24).hex())

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Import models and create tables
with app.app_context():
    import models
    db.create_all()

# Create user workspaces directory if it doesn't exist
WORKSPACE_ROOT = Path("./user_workspaces")
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

# Get API keys from environment - force reload from .env
load_dotenv(override=True)
openai_api_key = os.environ.get("OPENAI_API_KEY", "")
anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
gemini_api_key = os.environ.get("GEMINI_API_KEY", "")

logging.info("=== Inicializando clientes de IA ===")
logging.info(f"OpenAI API key: {'Configurada' if openai_api_key else 'No configurada'}")
logging.info(f"Anthropic API key: {'Configurada' if anthropic_api_key else 'No configurada'}")
logging.info(f"Gemini API key: {'Configurada' if gemini_api_key else 'No configurada'}")

# Inicializar cliente de OpenAI
openai_client = None
if openai_api_key:
    try:
        # Configurar el token globalmente para mantener retrocompatibilidad
        openai.api_key = openai_api_key 
        # Crear el cliente usando la API moderna
        openai_client = openai.OpenAI(api_key=openai_api_key)
        logging.info(f"Cliente OpenAI inicializado correctamente. Key: {openai_api_key[:5]}...{openai_api_key[-5:]}")
        
        # Probar cliente con una solicitud sencilla para verificar
        try:
            test_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            logging.info(f"Test de OpenAI exitoso: {test_response.model}")
        except Exception as test_error:
            logging.error(f"Error en test de OpenAI: {str(test_error)}")
    except Exception as e:
        logging.error(f"Error al inicializar cliente OpenAI: {str(e)}")
        openai_client = None
else:
    logging.warning("OPENAI_API_KEY no encontrada. Las funciones de OpenAI no estarán disponibles.")

# Inicializar cliente de Anthropic
anthropic_client = None
if anthropic_api_key:
    try:
        anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        logging.info(f"Cliente Anthropic inicializado correctamente. Key: {anthropic_api_key[:5]}...{anthropic_api_key[-5:]}")
        
        # Probar cliente con una solicitud sencilla para verificar
        try:
            test_response = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=5,
                messages=[
                    {"role": "user", "content": "test"}
                ],
                system="test"
            )
            logging.info(f"Test de Anthropic exitoso: {test_response.model}")
        except Exception as test_error:
            logging.error(f"Error en test de Anthropic: {str(test_error)}")
    except Exception as e:
        logging.error(f"Error al inicializar cliente Anthropic: {str(e)}")
        anthropic_client = None
else:
    logging.warning("ANTHROPIC_API_KEY no encontrada. Las funciones de Anthropic no estarán disponibles.")

# Inicializar cliente de Google Gemini
genai_configured = False
if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        genai_configured = True
        logging.info(f"Google Gemini API configurada correctamente. Key: {gemini_api_key[:5]}...{gemini_api_key[-5:]}")
        
        # Probar cliente con una solicitud sencilla para verificar
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            test_response = model.generate_content("Responde con una palabra")
            logging.info(f"Test de Gemini exitoso: {test_response.text[:20]}")
        except Exception as test_error:
            logging.error(f"Error en test de Gemini: {str(test_error)}")
    except Exception as e:
        logging.error(f"Error al configurar Google Gemini: {str(e)}")
        genai_configured = False
else:
    logging.warning("GEMINI_API_KEY no encontrada. Las funciones de Google Gemini no estarán disponibles.")

# This is defined above, removing duplicate definition
# WORKSPACE_ROOT is already defined and created above

def get_user_workspace(user_id="default"):
    """Get or create a workspace directory for the user."""
    workspace_path = WORKSPACE_ROOT / user_id
    if not workspace_path.exists():
        workspace_path.mkdir(parents=True)
        # Create a README file in the workspace
        with open(workspace_path / "README.md", "w") as f:
            f.write("# Workspace\n\nEste es tu espacio de trabajo. Usa los comandos para crear y modificar archivos aquí.")
    
    # Track workspace in the database if possible
    try:
        from models import User, Workspace
        
        # Use a default user if no proper authentication is set up
        default_user = db.session.query(User).filter_by(username="default_user").first()
        if not default_user:
            default_user = User(
                username="default_user",
                email="default@example.com",
            )
            default_user.set_password("default_password")
            db.session.add(default_user)
            db.session.commit()
        
        # Check if workspace exists in database
        workspace = db.session.query(Workspace).filter_by(
            user_id=default_user.id,
            name=user_id
        ).first()
        
        if not workspace:
            # Create a new workspace record
            workspace = Workspace(
                name=user_id,
                path=str(workspace_path),
                user_id=default_user.id,
                is_default=True,
                last_accessed=datetime.utcnow()
            )
            db.session.add(workspace)
            db.session.commit()
        else:
            # Update the last accessed time
            workspace.last_accessed = datetime.utcnow()
            db.session.commit()
            
    except Exception as e:
        logging.error(f"Error tracking workspace in database: {str(e)}")
    
    return workspace_path

@app.route('/api/test_direct')
def api_test_direct():
    """Ruta de prueba directa para diagnóstico."""
    return jsonify({
        'status': 'ok',
        'message': 'Ruta de prueba directa funciona correctamente',
        'openai_key': 'Configurado' if os.environ.get('OPENAI_API_KEY') else 'No configurado',
        'anthropic_key': 'Configurado' if os.environ.get('ANTHROPIC_API_KEY') else 'No configurado',
        'gemini_key': 'Configurado' if os.environ.get('GEMINI_API_KEY') else 'No configurado'
    })

@app.route('/')
def index():
    """Render the main page."""
    try:
        return render_template('index.html')
    except Exception as e:
        logging.error(f"Error rendering index: {str(e)}")
        return str(e), 500
    
@app.route('/chat')
def chat():
    """Render the chat page with specialized agents."""
    return render_template('chat.html')
    
@app.route('/files')
def files():
    """File explorer view."""
    return render_template('files.html')
    
@app.route('/edit/<path:file_path>')
def edit_file(file_path):
    """Edit a file."""
    try:
        # Get the user workspace
        user_id = session.get('user_id', 'default')
        workspace_path = get_user_workspace(user_id)
        
        # Determine the target file
        # Make sure we don't escape the workspace
        file_path = file_path.replace('..', '')  # Basic path traversal protection
        target_file = (workspace_path / file_path).resolve()
        
        if not str(target_file).startswith(str(workspace_path.resolve())):
            return jsonify({'error': 'Access denied: Cannot access files outside workspace'}), 403
            
        if not target_file.exists():
            return jsonify({'error': 'File not found'}), 404
            
        if target_file.is_dir():
            return jsonify({'error': 'Cannot edit a directory'}), 400
            
        # Read file content
        with open(target_file, 'r') as f:
            content = f.read()
            
        # Determine file type for syntax highlighting
        file_type = get_file_type(target_file.name)
        file_size = target_file.stat().st_size
            
        return render_template('editor.html', 
                             file_path=file_path,
                             file_name=target_file.name,
                             file_content=content,
                             file_type=file_type,
                             file_size=file_size)
    except Exception as e:
        logging.error(f"Error editing file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/code_corrector')
def code_corrector():
    """Render the code corrector page."""
    return render_template('code_corrector.html')
    
@app.route('/api/process_code', methods=['POST'])
def process_code():
    """Process code for corrections and improvements."""
    try:
        data = request.json
        code = data.get('code', '')
        file_path = data.get('file_path', '')
        instructions = data.get('instructions', 'Corrige errores y mejora la calidad del código')
        
        if not code:
            return jsonify({'error': 'No se proporcionó código para procesar'}), 400
            
        # Detectar el lenguaje por la extensión del archivo
        language = 'unknown'
        if file_path:
            ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
            if ext in ['py', 'pyw']:
                language = 'python'
            elif ext in ['js', 'ts', 'jsx', 'tsx']:
                language = 'javascript'
            elif ext in ['html', 'htm']:
                language = 'html'
            elif ext in ['css', 'scss', 'sass']:
                language = 'css'
            elif ext in ['json']:
                language = 'json'
        
        # Preparar el prompt para el modelo
        prompt = f"""Eres un experto corrector de código en {language}. 
        
        Analiza el siguiente código y realiza correcciones y mejoras siguiendo estas instrucciones:
        {instructions}
        
        Código original:
        ```
        {code}
        ```
        
        Por favor, proporciona:
        1. El código corregido
        2. Un resumen de los cambios realizados (máximo 5 puntos)
        3. Una explicación detallada de las correcciones y mejoras

        Formato de respuesta:
        {{"corrected_code": "código corregido aquí", 
          "summary": ["punto 1", "punto 2", ...], 
          "explanation": "explicación detallada aquí"}}
        """
        
        # Utilizar el modelo seleccionado predeterminado (OpenAI)
        response = {}
        model_choice = data.get('model', 'openai')

        if model_choice == 'anthropic' and os.environ.get('ANTHROPIC_API_KEY'):
            # Usar Anthropic Claude
            client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
            completion = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.2,
                system="Eres un experto en programación y tu tarea es corregir y mejorar código. Responde siempre en JSON.",
                messages=[{"role": "user", "content": prompt}]
            )
            try:
                response = json.loads(completion.content[0].text)
            except (json.JSONDecodeError, IndexError):
                # Si no podemos analizar JSON, devolver el texto completo
                response = {
                    "corrected_code": code,  # Mantener el código original
                    "summary": ["No se pudieron procesar las correcciones"],
                    "explanation": completion.content[0].text if completion.content else "No se pudo generar explicación"
                }
                
        elif model_choice == 'gemini' and os.environ.get('GEMINI_API_KEY'):
            # Usar Google Gemini
            genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
            model = genai.GenerativeModel('gemini-1.5-pro')
            gemini_response = model.generate_content(prompt)
            
            try:
                response = json.loads(gemini_response.text)
            except json.JSONDecodeError:
                # Intentar extraer JSON si está en un formato no estándar
                response = {
                    "corrected_code": code,  # Mantener el código original
                    "summary": ["No se pudieron procesar las correcciones"],
                    "explanation": gemini_response.text
                }
                
        else:
            # Usar OpenAI como valor predeterminado
            openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            completion = openai_client.chat.completions.create(
                model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                response_format={"type": "json_object"},
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "Eres un experto en programación y tu tarea es corregir y mejorar código. Responde siempre en JSON."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            try:
                response = json.loads(completion.choices[0].message.content)
            except json.JSONDecodeError:
                response = {
                    "corrected_code": code,  # Mantener el código original
                    "summary": ["No se pudieron procesar las correcciones"],
                    "explanation": completion.choices[0].message.content
                }
        
        # Asegurar que todos los campos necesarios estén presentes
        if 'corrected_code' not in response:
            response['corrected_code'] = code
        if 'summary' not in response:
            response['summary'] = ["No se generó resumen de cambios"]
        if 'explanation' not in response:
            response['explanation'] = "No se generó explicación detallada"
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Error processing code: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/process_instructions', methods=['POST'])
def process_instructions():
    """Process natural language instructions and convert to terminal commands."""
    try:
        data = request.json
        user_input = data.get('instruction', '')
        model_choice = data.get('model', 'openai')  # Default to OpenAI
        
        if not user_input:
            return jsonify({'error': 'No instruction provided'}), 400
        
        terminal_command = ""
        
        # Use selected model to generate command - Versión optimizada para velocidad
        if model_choice == 'openai':
            # Ampliamos la lista de comandos locales para evitar llamadas a la API
            user_input_lower = user_input.lower()
            
            # Mapa de comandos comunes para respuesta inmediata
            command_map = {
                "listar": "ls -la",
                "mostrar archivos": "ls -la", 
                "mostrar directorio": "ls -la",
                "ver archivos": "ls -la",
                "archivos": "ls -la",
                "dir": "ls -la",
                "hola": "echo '¡Hola! ¿En qué puedo ayudarte hoy?'",
                "saludar": "echo '¡Hola! ¿En qué puedo ayudarte hoy?'",
                "fecha": "date",
                "hora": "date +%H:%M:%S",
                "calendario": "cal",
                "ayuda": "echo 'Puedo convertir tus instrucciones en comandos de terminal. Prueba pidiendo crear archivos, listar directorios, etc.'",
                "quien soy": "whoami",
                "donde estoy": "pwd",
                "limpiar": "clear",
                "sistema": "uname -a",
                "memoria": "free -h",
                "espacio": "df -h",
                "procesos": "ps aux"
            }
            
            # Búsqueda exacta primero (más rápida)
            for key, cmd in command_map.items():
                if key in user_input_lower:
                    terminal_command = cmd
                    break
            
            # Patrones específicos si no hubo coincidencia exacta
            if not terminal_command:
                if "crear" in user_input_lower and "carpeta" in user_input_lower:
                    folder_name = user_input_lower.split("carpeta")[-1].strip()
                    terminal_command = f"mkdir -p {folder_name}"
                elif "crear" in user_input_lower and "archivo" in user_input_lower:
                    parts = user_input_lower.split("archivo")
                    if len(parts) > 1:
                        file_name = parts[-1].strip()
                        terminal_command = f"touch {file_name}"
                    else:
                        terminal_command = "touch nuevo_archivo.txt"
                elif "mostrar" in user_input_lower and ("contenido" in user_input_lower or "cat" in user_input_lower):
                    parts = user_input_lower.replace("mostrar", "").replace("contenido", "").replace("del", "").replace("de", "").strip()
                    terminal_command = f"cat {parts}"
                elif "eliminar" in user_input_lower or "borrar" in user_input_lower:
                    words = user_input_lower.split()
                    target_idx = -1
                    for i, word in enumerate(words):
                        if word in ["archivo", "carpeta", "directorio", "fichero"]:
                            target_idx = i + 1
                            break
                    if target_idx >= 0 and target_idx < len(words):
                        target = words[target_idx]
                        terminal_command = f"rm -rf {target}"
                    else:
                        terminal_command = "echo 'Por favor especifica qué quieres eliminar'"
            
            # Solo llamamos a la API si no se encontró un comando local
            if not terminal_command:
                try:
                    if not openai_client:
                        raise Exception("OpenAI API key not configured")
                    
                    # Optimización: Usamos gpt-4o con menos tokens para respuesta más rápida
                    response = openai_client.chat.completions.create(
                        model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                        messages=[
                            {"role": "system", "content": "Convierte instrucciones a comandos de terminal Linux. Responde solo con el comando exacto, sin comillas ni texto adicional."},
                            {"role": "user", "content": user_input}
                        ],
                        max_tokens=60,
                        temperature=0.1
                    )
                    
                    terminal_command = response.choices[0].message.content.strip()
                    # Limpiamos los bloques de código que a veces devuelve
                    terminal_command = terminal_command.replace("```bash", "").replace("```", "").strip()
                except Exception as e:
                    logging.warning(f"OpenAI failed, using fallback: {str(e)}")
                    # Fallback más inteligente basado en palabras clave
                    if "listar" in user_input_lower or "mostrar" in user_input_lower:
                        terminal_command = "ls -la"
                    else:
                        terminal_command = "echo 'No se pudo procesar la instrucción'"
            
        elif model_choice == 'anthropic':
            if not anthropic_client:
                return jsonify({'error': 'Anthropic API key not configured'}), 500
                
            # Use Anthropic to generate terminal command
            response = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",  # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024.
                max_tokens=100,
                messages=[
                    {"role": "user", "content": f"Convert this instruction to a terminal command without any explanation: {user_input}"}
                ],
                system="You are a helpful assistant that converts natural language instructions into terminal commands. Only output the exact command without explanations."
            )
            
            terminal_command = response.content[0].text.strip()
            
        elif model_choice == 'gemini':
            # Implementación básica de Gemini con manejo de errores mejorado
            try:
                import google.generativeai as genai
                
                gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
                if not gemini_api_key:
                    # Fallback para cuando no hay API key configurada
                    logging.warning("Gemini API key not configured, using fallback logic")
                    if "crear" in user_input.lower() and "carpeta" in user_input.lower():
                        folder_name = user_input.lower().split("carpeta")[-1].strip()
                        terminal_command = f"mkdir -p {folder_name}"
                    else:
                        terminal_command = "echo 'Gemini API key not configured'"
                    return jsonify({'command': terminal_command})
                    
                try:
                    genai.configure(api_key=gemini_api_key)
                    # Actualizado para usar gemini-1.5-pro que está disponible
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    
                    response = model.generate_content(
                        f"Convert this instruction to a terminal command without any explanation: {user_input}"
                    )
                    terminal_command = response.text.strip()
                except Exception as api_error:
                    logging.error(f"Gemini API error: {str(api_error)}")
                    # Fallback si hay error con la API
                    if "crear" in user_input.lower() and "carpeta" in user_input.lower():
                        folder_name = user_input.lower().split("carpeta")[-1].strip()
                        terminal_command = f"mkdir -p {folder_name}"
                    else:
                        terminal_command = "echo 'Error connecting to Gemini API'"
                
                # Si el modelo devuelve una respuesta vacía, intentamos con un comando simple
                if not terminal_command:
                    logging.warning("Gemini returned empty response, using fallback logic")
                    
                    # Lógica simple para comandos básicos
                    if "crear" in user_input.lower() and "carpeta" in user_input.lower():
                        folder_name = user_input.lower().split("carpeta")[-1].strip()
                        terminal_command = f"mkdir -p {folder_name}"
                    else:
                        terminal_command = "echo 'No se pudo generar un comando'"
            except Exception as e:
                logging.error(f"Error using Gemini API: {str(e)}")
                # En lugar de devolver error 500, usamos lógica de respaldo
                if "crear" in user_input.lower() and "carpeta" in user_input.lower():
                    folder_name = user_input.lower().split("carpeta")[-1].strip()
                    terminal_command = f"mkdir -p {folder_name}"
                else:
                    terminal_command = "echo 'Error with Gemini API'"
        else:
            return jsonify({'error': 'Invalid model selection'}), 400
            
        logging.debug(f"Generated command using {model_choice}: {terminal_command}")
        
        return jsonify({'command': terminal_command})
    except Exception as e:
        logging.error(f"Error processing instructions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/preview', methods=['GET'])
def preview():
    """Render the preview page."""
    return render_template('preview.html')

@app.route('/api/preview', methods=['POST'])
def generate_preview():
    """Generate a preview of HTML content."""
    try:
        data = request.json
        html_content = data.get('html', '')
        
        if not html_content:
            return jsonify({'error': 'No HTML content provided'}), 400
            
        # TODO: Mejorar esta función para validar y sanitizar el HTML
        
        # Devolver el HTML para previsualización
        return jsonify({
            'success': True,
            'html': html_content
        })
    except Exception as e:
        logging.error(f"Error generating preview: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/execute_command', methods=['POST'])
def execute_command():
    """Execute a terminal command and return the output."""
    try:
        data = request.json
        command = data.get('command', '')
        model_used = data.get('model', 'openai')
        instruction = data.get('instruction', '')
        
        if not command:
            return jsonify({'error': 'No command provided'}), 400
        
        # Get the user workspace
        user_id = session.get('user_id', 'default')
        workspace_path = get_user_workspace(user_id)
        
        # Execute the command in the user's workspace
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=str(workspace_path),  # Set working directory to user workspace
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        # Store command in database - but with error handling
        try:
            # Verificar si existe el usuario por defecto, crearlo si no existe
            from models import User, Command
            
            # Verificar si existe el usuario por defecto
            default_user = db.session.query(User).filter_by(username="default_user").first()
            
            # Si no existe, crear un usuario por defecto
            if not default_user:
                default_user = User(
                    username="default_user", 
                    email="default@example.com"
                )
                default_user.set_password("defaultpassword")
                db.session.add(default_user)
                db.session.commit()
                logging.info("Created default user")
            
            # Create command history entry
            cmd = Command(
                instruction=instruction,
                generated_command=command,
                output=stdout + ("\n" + stderr if stderr else ""),
                status=process.returncode,
                model_used=model_used,
                user_id=default_user.id
            )
            db.session.add(cmd)
            db.session.commit()
        except Exception as e:
            logging.error(f"Error storing command in database: {str(e)}")
            # Seguimos ejecutando aunque falle el guardado en base de datos
        
        result = {
            'stdout': stdout,
            'stderr': stderr,
            'exitCode': process.returncode,
            'workspace': str(workspace_path.relative_to(WORKSPACE_ROOT.parent))
        }
        
        logging.debug(f"Command execution result: {result}")
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error executing command: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    """Procesa mensajes del chat usando el agente especializado seleccionado."""
    try:
        # Mejorar logging para depuración detallada
        logging.info("=== Solicitud recibida en /api/chat ===")
        
        data = request.json
        logging.info(f"Datos recibidos (JSON): {data}")
        
        # Para depuración, verificamos si OpenAI está configurado correctamente
        openai_key = os.environ.get('OPENAI_API_KEY')
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        gemini_key = os.environ.get('GEMINI_API_KEY')
        
        logging.info(f"Estado API keys: OpenAI: {'Configurado' if openai_key else 'No configurado'}, "
                    f"Anthropic: {'Configurado' if anthropic_key else 'No configurado'}, "
                    f"Gemini: {'Configurado' if gemini_key else 'No configurado'}")
        
        user_message = data.get('message', '')
        agent_id = data.get('agent_id', 'default')
        agent_prompt = data.get('agent_prompt', '')
        context = data.get('context', [])
        model_choice = data.get('model', 'openai')
        collaborative_mode = data.get('collaborative_mode', True)  # Modo colaborativo activado por defecto
        chat_mode = data.get('chat_mode', 'normal')  # Modo de chat: normal, creation, code_edit, etc.

@app.route('/api/documents/list', methods=['GET'])
def list_documents():
    """API for listing documents."""
    try:
        user_id = request.args.get('user_id', 'default')
        directory = request.args.get('directory', '.')
        
        files = list_files(directory, user_id)
        
        return jsonify({
            'success': True,
            'files': files
        })
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

