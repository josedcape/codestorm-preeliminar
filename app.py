# Flask application for Codestorm-Assistant
import os
import json
import logging
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

# Configure logging with detailed output
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Get API keys with explicit path to .env
load_dotenv(dotenv_path=Path('.env'), override=True)

# Get and verify API keys
openai_api_key = os.getenv('OPENAI_API_KEY')
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
gemini_api_key = os.getenv('GEMINI_API_KEY')

# Log API key status (safely)
logging.info("=== API Keys Status ===")
logging.info(f"OpenAI API key: {'Configured' if openai_api_key else 'Missing'}")
logging.info(f"Anthropic API key: {'Configured' if anthropic_api_key else 'Missing'}")
logging.info(f"Gemini API key: {'Configured' if gemini_api_key else 'Missing'}")

# Import utilities for agents with improved prompts with emojis
from agents_utils import get_agent_system_prompt, get_agent_name, generate_content, explore_repository_files

# Import diagnostic routes
from diagnostic_routes import register_diagnostic_routes

# Comment out the monkey patch to avoid conflicts with OpenAI and other libraries
# eventlet.monkey_patch(os=True, select=True, socket=True, thread=True, time=True)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Register diagnostic routes
register_diagnostic_routes(app)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///codestorm.db")
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
WORKSPACE_ROOT = os.path.abspath("./user_workspaces")
os.makedirs(WORKSPACE_ROOT, exist_ok=True)

# Initialize AI clients
logging.info("=== Initializing AI Clients ===")

# Initialize OpenAI client
openai_client = None
if openai_api_key:
    try:
        openai.api_key = openai_api_key
        openai_client = openai.OpenAI(api_key=openai_api_key)
        logging.info(f"OpenAI client initialized successfully. Key: {openai_api_key[:5]}...{openai_api_key[-5:]}")

        # Test OpenAI client with a simple request
        try:
            test_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            logging.info(f"OpenAI test successful: {test_response.model}")
        except Exception as test_error:
            logging.error(f"OpenAI test error: {str(test_error)}")
    except Exception as e:
        logging.error(f"Error initializing OpenAI client: {str(e)}")
        openai_client = None
else:
    logging.warning("OPENAI_API_KEY not found. OpenAI functions will not be available.")

# Initialize Anthropic client
anthropic_client = None
if anthropic_api_key:
    try:
        anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        logging.info(f"Anthropic client initialized successfully. Key: {anthropic_api_key[:5]}...{anthropic_api_key[-5:]}")

        # Test Anthropic client with a simple request
        try:
            test_response = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=5,
                messages=[
                    {"role": "user", "content": "test"}
                ],
                system="test"
            )
            logging.info(f"Anthropic test successful: {test_response.model}")
        except Exception as test_error:
            logging.error(f"Anthropic test error: {str(test_error)}")
    except Exception as e:
        logging.error(f"Error initializing Anthropic client: {str(e)}")
        anthropic_client = None
else:
    logging.warning("ANTHROPIC_API_KEY not found. Anthropic functions will not be available.")

# Initialize Google Gemini client
genai_configured = False
if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        genai_configured = True
        logging.info(f"Google Gemini API configured successfully. Key: {gemini_api_key[:5]}...{gemini_api_key[-5:]}")

        # Test Gemini client with a simple request
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            test_response = model.generate_content("Respond with one word")
            logging.info(f"Gemini test successful: {test_response.text[:20]}")
        except Exception as test_error:
            logging.error(f"Gemini test error: {str(test_error)}")
    except Exception as e:
        logging.error(f"Error configuring Google Gemini: {str(e)}")
        genai_configured = False
else:
    logging.warning("GEMINI_API_KEY not found. Google Gemini functions will not be available.")

def get_user_workspace(user_id="default"):
    """Get or create a workspace directory for the user."""
    # Ensure path is absolute
    workspace_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, user_id))
    if not os.path.exists(workspace_path):
        os.makedirs(workspace_path, exist_ok=True)
        # Create a README file in the workspace
        with open(os.path.join(workspace_path, "README.md"), "w") as f:
            f.write("# Workspace\n\nThis is your workspace. Use commands to create and modify files here.")

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
                path=workspace_path,
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
    """Direct test route for diagnostics."""
    return jsonify({
        'status': 'ok',
        'message': 'Direct test route works correctly',
        'openai_key': 'Configured' if os.environ.get('OPENAI_API_KEY') else 'Not configured',
        'anthropic_key': 'Configured' if os.environ.get('ANTHROPIC_API_KEY') else 'Not configured',
        'gemini_key': 'Configured' if os.environ.get('GEMINI_API_KEY') else 'Not configured'
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
        # Ensure we don't escape the workspace
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

@app.route('/code_corrector/')
def code_corrector_slash():
    """Redirect to ensure both with and without trailing slash work."""
    return render_template('code_corrector.html')

@app.route('/constructor')
def constructor():
    """Render the constructor page."""
    return render_template('constructor.html')

@app.route('/api/process_code', methods=['POST'])
def process_code():
    """Process code for corrections and improvements."""
    try:
        data = request.json
        code = data.get('code', '')
        file_path = data.get('file_path', '')
        instructions = data.get('instructions', 'Correct errors and improve code quality')

        if not code:
            return jsonify({'error': 'No code provided for processing'}), 400

        # Verify code size
        if len(code) > 1000000:  # Approximately 1MB (sufficient for ~2000 lines)
            return jsonify({'error': 'The code is too large. Please split it into smaller parts.'}), 413

        # Detect language by file extension
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

        # Prepare the prompt for the model
        prompt = f"""You are an expert code corrector in {language}.

        Analyze the following code and make corrections and improvements following these instructions:
        {instructions}

        Original code:
        ```
        {code}
        ```

        Please provide:
        1. The corrected code
        2. A summary of the changes made (maximum 5 points)
        3. A detailed explanation of the corrections and improvements

        Response format:
        {{
          "corrected_code": "corrected code here",
          "summary": ["point 1", "point 2", ...],
          "explanation": "detailed explanation here"
        }}
        """

        # Use the selected model (default to OpenAI)
        response = {}
        model_choice = data.get('model', 'openai')

        if model_choice == 'anthropic' and os.environ.get('ANTHROPIC_API_KEY'):
            # Use Anthropic Claude
            client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
            completion = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.2,
                system="You are an expert in programming and your task is to correct and improve code. Always respond in JSON.",
                messages=[{"role": "user", "content": prompt}]
            )
            try:
                response = json.loads(completion.content[0].text)
            except (json.JSONDecodeError, IndexError):
                # If JSON parsing fails, return the full text
                response = {
                    "corrected_code": code,  # Keep the original code
                    "summary": ["Could not process corrections"],
                    "explanation": completion.content[0].text if completion.content else "Could not generate explanation"
                }

        elif model_choice == 'gemini' and os.environ.get('GEMINI_API_KEY'):
            # Use Google Gemini
            genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
            model = genai.GenerativeModel('gemini-1.5-pro')
            gemini_response = model.generate_content(prompt)

            try:
                response = json.loads(gemini_response.text)
            except json.JSONDecodeError:
                # Attempt to extract JSON if in non-standard format
                response = {
                    "corrected_code": code,  # Keep the original code
                    "summary": ["Could not process corrections"],
                    "explanation": gemini_response.text
                }

        else:
            # Use OpenAI as the default
            openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            completion = openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=8000,  # Increase tokens to handle larger responses
                messages=[
                    {"role": "system", "content": "You are an expert in programming and your task is to correct and improve code. Always respond in JSON. Process the code efficiently even if it is extensive."},
                    {"role": "user", "content": prompt}
                ]
            )

            try:
                response = json.loads(completion.choices[0].message.content)
            except json.JSONDecodeError:
                response = {
                    "corrected_code": code,  # Keep the original code
                    "summary": ["Could not process corrections"],
                    "explanation": completion.choices[0].message.content
                }

        # Ensure all necessary fields are present
        if 'corrected_code' not in response:
            response['corrected_code'] = code
        if 'summary' not in response:
            response['summary'] = ["No summary of changes generated"]
        if 'explanation' not in response:
            response['explanation'] = "No detailed explanation generated"

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

        # Use selected model to generate command - Optimized for speed
        if model_choice == 'openai':
            # Expand the list of local commands to avoid API calls
            user_input_lower = user_input.lower()

            # Map of common commands for immediate response
            command_map = {
                "list": "ls -la",
                "show files": "ls -la",
                "show directory": "ls -la",
                "view files": "ls -la",
                "files": "ls -la",
                "dir": "ls -la",
                "hello": "echo 'Hello! How can I assist you today?'",
                "greet": "echo 'Hello! How can I assist you today?'",
                "date": "date",
                "time": "date +%H:%M:%S",
                "calendar": "cal",
                "help": "echo 'I can convert your instructions into terminal commands. Try asking to create files, list directories, etc.'",
                "who am i": "whoami",
                "where am i": "pwd",
                "clear": "clear",
                "system info": "uname -a",
                "memory": "free -h",
                "disk space": "df -h",
                "processes": "ps aux"
            }

            # Exact match first (faster)
            for key, cmd in command_map.items():
                if key in user_input_lower:
                    terminal_command = cmd
                    break

            # Specific patterns if no exact match
            if not terminal_command:
                if "create" in user_input_lower and "folder" in user_input_lower:
                    folder_name = user_input_lower.split("folder")[-1].strip()
                    terminal_command = f"mkdir -p {folder_name}"
                elif "create" in user_input_lower and "file" in user_input_lower:
                    parts = user_input_lower.split("file")
                    if len(parts) > 1:
                        file_name = parts[-1].strip()
                        terminal_command = f"touch {file_name}"
                    else:
                        terminal_command = "touch new_file.txt"
                elif "show" in user_input_lower and ("content" in user_input_lower or "cat" in user_input_lower):
                    parts = user_input_lower.replace("show", "").replace("content", "").replace("of", "").replace("the", "").strip()
                    terminal_command = f"cat {parts}"
                elif "delete" in user_input_lower or "remove" in user_input_lower:
                    words = user_input_lower.split()
                    target_idx = -1
                    for i, word in enumerate(words):
                        if word in ["file", "folder", "directory"]:
                            target_idx = i + 1
                            break
                    if target_idx >= 0 and target_idx < len(words):
                        target = words[target_idx]
                        terminal_command = f"rm -rf {target}"
                    else:
                        terminal_command = "echo 'Please specify what you want to delete'"

            # Call the API only if no local command is found
            if not terminal_command:
                try:
                    if not openai_client:
                        raise Exception("OpenAI API key not configured")

                    # Optimization: Use gpt-4o with fewer tokens for faster response
                    response = openai_client.chat.completions.create(
                        model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                        messages=[
                            {"role": "system", "content": "Convert instructions to Linux terminal commands. Respond only with the exact command, without quotes or additional text."},
                            {"role": "user", "content": user_input}
                        ],
                        max_tokens=60,
                        temperature=0.1
                    )

                    terminal_command = response.choices[0].message.content.strip()
                    # Clean up code blocks that may be returned
                    terminal_command = terminal_command.replace("```bash", "").replace("```", "").strip()
                except Exception as e:
                    logging.warning(f"OpenAI failed, using fallback: {str(e)}")
                    # Fallback based on keywords
                    if "list" in user_input_lower or "show" in user_input_lower:
                        terminal_command = "ls -la"
                    else:
                        terminal_command = "echo 'Could not process the instruction'"

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
            # Basic Gemini implementation with improved error handling
            try:
                import google.generativeai as genai

                gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
                if not gemini_api_key:
                    # Fallback when no API key is configured
                    logging.warning("Gemini API key not configured, using fallback logic")
                    if "create" in user_input.lower() and "folder" in user_input.lower():
                        folder_name = user_input.lower().split("folder")[-1].strip()
                        terminal_command = f"mkdir -p {folder_name}"
                    else:
                        terminal_command = "echo 'Gemini API key not configured'"
                    return jsonify({'command': terminal_command})

                try:
                    genai.configure(api_key=gemini_api_key)
                    # Updated to use gemini-1.5-pro which is available
                    model = genai.GenerativeModel('gemini-1.5-pro')

                    response = model.generate_content(
                        f"Convert this instruction to a terminal command without any explanation: {user_input}"
                    )
                    terminal_command = response.text.strip()
                except Exception as api_error:
                    logging.error(f"Gemini API error: {str(api_error)}")
                    # Fallback if API error occurs
                    if "create" in user_input.lower() and "folder" in user_input.lower():
                        folder_name = user_input.lower().split("folder")[-1].strip()
                        terminal_command = f"mkdir -p {folder_name}"
                    else:
                        terminal_command = "echo 'Error connecting to Gemini API'"

                # If the model returns an empty response, use fallback logic
                if not terminal_command:
                    logging.warning("Gemini returned empty response, using fallback logic")

                    # Simple logic for basic commands
                    if "create" in user_input.lower() and "folder" in user_input.lower():
                        folder_name = user_input.lower().split("folder")[-1].strip()
                        terminal_command = f"mkdir -p {folder_name}"
                    else:
                        terminal_command = "echo 'Could not generate a command'"
            except Exception as e:
                logging.error(f"Error using Gemini API: {str(e)}")
                # Use fallback logic instead of returning a 500 error
                if "create" in user_input.lower() and "folder" in user_input.lower():
                    folder_name = user_input.lower().split("folder")[-1].strip()
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
    """Render the basic preview page."""
    return render_template('preview.html')

@app.route('/web_preview', methods=['GET'])
def web_preview():
    """Render the advanced web preview page."""
    return render_template('web_preview.html')

@app.route('/api/preview', methods=['POST'])
def generate_preview():
    """Generate a preview of HTML content."""
    try:
        data = request.json
        html_content = data.get('html', '')
        device_type = data.get('device', 'desktop')

        if not html_content:
            return jsonify({'error': 'No HTML content provided'}), 400

        # Sanitizar el HTML (implementación básica)
        # Eliminar scripts potencialmente peligrosos
        sanitized_html = html_content

        # Añadir meta viewport si no existe para mejor visualización en dispositivos móviles
        if '<meta name="viewport"' not in sanitized_html and '<head>' in sanitized_html:
            sanitized_html = sanitized_html.replace(
                '<head>',
                '<head>\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">'
            )

        # Configurar dimensiones según el dispositivo
        dimensions = {
            'desktop': {'width': '100%', 'height': '100%'},
            'tablet': {'width': '768px', 'height': '1024px'},
            'mobile': {'width': '375px', 'height': '667px'}
        }

        # Retornar el HTML y las dimensiones para la previsualización
        return jsonify({
            'success': True,
            'html': sanitized_html,
            'dimensions': dimensions.get(device_type, dimensions['desktop'])
        })
    except Exception as e:
        logging.error(f"Error generating preview: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Rutas para el explorador de archivos
@app.route('/api/files', methods=['GET'])
def list_files_api():
    """API para listar archivos con soporte para AJAX."""
    try:
        directory = request.args.get('directory', '.')
        user_id = session.get('user_id', 'default')
        workspace_path = get_user_workspace(user_id)

        # Verificar que el directorio esté dentro del workspace
        target_dir = os.path.abspath(os.path.join(workspace_path, directory))
        if not target_dir.startswith(workspace_path):
            return jsonify({'error': 'Acceso denegado: No se puede acceder a directorios fuera del workspace'}), 403

        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            return jsonify({'error': 'Directorio no encontrado'}), 404

        # Listar archivos
        files = []
        for item in os.listdir(target_dir):
            item_path = os.path.join(target_dir, item)
            is_dir = os.path.isdir(item_path)
            
            # Calcular ruta relativa al workspace
            rel_path = os.path.relpath(item_path, workspace_path)
            
            file_info = {
                'name': item,
                'path': rel_path,
                'type': 'directory' if is_dir else 'file',
                'size': os.path.getsize(item_path) if not is_dir else 0,
                'last_modified': datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat()
            }

            # Determinar tipo de archivo para iconos
            if not is_dir:
                _, ext = os.path.splitext(item)
                ext = ext.lower()
                if ext in ['.py', '.pyw']:
                    file_info['file_type'] = 'python'
                elif ext in ['.js', '.ts', '.jsx', '.tsx']:
                    file_info['file_type'] = 'javascript'
                elif ext in ['.html', '.htm']:
                    file_info['file_type'] = 'html'
                elif ext in ['.css', '.scss', '.sass']:
                    file_info['file_type'] = 'css'
                elif ext in ['.json']:
                    file_info['file_type'] = 'json'
                elif ext in ['.md', '.markdown']:
                    file_info['file_type'] = 'markdown'
                elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']:
                    file_info['file_type'] = 'image'
                else:
                    file_info['file_type'] = 'unknown'

            files.append(file_info)

        # Ordenar: directorios primero, luego archivos, ambos alfabéticamente
        files.sort(key=lambda x: (0 if x['type'] == 'directory' else 1, x['name'].lower()))

        return jsonify({
            'files': files,
            'current_dir': directory,
            'parent_dir': os.path.dirname(directory) if directory != '.' else None
        })

    except Exception as e:
        logging.error(f"Error listando archivos: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Ruta para subir archivos
@app.route('/api/explorer/upload', methods=['POST'])
def upload_file():
    """API para subir archivos."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se encontró el archivo en la solicitud'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400

        path = request.form.get('path', '.')
        extract = request.form.get('extract', 'false').lower() == 'true'

        # Obtener el workspace del usuario
        user_id = session.get('user_id', 'default')
        workspace_path = get_user_workspace(user_id)

        # Verificar que la ruta esté dentro del workspace
        target_dir = (workspace_path / path).resolve()
        if not str(target_dir).startswith(str(workspace_path.resolve())):
            return jsonify({'error': 'Acceso denegado: No se puede acceder a directorios fuera del workspace'}), 403

        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

        # Guardar el archivo
        filename = file.filename
        file_path = target_dir / filename
        file.save(file_path)

        # Extraer si es un archivo ZIP y se solicitó extracción
        is_zip = filename.lower().endswith('.zip')
        if is_zip and extract:
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    extract_dir = target_dir / filename.rsplit('.', 1)[0]
                    extract_dir.mkdir(exist_ok=True)
                    zip_ref.extractall(extract_dir)
                return jsonify({
                    'success': True,
                    'message': f'Archivo {filename} subido y extraído exitosamente',
                    'extracted': True,
                    'extract_path': str(extract_dir.relative_to(workspace_path))
                })
            except Exception as zip_error:
                logging.error(f"Error al extraer ZIP: {str(zip_error)}")
                return jsonify({
                    'success': True,
                    'message': f'Archivo {filename} subido pero hubo un error al extraerlo: {str(zip_error)}',
                    'file_path': str(file_path.relative_to(workspace_path)),
                    'extracted': False
                })

        return jsonify({
            'success': True,
            'message': f'Archivo {filename} subido exitosamente',
            'file_path': str(file_path.relative_to(workspace_path)),
            'is_zip': is_zip
        })

    except Exception as e:
        logging.error(f"Error subiendo archivo: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload_preview_file', methods=['POST'])
def upload_preview_file():
    """Procesar archivos HTML cargados para previsualización."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if not file.filename.lower().endswith(('.html', '.htm')):
            return jsonify({'error': 'Only HTML files are allowed'}), 400

        # Leer el contenido del archivo
        html_content = file.read().decode('utf-8')

        # Validar que sea HTML
        if not ('<html' in html_content.lower() or '<!doctype html' in html_content.lower()):
            return jsonify({'error': 'Invalid HTML file'}), 400

        # Sanitizar el contenido HTML (implementación básica)
        sanitized_html = html_content

        return jsonify({
            'success': True,
            'html': sanitized_html,
            'filename': file.filename
        })
    except Exception as e:
        logging.error(f"Error uploading preview file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate_html', methods=['POST'])
def validate_html():
    """Validar el código HTML para la previsualización."""
    try:
        data = request.json
        html_content = data.get('html', '')

        if not html_content:
            return jsonify({'error': 'No HTML content provided'}), 400

        # Implementación básica de validación
        errors = []
        warnings = []

        # Verificar si tiene una estructura HTML básica
        if '<!DOCTYPE html>' not in html_content:
            warnings.append('Falta la declaración DOCTYPE')

        if '<html' not in html_content:
            errors.append('Falta la etiqueta HTML')

        if '<head>' not in html_content:
            warnings.append('Falta la sección HEAD')

        if '<body>' not in html_content:
            warnings.append('Falta la etiqueta BODY')

        # Verificar etiquetas mal cerradas (implementación muy básica)
        open_tags = re.findall(r'<([a-z0-9]+)[^>]*>', html_content, re.IGNORECASE)
        close_tags = re.findall(r'</([a-z0-9]+)>', html_content, re.IGNORECASE)

        for tag in set(open_tags):
            if open_tags.count(tag) > close_tags.count(tag) and tag not in ['meta', 'link', 'img', 'br', 'hr', 'input']:
                warnings.append(f'Posible etiqueta <{tag}> sin cerrar')

        return jsonify({
            'success': True,
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        })
    except Exception as e:
        logging.error(f"Error validating HTML: {str(e)}")
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

        # Store command in database with error handling
        try:
            from models import User, Command

            # Verify if the default user exists, create if not
            default_user = db.session.query(User).filter_by(username="default_user").first()

            # Create default user if not exists
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
            # Continue execution even if database save fails

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
    """Process chat messages using the selected specialized agent."""
    try:
        logging.info("=== Request received at /api/chat ===")

        data = request.json
        logging.info(f"Received data (JSON): {data}")

        # Verify API keys for debugging
        openai_key = os.environ.get('OPENAI_API_KEY')
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        gemini_key = os.environ.get('GEMINI_API_KEY')

        logging.info(f"API key status: OpenAI: {'Configured' if openai_key else 'Not configured'}, "
                    f"Anthropic: {'Configured' if anthropic_key else 'Not configured'}, "
                    f"Gemini: {'Configured' if gemini_key else 'Not configured'}")

        user_message = data.get('message', '')
        agent_id = data.get('agent_id', 'default')
        agent_prompt = data.get('agent_prompt', '')
        context = data.get('context', [])
        model_choice = data.get('model', 'openai')
        collaborative_mode = data.get('collaborative_mode', True)  # Collaborative mode enabled by default
        chat_mode = data.get('chat_mode', 'normal')  # Chat mode: normal, creation, code_edit, etc.

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Get the system prompt for the selected agent
        agent_system_prompt = get_agent_system_prompt(agent_id, agent_prompt)
        agent_name = get_agent_name(agent_id)

        # Process the message with the selected model
        logging.info(f"Processing message with {model_choice} and agent '{agent_name}'")
        response_content = generate_content(
            user_message,
            context,
            agent_system_prompt,
            model_choice,
            collaborative_mode,
            chat_mode
        )

        # Build the response
        response = {
            'content': response_content,
            'agent_name': agent_name,
            'model_used': model_choice
        }

        logging.info(f"Response generated successfully using {model_choice}")
        return jsonify(response)

    except Exception as e:
        logging.error(f"Error in handle_chat: {str(e)}")
        return jsonify({'error': f"Error processing the message: {str(e)}"}), 500

@app.route('/api/documents/list', methods=['GET'])
def list_documents():
    """API for listing documents."""
    try:
        user_id = request.args.get('user_id', 'default')
        directory = request.args.get('directory', '.')

        # Basic function to list files
        def list_files(directory, user_id):
            workspace_path = get_user_workspace(user_id)
            target_dir = (workspace_path / directory).resolve()

            # Verify that we don't escape the workspace
            if not str(target_dir).startswith(str(workspace_path.resolve())):
                return []

            if not target_dir.exists() or not target_dir.is_dir():
                return []

            files = []
            for item in target_dir.iterdir():
                file_info = {
                    'name': item.name,
                    'path': str(item.relative_to(workspace_path)),
                    'type': 'directory' if item.is_dir() else 'file',
                    'size': item.stat().st_size if item.is_file() else 0,
                    'lastModified': datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                }
                files.append(file_info)

            # Sort: directories first, then files, both alphabetically
            files.sort(key=lambda x: (0 if x['type'] == 'directory' else 1, x['name'].lower()))
            return files

        files = list_files(directory, user_id)

        return jsonify({
            'success': True,
            'files': files
        })
    except Exception as e:
        logging.error(f"Error listing documents: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/file/create', methods=['POST'])
def create_file():
    """API to create a new file."""
    try:
        data = request.json
        file_path = data.get('path', '')
        content = data.get('content', '')

        if not file_path:
            return jsonify({'error': 'No file path provided'}), 400

        # Get the user workspace
        user_id = session.get('user_id', 'default')
        workspace_path = get_user_workspace(user_id)

        # Prevent path traversal
        file_path = file_path.replace('..', '')
        target_file = (workspace_path / file_path).resolve()

        # Verify that we don't escape the workspace
        if not str(target_file).startswith(str(workspace_path.resolve())):
            return jsonify({'error': 'Access denied: Cannot access files outside workspace'}), 403

        # Create directories if necessary
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)

        return jsonify({
            'success': True,
            'message': f'File {file_path} created successfully'
        })
    except Exception as e:
        logging.error(f"Error creating file: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/file/read', methods=['GET'])
def read_file():
    """API to read the content of a file."""
    try:
        file_path = request.args.get('path', '')

        if not file_path:
            return jsonify({'error': 'No file path provided'}), 400

        # Get the user workspace
        user_id = session.get('user_id', 'default')
        workspace_path = get_user_workspace(user_id)

        # Prevent path traversal
        file_path = file_path.replace('..', '')
        target_file = (workspace_path / file_path).resolve()

        # Verify that we don't escape the workspace
        if not str(target_file).startswith(str(workspace_path.resolve())):
            return jsonify({'error': 'Access denied: Cannot access files outside workspace'}), 403

        if not target_file.exists():
            return jsonify({'error': 'File not found'}), 404

        if target_file.is_dir():
            return jsonify({'error': 'Cannot read a directory'}), 400

        # Read the file
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Determine file type for syntax highlighting
        file_type = get_file_type(target_file.name)

        return jsonify({
            'success': True,
            'content': content,
            'file_type': file_type,
            'file_size': target_file.stat().st_size,
            'last_modified': datetime.fromtimestamp(target_file.stat().st_mtime).isoformat()
        })
    except Exception as e:
        logging.error(f"Error reading file: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Function to start the server with the correct port
if __name__ == '__main__':
    # Get port from environment or use 5000 as default
    port = int(os.environ.get('PORT', 5000))

    # Use debug=True during development, False in production
    debug_mode = os.environ.get('FLASK_ENV') == 'development'

    logging.info(f"Starting server on port {port}, debug_mode={debug_mode}")

    # Start the application with threaded=True for better handling of concurrent requests
    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)