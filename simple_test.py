import os
import re
import json
import logging
import subprocess
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory, redirect, url_for, flash
from werkzeug.utils import secure_filename
import requests  # Usamos requests en lugar de aiohttp
import project_analyzer  # Importar el analizador de proyectos
from agents_utils import explore_repository_files  # Importar función para explorar repositorios
# Configurar logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'codestorm-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Limitar a 500MB
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'user_workspaces')
# Configuración para manejar solicitudes grandes
app.config['MAX_CONTENT_PATH'] = None

# Funciones auxiliares para el manejo de archivos y directorios
def get_user_workspace(user_id='default'):
    """Obtiene o crea un espacio de trabajo para el usuario."""
    workspace_dir = os.path.join(os.getcwd(), 'user_workspaces', user_id)
    
    # Asegurarnos de que el directorio exista
    os.makedirs(workspace_dir, exist_ok=True)
    
    # Guardar registros de los archivos originales/sistema si no existe
    system_files_record = os.path.join(workspace_dir, '.system_files.json')
    if not os.path.exists(system_files_record):
        # Si es la primera vez, registrar los archivos actuales como del sistema
        try:
            system_files = []
            for root, dirs, files in os.walk(workspace_dir):
                rel_path = os.path.relpath(root, workspace_dir)
                if rel_path == '.':
                    rel_path = ''
                for file in files:
                    if file != '.system_files.json':  # No incluir este archivo
                        file_path = os.path.join(rel_path, file)
                        system_files.append(file_path)
            
            # Guardar la lista de archivos originales
            with open(system_files_record, 'w') as f:
                json.dump(system_files, f)
                
            logger.info(f"Creado registro de archivos del sistema en {workspace_dir}")
        except Exception as e:
            logger.error(f"Error al crear registro de archivos del sistema: {e}")
    
    return workspace_dir

def list_files(directory='.', user_id='default', filter_system_files=True):
    """
    Lista archivos y directorios en una ruta especificada.
    
    Args:
        directory: Directorio relativo dentro del workspace
        user_id: ID del usuario
        filter_system_files: Si es True, filtra los archivos del sistema
    """
    workspace = get_user_workspace(user_id)
    
    # Asegurarnos de que el directorio solicitado está dentro del workspace del usuario
    # y normalizar para evitar path traversal
    if directory == '/' or directory.startswith('/'):
        # Si el usuario solicita la raíz del sistema (que no debería ocurrir normalmente),
        # redirigirlo al workspace
        directory = '.'
    
    target_dir = os.path.normpath(os.path.join(workspace, directory))
    
    # Verificar que el target_dir está dentro del workspace para seguridad
    if not target_dir.startswith(os.path.normpath(workspace)):
        logger.warning(f"Intento de acceso a directorio fuera del workspace: {directory}")
        return []
    
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return []
    
    # Cargar la lista de archivos del sistema si necesitamos filtrar
    system_files = []
    if filter_system_files:
        system_files_record = os.path.join(workspace, '.system_files.json')
        try:
            if os.path.exists(system_files_record):
                with open(system_files_record, 'r') as f:
                    system_files = json.load(f)
        except Exception as e:
            logger.error(f"Error al cargar la lista de archivos del sistema: {e}")
    
    try:
        entries = []
        for entry in os.listdir(target_dir):
            # Saltamos el archivo de sistema que contiene los registros
            if entry == '.system_files.json':
                continue
                
            # Construir la ruta relativa del archivo o directorio
            rel_path = os.path.join(directory, entry) if directory != '.' else entry
            entry_path = os.path.join(workspace, rel_path)
            
            # Verificar que la ruta resultante sigue dentro del workspace
            if not os.path.normpath(entry_path).startswith(os.path.normpath(workspace)):
                logger.warning(f"Saltando entrada potencialmente insegura: {rel_path}")
                continue
                
            # Verificar que la entrada existe antes de intentar determinar su tipo
            if not os.path.exists(entry_path):
                continue
                
            entry_type = 'directory' if os.path.isdir(entry_path) else 'file'
            
            # Verificar si este archivo o directorio debería ser filtrado
            should_filter = False
            if filter_system_files and entry_type == 'file':
                # Verificar si el archivo está en la lista de archivos del sistema
                if rel_path in system_files:
                    should_filter = True
                    
            # Solo agregar si no estamos filtrando este archivo
            if not should_filter:
                if entry_type == 'file':
                    try:
                        file_size = os.path.getsize(entry_path)
                        file_extension = os.path.splitext(entry)[1].lower()[1:] if '.' in entry else ''
                        
                        entries.append({
                            'name': entry,
                            'type': entry_type,
                            'path': rel_path,
                            'size': file_size,
                            'extension': file_extension
                        })
                    except Exception as e:
                        # Ignorar errores al acceder a archivos individuales
                        logger.warning(f"Error al acceder al archivo {entry_path}: {e}")
                        continue
                else:
                    # Para directorios, simplemente los incluimos sin recursión
                    # para evitar problemas con directorios del sistema
                    entries.append({
                        'name': entry,
                        'type': entry_type,
                        'path': rel_path
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
    
@app.route('/files')
def files():
    """Ruta al explorador de archivos."""
    return render_template('files.html')

@app.route('/code_corrector')
def code_corrector():
    """Ruta al corrector de código."""
    return render_template('code_corrector.html')

@app.route('/constructor')
def constructor():
    """Ruta al constructor de tareas."""
    return render_template('constructor.html')

@app.route('/api/analyze_code', methods=['POST'])
def analyze_code():
    """
    API para analizar código con instrucciones específicas.
    Utiliza los modelos de IA para mejorar y optimizar el código proporcionado.
    
    Espera:
    - code: código a analizar
    - language: lenguaje del código
    - instructions: instrucciones específicas (opcional)
    - model: modelo de IA a utilizar (openai, anthropic, gemini)
    - agent_id: tipo de agente a utilizar (developer, architect, advanced, general)
    
    Retorna:
    - improved_code: código mejorado
    - explanations: lista de explicaciones sobre los cambios
    - suggestions: lista de sugerencias para mejoras adicionales
    """
    try:
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'python')
        instructions = data.get('instructions', 'Mejora y optimiza este código.')
        model = data.get('model', 'openai')
        agent_id = data.get('agent_id', 'developer')
        
        logger.info(f"Analizando código en {language} con modelo {model}, agente {agent_id}")
        
        # Simular respuesta con mejoras básicas según el lenguaje
        # En una implementación real, aquí se llamaría a la función de análisis de la IA
        
        improved_code = code
        explanations = []
        suggestions = []
        
        # Simulación básica de mejoras según el lenguaje
        if language == 'python':
            if 'import ' not in code:
                improved_code = '# Añadir imports necesarios\nimport os\nimport sys\n\n' + code
                explanations.append('Se agregaron imports básicos que podrían ser necesarios.')
            
            if 'print(' in code and not 'if __name__' in code:
                improved_code += '\n\nif __name__ == "__main__":\n    # Código principal aquí\n    pass'
                explanations.append('Se agregó el bloque if __name__ == "__main__" para mejor estructura.')
            
            suggestions = [
                'Considera agregar docstrings para documentar las funciones.',
                'Utiliza typing para anotaciones de tipo.',
                'Agrega manejo de errores con bloques try/except.',
                'Implementa logging para facilitar la depuración.'
            ]
            
        elif language == 'javascript':
            if 'var ' in code:
                improved_code = code.replace('var ', 'const ')
                explanations.append('Se reemplazaron declaraciones "var" por "const" para mejor control de ámbito.')
            
            suggestions = [
                'Considera usar funciones de flecha en lugar de funciones tradicionales.',
                'Implementa async/await para código asíncrono más legible.',
                'Utiliza destructuring para simplificar asignaciones.',
                'Agrega validación de parámetros al inicio de las funciones.'
            ]
            
        elif language == 'html':
            if '<!DOCTYPE html>' not in code:
                improved_code = '<!DOCTYPE html>\n<html lang="es">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Documento</title>\n</head>\n<body>\n' + code + '\n</body>\n</html>'
                explanations.append('Se agregó la estructura básica de un documento HTML5.')
            
            suggestions = [
                'Asegúrate de usar etiquetas semánticas como <header>, <footer>, <main>.',
                'Incluye atributos alt en todas las imágenes para accesibilidad.',
                'Considera agregar metaetiquetas para SEO.',
                'Verifica la accesibilidad con roles ARIA cuando sea necesario.'
            ]
            
        # Modificamos la respuesta según el agente especializado seleccionado
        if agent_id == "developer":
            explanations.append('Análisis realizado por el agente Desarrollador de Código, enfocado en buenas prácticas y optimización.')
            suggestions.append('El agente desarrollador recomienda seguir las convenciones de estilo del lenguaje seleccionado.')
        elif agent_id == "architect":
            explanations.append('Análisis realizado por el agente Arquitecto de Sistemas, enfocado en estructura y escalabilidad.')
            suggestions.append('El agente arquitecto recomienda considerar patrones de diseño apropiados para esta implementación.')
        elif agent_id == "advanced":
            explanations.append('Análisis realizado por el agente Experto Avanzado, enfocado en técnicas sofisticadas y optimizaciones de alto nivel.')
            suggestions.append('El agente avanzado detecta oportunidades para aplicar técnicas más sofisticadas en este código.')
            
        # Retornar respuesta
        return jsonify({
            'success': True,
            'improved_code': improved_code,
            'explanations': explanations,
            'suggestions': suggestions
        })
        
    except Exception as e:
        logger.error(f"Error al analizar código: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/edit_file')
def edit_file():
    """Editar un archivo."""
    file_path = request.args.get('path', '')
    if not file_path:
        return redirect('/files')
    
    try:
        workspace = get_user_workspace()
        full_path = os.path.join(workspace, file_path)
        
        # Verificar path traversal
        if not os.path.normpath(full_path).startswith(os.path.normpath(workspace)):
            flash('Ruta de archivo inválida', 'danger')
            return redirect('/files')
        
        # Verificar que el archivo existe
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            flash('El archivo no existe', 'danger')
            return redirect('/files')
        
        # Leer el archivo
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Determinar el tipo de archivo
        file_type = os.path.splitext(file_path)[1].lstrip('.').upper() or 'TXT'
        
        return render_template('editor.html', file_path=file_path, file_content=content, file_type=file_type)
    except Exception as e:
        logger.error(f"Error al editar archivo: {str(e)}")
        flash(f'Error al abrir el archivo: {str(e)}', 'danger')
        return redirect('/files')

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

@app.route('/api/save_file', methods=['POST'])
def save_file():
    """Guarda cambios en un archivo."""
    try:
        data = request.json
        file_path = data.get('file_path')
        content = data.get('content', '')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'Se requiere ruta de archivo'
            }), 400
        
        workspace = get_user_workspace()
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
            'file_path': file_path,
            'message': 'Archivo guardado correctamente'
        })
    except Exception as e:
        logger.error(f"Error al guardar archivo: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/files/delete', methods=['POST'])
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
        
        # Verificar que el archivo o directorio existe
        if not os.path.exists(full_path):
            return jsonify({
                'success': False,
                'error': 'El archivo o directorio no existe'
            }), 404
        
        # Eliminar archivo o directorio
        if os.path.isfile(full_path):
            os.remove(full_path)
        elif os.path.isdir(full_path):
            import shutil
            shutil.rmtree(full_path)
        
        return jsonify({
            'success': True,
            'file_path': file_path,
            'message': f"Se ha eliminado {file_path}"
        })
    except Exception as e:
        logger.error(f"Error al eliminar archivo: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API para análisis de código
@app.route('/api/analyze_code', methods=['POST'])
def process_code():
    """
    API para analizar código con instrucciones específicas.
    Utiliza los modelos de IA para mejorar y optimizar el código proporcionado.
    """
    try:
        data = request.json
        user_id = data.get('user_id', 'default')
        code = data.get('code')
        language = data.get('language', 'python')
        instructions = data.get('instructions', '')
        model = data.get('model', 'openai')
        agent_id = data.get('agent_id', 'developer')
        
        logger.info(f"Analizando código en {language} con modelo {model}, agente {agent_id}")
        
        if not code:
            return jsonify({
                'success': False,
                'error': 'Se requiere código para analizar'
            }), 400
        
        # En una implementación real, aquí se conectaría con un servicio de IA
        # para analizar el código. Para esta versión simplificada, simulamos una respuesta.
        
        # Análisis básico de código
        improved_code = code
        explanations = ["El código se ve bien estructurado."]
        suggestions = ["Considera añadir comentarios para mejorar la legibilidad."]
        
        # Modificamos la respuesta según el agente especializado seleccionado
        if agent_id == "developer":
            explanations.append('Análisis realizado por el agente Desarrollador de Código, enfocado en buenas prácticas y optimización.')
            suggestions.append('Recomendación del desarrollador: Sigue las convenciones de estilo del lenguaje seleccionado.')
        elif agent_id == "architect":
            explanations.append('Análisis realizado por el agente Arquitecto de Sistemas, enfocado en estructura y escalabilidad.')
            suggestions.append('Recomendación del arquitecto: Considera patrones de diseño apropiados para esta implementación.')
        elif agent_id == "advanced":
            explanations.append('Análisis realizado por el agente Experto Avanzado, enfocado en técnicas sofisticadas y optimizaciones de alto nivel.')
            suggestions.append('Recomendación del experto: Hay oportunidades para aplicar técnicas más avanzadas en este código.')
        
        # Respuestas según el lenguaje
        if language == 'python':
            if 'def ' in code and not code.strip().startswith('def '):
                explanations.append("Has definido funciones correctamente.")
            if 'import ' in code:
                suggestions.append("Verifica que todas las importaciones sean necesarias para tu código.")
            if 'while ' in code and 'break' not in code:
                suggestions.append("Considera añadir una condición de salida en tu bucle while para evitar bucles infinitos.")
                
        elif language == 'javascript':
            if 'function ' in code:
                explanations.append("Has definido funciones correctamente.")
            if 'var ' in code:
                suggestions.append("Considera usar 'let' o 'const' en lugar de 'var' para una mejor gestión de ámbito.")
            if 'console.log' in code:
                suggestions.append("Recuerda eliminar las declaraciones console.log en código de producción.")
                
        # Mejoras simuladas basadas en instrucciones
        if instructions:
            if 'optimizar' in instructions.lower() or 'rendimiento' in instructions.lower():
                suggestions.append("Para optimizar el rendimiento, considera utilizar estructuras de datos más eficientes.")
                explanations.append("El rendimiento podría mejorarse reduciendo las operaciones redundantes.")
            
            if 'seguridad' in instructions.lower():
                suggestions.append("Para mejorar la seguridad, valida todas las entradas del usuario.")
                explanations.append("Es importante proteger tu código contra entradas maliciosas.")
        
        # Simulamos mejoras en el código para casos específicos
        if language == 'python' and 'fibonacci' in code.lower() and 'def fibonacci' in code.lower():
            if 'fibonacci(n-1) + fibonacci(n-2)' in code:
                improved_code = code.replace('def fibonacci(n):', 'def fibonacci(n):  # Versión optimizada')
                improved_code = improved_code.replace('    if n <= 0:', '    # Verificación de entrada\n    if n <= 0:')
                improved_code = improved_code.replace('    elif n == 1:', '    elif n == 1:')
                improved_code = improved_code.replace('    else:\n        return fibonacci(n-1) + fibonacci(n-2)', 
                                                   '    else:\n        # Usamos enfoque iterativo para mejor rendimiento\n'
                                                   '        a, b = 0, 1\n        for _ in range(2, n + 1):\n'
                                                   '            a, b = b, a + b\n        return b')
                
                explanations = ["Tu implementación usa recursión, lo que puede llevar a desbordamiento de pila para valores grandes.",
                               "La función recursiva tiene complejidad de tiempo O(2^n), que es exponencial.",
                               "La implementación iterativa propuesta tiene complejidad O(n), mucho más eficiente."]
                
                suggestions = ["Utiliza el enfoque iterativo para mejorar el rendimiento.",
                              "Añade validación de entrada para manejar valores negativos.",
                              "Considera implementar memoización si necesitas mantener el enfoque recursivo."]
        
        return jsonify({
            'success': True,
            'improved_code': improved_code,
            'explanations': explanations,
            'suggestions': suggestions
        })
    except Exception as e:
        logger.error(f"Error al analizar código: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# APIs para chat y generación de contenido
@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API para chat con agentes especializados."""
    try:
        # Registro detallado para diagnóstico
        logger.info("=== Solicitud recibida en /api/chat ===")
        
        data = request.json
        logger.info(f"Datos recibidos (JSON): {data}")
        
        user_id = data.get('user_id', 'default')
        message = data.get('message', '')
        agent_id = data.get('agent_id', 'general')
        model_choice = data.get('model', 'openai')
        context = data.get('context', [])
        
        # Para depuración, verificamos si las claves API están configuradas
        openai_key = os.environ.get('OPENAI_API_KEY')
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        gemini_key = os.environ.get('GEMINI_API_KEY')
        
        logger.info(f"Estado API keys: OpenAI: {'Configurado' if openai_key else 'No configurado'}, "
                   f"Anthropic: {'Configurado' if anthropic_key else 'No configurado'}, "
                   f"Gemini: {'Configurado' if gemini_key else 'No configurado'}")
        
        logger.info(f"Procesando mensaje: '{message}' con agente: {agent_id}, modelo: {model_choice}")
        
        if not message or message.strip() == '':
            error_msg = 'Se requiere un mensaje no vacío'
            logger.warning(f"Error: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Filtrar mensajes de sistema del contexto (como "Conectando con el servidor...")
        filtered_context = [msg for msg in context if msg.get('role') != 'system' and msg.get('content')]
        
        # Importar aquí para evitar problemas de importación circular
        from agents_utils import generate_response
        
        # Llamar a la función real de generación de respuesta
        response_data = generate_response(
            user_message=message,
            agent_id=agent_id,
            context=filtered_context,
            model=model_choice
        )
        
        if not response_data.get('success'):
            return jsonify({
                'success': False,
                'error': response_data.get('error', 'Error generando respuesta')
            }), 500
        
        response = response_data.get('response', '')
        logger.info(f"Respuesta generada correctamente para '{message}'")
        
        return jsonify({
            'success': True,
            'message': message,
            'response': response,
            'agent_id': agent_id,
            'debug_info': {
                'api_keys_configured': {
                    'openai': bool(openai_key),
                    'anthropic': bool(anthropic_key),
                    'gemini': bool(gemini_key)
                },
                'message_type': 'complex'
            }
        })
    except Exception as e:
        error_details = str(e)
        logger.error(f"Error en el chat: {error_details}")
        
        # Proporcionar más detalles sobre el error para facilitar el diagnóstico
        return jsonify({
            'success': False,
            'error': error_details,
            'error_type': type(e).__name__,
            'suggestion': "Por favor, verifica el formato de tu solicitud y que todos los campos requeridos estén presentes."
        }), 500

# API para ejecución de comandos
@app.route('/api/execute', methods=['POST'])
def api_execute_command():
    """API para ejecutar comandos directamente en el workspace del usuario."""
    # Definir command fuera del bloque try para que esté disponible en los bloques except
    command = None
    
    try:
        data = request.json
        user_id = data.get('user_id', 'default')
        command = data.get('command')
        agent_id = data.get('agent_id', 'general')
        
        if not command:
            return jsonify({
                'success': False,
                'error': 'Se requiere un comando'
            }), 400
        
        # Obtener el workspace del usuario (ahora inicia vacío)
        workspace = get_user_workspace(user_id)
        
        # Agregar información de registro sobre el comando ejecutado
        logger.info(f"Ejecutando comando: '{command}' en workspace '{user_id}', agente: {agent_id}")
        
        # Ejecutar el comando en un subproceso
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=workspace
        )
        
        # Esperar la respuesta con un tiempo límite de 30 segundos
        stdout, stderr = process.communicate(timeout=30)
        status = process.returncode
        
        # Preparar la respuesta con los resultados de la ejecución
        stdout_text = stdout.decode('utf-8', errors='replace')
        stderr_text = stderr.decode('utf-8', errors='replace')
        
        # Registrar el resultado del comando si hubo un error
        if status != 0:
            logger.warning(f"Comando '{command}' terminó con código {status}. Stderr: {stderr_text}")
        
        result = {
            'success': True,
            'command': command,
            'stdout': stdout_text,
            'stderr': stderr_text,
            'status': status,
            'agent_id': agent_id
        }
        
        return jsonify(result)
    except subprocess.TimeoutExpired as e:
        # Ahora command está disponible aquí
        error_msg = f'Tiempo de ejecución agotado (30s)'
        if command:
            error_msg += f' para el comando: {command}'
            logger.error(f"Timeout al ejecutar comando: '{command}'")
        else:
            logger.error("Timeout al ejecutar un comando desconocido")
        
        return jsonify({
            'success': False,
            'error': error_msg
        }), 504
    except Exception as e:
        error_cmd = f" ejecutando '{command}'" if command else ""
        logger.error(f"Error al ejecutar comando{error_cmd}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/constructor', methods=['POST'])
def api_constructor():
    """
    API específica para el Constructor de Tareas.
    
    Permite la creación guiada de aplicaciones mediante análisis, 
    retroalimentación y construcción paso a paso. Mantiene un estado
    de conversación más complejo que incluye las fases del proyecto,
    archivos generados y progreso de implementación.
    
    Espera:
    - message: mensaje del usuario
    - agent_id: ID del agente especializado (default: architect)
    - context: historial de mensajes
    - model: modelo de IA a utilizar (openai, anthropic, gemini)
    - collaborative_mode: si está activado el modo colaborativo
    - conversation_state: estado de la conversación específico del constructor
    
    Retorna:
    - La respuesta al mensaje
    - Acciones especiales a realizar (crear archivos, ejecutar comandos, etc.)
    - Estado de conversación actualizado
    """
    try:
        # Registro detallado para diagnóstico
        logger.info("=== Solicitud recibida en /api/constructor ===")
        
        data = request.json
        logger.info(f"Datos recibidos (JSON): {data}")
        
        user_id = data.get('user_id', 'default')
        message = data.get('message', '')
        agent_id = data.get('agent_id', 'architect')  # Por defecto usamos el arquitecto
        model_choice = data.get('model', 'openai')
        context = data.get('context', [])
        conversation_state = data.get('conversation_state', {})
        
        # Para depuración, verificamos si las claves API están configuradas
        openai_key = os.environ.get('OPENAI_API_KEY')
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        gemini_key = os.environ.get('GEMINI_API_KEY')
        
        logger.info(f"Estado API keys: OpenAI: {'Configurado' if openai_key else 'No configurado'}, "
                   f"Anthropic: {'Configurado' if anthropic_key else 'No configurado'}, "
                   f"Gemini: {'Configurado' if gemini_key else 'No configurado'}")
        
        logger.info(f"Procesando mensaje de constructor: '{message}' con agente: {agent_id}, modelo: {model_choice}")
        
        if not message or message.strip() == '':
            error_msg = 'Se requiere un mensaje no vacío'
            logger.warning(f"Error: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Filtrar mensajes de sistema del contexto
        filtered_context = [msg for msg in context if msg.get('role') != 'system' and msg.get('content')]
        
        # Para el constructor, añadimos instrucciones especiales al mensaje
        # para enfocarlo en el desarrollo guiado de aplicaciones
        special_instructions = f"""
        Estás actuando como un Constructor de Tareas especializado, guiando paso a paso el desarrollo de una aplicación.
        
        Estado actual del proyecto:
        - Fase: {conversation_state.get('taskPhase', 'initial')}
        - Tipo de proyecto: {conversation_state.get('projectType', 'No definido')}
        - Progreso de implementación: {conversation_state.get('implementationProgress', 0)}%
        
        Tu objetivo es:
        1. Analizar los requisitos del proyecto
        2. Planificar la estructura de los archivos y componentes
        3. Guiar la implementación paso a paso
        4. Sugerir mejoras y probar la funcionalidad
        
        Proporciona orientación precisa, realiza preguntas cuando necesites más información,
        y ayuda al usuario a completar su proyecto de manera efectiva.
        """
        
        # Importar aquí para evitar problemas de importación circular
        from agents_utils import generate_response
        
        # Modificar el mensaje para incluir las instrucciones especiales
        enhanced_message = f"{message}\n\n{special_instructions}"
        
        # Llamar a la función de generación de respuesta
        response_data = generate_response(
            user_message=enhanced_message,
            agent_id=agent_id,
            context=filtered_context,
            model=model_choice
        )
        
        if not response_data.get('success'):
            return jsonify({
                'success': False,
                'error': response_data.get('error', 'Error generando respuesta')
            }), 500
        
        response = response_data.get('response', '')
        logger.info(f"Respuesta de constructor generada correctamente para '{message}'")
        
        # Analizamos el mensaje para detectar acciones a realizar
        actions = []
        
        # Por ahora, solo un constructor de acciones simple
        # En una implementación completa, se analizaría la respuesta para detectar
        # creación de archivos, ejecución de comandos, actualización de progreso, etc.
        
        # Actualizar el estado de la conversación
        # En una implementación real, se actualizaría según el análisis de la respuesta
        if conversation_state.get('taskPhase') == 'initial' and len(filtered_context) <= 2:
            # Primera interacción, cambiar a fase de análisis
            conversation_state['taskPhase'] = 'analysis'
            conversation_state['implementationProgress'] = 10
            
            # Añadir acción para actualizar progreso
            actions.append({
                'type': 'update_progress',
                'progress': 10
            })
        
        return jsonify({
            'success': True,
            'message': message,
            'response': response,
            'agent_id': agent_id,
            'actions': actions,
            'conversation_state': conversation_state,
            'debug_info': {
                'api_keys_configured': {
                    'openai': bool(openai_key),
                    'anthropic': bool(anthropic_key),
                    'gemini': bool(gemini_key)
                },
                'message_type': 'complex'
            }
        })
    except Exception as e:
        error_details = str(e)
        logger.error(f"Error en el constructor: {error_details}")
        
        return jsonify({
            'success': False,
            'error': error_details,
            'error_type': type(e).__name__,
            'suggestion': "Por favor, verifica el formato de tu solicitud y que todos los campos requeridos estén presentes."
        }), 500

@app.route('/api/process', methods=['POST'])
def process_instruction():
    """
    Procesa una instrucción en lenguaje natural para realizar acciones.
    
    La instrucción puede ser:
    - Crear un archivo
    - Crear una carpeta
    - Ejecutar un comando
    - Construir una aplicación
    - Modificar un archivo existente
    """
    try:
        data = request.json
        user_id = data.get('user_id', 'default')
        instruction = data.get('instruction')
        model = data.get('model', 'openai')
        agent_id = data.get('agent_id', 'general')
        
        if not instruction:
            return jsonify({
                'success': False,
                'error': 'Se requiere una instrucción'
            }), 400
        
        logger.info(f"Procesando instrucción: '{instruction}' con modelo: {model}, agente: {agent_id}")
        workspace = get_user_workspace(user_id)
        
        # Detectar si la instrucción parece ser un comando directo
        command_prefixes = ['ejecuta ', 'corre ', 'run ', 'python ', 'node ', 'npm ', 'ls ', 'mkdir ', 'touch ', 'cat ', 'git ']
        is_command = any(instruction.lower().startswith(prefix) for prefix in command_prefixes)
        
        if is_command:
            # Extraer el comando del prefijo
            command = instruction
            for prefix in ['ejecuta ', 'corre ', 'run ']:
                if instruction.lower().startswith(prefix):
                    command = instruction[len(prefix):]
                    break
            
            # Registrar la acción
            logger.info(f"Procesando instrucción como comando directo: '{command}' con agente {agent_id}")
            
            # Ejecutar el comando
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=workspace
            )
            
            stdout, stderr = process.communicate(timeout=30)
            status = process.returncode
            
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')
            
            # Registrar el resultado si hubo error
            if status != 0:
                logger.warning(f"Comando '{command}' terminó con código {status}. Stderr: {stderr_text}")
            
            return jsonify({
                'success': True,
                'command': command,
                'result': stdout_text,
                'error': stderr_text,
                'status': status,
                'agent_id': agent_id,
                'model': model
            })
            
        # CASO 1: Construir una aplicación
        # Patrones para detectar intención de construir una aplicación
        build_app_patterns = [
            r'(?:construye|crea|genera|haz|monta|inicia)\s+(?:una|un)?\s*(?:aplicaci[oó]n|app|proyecto|programa|chatbot|sitio|página|pagina|web)',
            r'(?:inicia|configura|prepara)\s+(?:una|un)?\s*(?:proyecto|aplicaci[oó]n|chatbot|sitio|página|pagina|web)',
            r'(?:crea|genera)\s+(?:una|un)?\s*(?:proyecto|aplicaci[oó]n|chatbot|sitio|página|pagina|web)\s+(?:de|con|usando|basad[oa]\s+en)\s+(?:Flask|React|Node|Express|Vue|Angular)',
            r'(?:quiero|necesito)\s+(?:hacer|crear|construir|desarrollar)\s+(?:una|un)?\s*(?:aplicaci[oó]n|app|proyecto|chatbot|sitio|página|pagina|web)',
            r'(?:ayuda|ayudame)\s+a\s+(?:crear|construir|desarrollar)\s+(?:una|un)?\s*(?:aplicaci[oó]n|app|proyecto|chatbot|sitio|página|pagina|web)',
            r'(?:crea|construye|genera|desarrolla)\s+(?:una|un)?\s*(?:chatbot|bot)\s+(?:usando|con|basad[oa]\s+en|moderno)?\s+(?:que\s+tenga|que\s+use)?'
        ]
        
        is_build_app = any(re.search(pattern, instruction.lower()) for pattern in build_app_patterns)
        
        # Patrones para detectar exploración de repositorios
        repo_patterns = [
            r'explora(?:r)? (?:el )?(?:repositorio|repo)(?: ([a-zA-Z0-9_\-\.]+))?',  # Nombre del repo opcional
            r'explora(?:r)? (?:los )?archivos(?: del| en el)? (?:repositorio|repo) ([a-zA-Z0-9_\-\.]+)',
            r'busca(?:r)? (?:en )?(?:el )?(?:repositorio|repo) ([a-zA-Z0-9_\-\.]+)',
            r'modifica(?:r)? (?:el )?archivo ([a-zA-Z0-9_\-\.\/]+) (?:en|del) (?:repositorio|repo) ([a-zA-Z0-9_\-\.]+)',
            r'lee(?:r)? (?:el )?archivo ([a-zA-Z0-9_\-\.\/]+) (?:en|del) (?:repositorio|repo) ([a-zA-Z0-9_\-\.]+)',
            r'crea(?:r)? (?:un )?archivo ([a-zA-Z0-9_\-\.\/]+) (?:en|del) (?:repositorio|repo) ([a-zA-Z0-9_\-\.]+)',
            r'lista(?:r)? (?:los )?archivos (?:en|del) (?:repositorio|repo) ([a-zA-Z0-9_\-\.]+)',
            r'muestra(?:me)? (?:el )?(?:contenido|código) de ([a-zA-Z0-9_\-\.\/]+) (?:en|del) (?:repositorio|repo) ([a-zA-Z0-9_\-\.]+)',
            r'(?:ver|mostrar|listar) (?:el )?(?:repositorio|repo) ([a-zA-Z0-9_\-\.]+)'
        ]
        
        is_repo_exploration = False
        repo_name = None
        
        # Comprobar si el mensaje coincide con algún patrón de exploración
        for pattern in repo_patterns:
            match = re.search(pattern, instruction.lower())
            if match:
                is_repo_exploration = True
                # Extraer nombre del repositorio (está en el grupo 1 o 2 dependiendo del patrón)
                if not match.groups():
                    repo_name = None  # No se especificó un nombre de repositorio
                elif len(match.groups()) == 1:
                    repo_name = match.group(1)
                else:
                    repo_name = match.group(2)
                break
                
        # Caso especial: si el mensaje es exactamente "explora el repositorio" sin nombre
        if instruction.lower().strip() in ["explora el repositorio", "explorar el repositorio", 
                                          "explora repositorio", "explorar repositorio",
                                          "muestra los repositorios", "mostrar repositorios",
                                          "ver repositorios", "listar repositorios"]:
            is_repo_exploration = True
            repo_name = None
            
        # CASO PARA EXPLORACIÓN DE REPOSITORIOS
        if is_repo_exploration:
            logger.info(f"Detectada intención de explorar repositorio: '{instruction}', repo: {repo_name}")
            
            # Si no se especificó un nombre de repositorio, listar los repositorios disponibles
            if not repo_name:
                # Buscar carpetas en el workspace que podrían ser repositorios
                repos = []
                for item in os.listdir(workspace):
                    item_path = os.path.join(workspace, item)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        # Verificar si es un repositorio Git
                        if os.path.exists(os.path.join(item_path, '.git')):
                            repos.append(f"{item} (Git)")
                        else:
                            repos.append(item)
                
                if repos:
                    response_message = "📚 Repositorios disponibles en tu espacio de trabajo:\n\n"
                    for repo in repos:
                        response_message += f"- {repo}\n"
                    response_message += "\nPuedes explorar un repositorio específico usando 'explora el repositorio [nombre]'."
                else:
                    response_message = "📭 No hay repositorios disponibles en tu espacio de trabajo.\n\nPuedes clonar un repositorio usando la opción 'Clonar repositorio de GitHub' o crear uno nuevo con 'crea un archivo [nombre]'."
                
                return jsonify({
                    'success': True,
                    'response': response_message,
                    'agent_id': agent_id,
                    'model': model
                })
            
            # Si se especificó un repositorio, verificar si existe
            repo_path = os.path.join(workspace, repo_name)
            
            if not os.path.exists(repo_path):
                return jsonify({
                    'success': False,
                    'error': f"El repositorio '{repo_name}' no existe en tu espacio de trabajo. Por favor, clona primero el repositorio usando la opción de GitHub o especifica un repositorio existente."
                })
            
            # Explorar el repositorio según la instrucción
            result = explore_repository_files(instruction, repo_path, model)
            
            if result.get('success'):
                # Construir una respuesta contextual según la acción realizada
                action = result.get('action', '')
                response_message = f"✅ He procesado tu instrucción para explorar el repositorio '{repo_name}'.\n\n"
                
                if action == 'explore':
                    # Formatear la lista de archivos/directorios para mostrarlos
                    items = result.get('items', [])
                    response_message += f"📂 Contenido del directorio '{result.get('path', '.')}' en el repositorio:\n\n"
                    
                    for item in items:
                        if item['type'] == 'directory':
                            response_message += f"📁 {item['name']}/\n"
                        else:
                            response_message += f"📄 {item['name']} ({item.get('file_type', '')})\n"
                            
                elif action == 'read':
                    # Mostrar el contenido del archivo con formato
                    content = result.get('content', '')
                    file_type = result.get('file_type', '')
                    response_message += f"📄 Contenido del archivo '{result.get('path', '')}':\n\n"
                    response_message += f"```{file_type}\n{content}\n```\n"
                    
                elif action == 'modify':
                    # Mostrar resumen de cambios realizados
                    response_message += f"✏️ {result.get('message', '')}\n\n"
                    if 'changes_summary' in result:
                        response_message += "Cambios realizados:\n"
                        response_message += f"```diff\n{result['changes_summary']}\n```\n"
                    
                elif action == 'create':
                    # Mostrar información sobre el archivo creado
                    response_message += f"✨ {result.get('message', '')}\n\n"
                    if 'content' in result:
                        file_extension = os.path.splitext(result.get('path', ''))[1].lstrip('.')
                        preview = result.get('content', '')
                        response_message += f"Vista previa del contenido:\n```{file_extension}\n{preview}\n```\n"
                
                elif action == 'search':
                    # Mostrar resultados de búsqueda
                    results = result.get('results', [])
                    query = result.get('query', '')
                    search_type = result.get('type', '')
                    
                    response_message += f"🔍 Búsqueda de '{query}' (tipo: {search_type}):\n\n"
                    if results:
                        for i, item in enumerate(results, 1):
                            response_message += f"{i}. {item}\n"
                    else:
                        response_message += "No se encontraron resultados para esta búsqueda.\n"
                
                return jsonify({
                    'success': True,
                    'response': response_message,
                    'agent_id': agent_id,
                    'model': model
                })
            else:
                # Si hubo algún error en la exploración
                error_message = result.get('error', 'Error desconocido al explorar el repositorio')
                response_message = f"❌ No pude completar la exploración: {error_message}\n\n"
                
                # Sugerir acciones alternativas según el tipo de error
                if 'no existe' in error_message.lower():
                    response_message += "Posibles soluciones:\n"
                    response_message += "- Verifica el nombre del repositorio\n"
                    response_message += "- Asegúrate de haber clonado el repositorio primero\n"
                    response_message += "- Prueba a especificar la ruta correcta dentro del repositorio\n"
                
                return jsonify({
                    'success': False,
                    'error': response_message
                })
        
        if is_build_app:
            logger.info(f"Detectada intención de construir aplicación: '{instruction}'")
            
            # Detectar tipo de aplicación
            app_type = 'web'  # por defecto
            framework = 'flask'  # por defecto
            
            # Detectar frameworks/tecnologías mencionados
            tech_patterns = {
                'flask': r'(?:flask|python\s+web|aplicación\s+web\s+python|framework\s+(?:con|de)\s+flask|chatbot\s+(?:con|usando|basado\s+en)\s+flask|flask\s+framework)',
                'django': r'(?:django)',
                'react': r'(?:react|reactjs)',
                'vue': r'(?:vue|vuejs)',
                'angular': r'(?:angular)',
                'node': r'(?:node|nodejs)',
                'express': r'(?:express|expressjs)',
                'api': r'(?:api|rest\s+api|restful)',
                'web': r'(?:web|página|pagina|sitio|chatbot|aplicación)',
                'desktop': r'(?:desktop|escritorio)',
                'mobile': r'(?:mobile|móvil|movil|android|ios)'
            }
            
            for tech, pattern in tech_patterns.items():
                if re.search(pattern, instruction.lower()):
                    if tech in ['flask', 'django', 'react', 'vue', 'angular', 'node', 'express']:
                        framework = tech
                    if tech in ['web', 'api', 'desktop', 'mobile']:
                        app_type = tech
            
            # Extraer el nombre de la aplicación/proyecto
            app_name_patterns = [
                r'(?:llamad[oa]|nombrad[oa]|nombre|con\s+nombre|con\s+título)\s+["\']?([^"\']+)["\']?',
                r'(?:un|una)\s+(?:proyecto|aplicación|chatbot)\s+(?:llamad[oa]|nombrad[oa])\s+["\']?([^"\']+)["\']?',
                r'(?:proyecto|aplicación|chatbot|app)\s+["\']?([^"\']+)["\']?',
                r'(?:crea|construye|genera|desarrolla)\s+(?:una|un)?\s*(?:chatbot|bot)\s+(?:moderno|simple)?\s+(?:llamad[oa]|nombrad[oa])?\s+["\']?([^"\']+)["\']?'
            ]
            
            app_name = None
            for pattern in app_name_patterns:
                match = re.search(pattern, instruction)
                if match:
                    # Extraer el nombre y verificar que tenga sentido (no sea una frase completa)
                    potential_name = match.group(1).strip()
                    # Si el nombre tiene más de 3 palabras o más de 30 caracteres, probablemente no es un nombre válido
                    if len(potential_name.split()) <= 3 and len(potential_name) <= 30:
                        app_name = potential_name
                        break
            
            if not app_name:
                # Generar un nombre temático según el tipo de aplicación
                import time
                timestamp = int(time.time())
                
                if "chatbot" in instruction.lower():
                    app_name = f"chatbot_{timestamp}"
                elif "web" in instruction.lower():
                    app_name = f"webapp_{timestamp}"
                else:
                    app_name = f"{framework}_app_{timestamp}"
            
            # Validar el nombre del proyecto
            app_name = app_name.replace(' ', '_').replace('-', '_').lower()
                
            # Ejecutar comandos secuenciales para crear la aplicación según el framework
            commands = []
            result_messages = []
            
            # Crear directorio para la aplicación
            app_dir = os.path.join(workspace, app_name)
            os.makedirs(app_dir, exist_ok=True)
            result_messages.append(f"✅ Creado directorio para proyecto: {app_name}")
            
            # Scaffold específico según el framework
            if framework == 'flask':
                # Crear estructura básica de una aplicación Flask
                commands.append(f"cd {app_name} && touch app.py")
                commands.append(f"cd {app_name} && mkdir templates static")
                commands.append(f"cd {app_name} && mkdir static/css static/js static/images")
                commands.append(f"cd {app_name} && touch templates/index.html static/css/style.css static/js/main.js")
                commands.append(f"cd {app_name} && touch requirements.txt")
                
                # Crear contenido de app.py
                # Si es un chatbot, crear una aplicación específica de chatbot
                is_chatbot = "chatbot" in instruction.lower() or "bot" in instruction.lower()
                
                if is_chatbot:
                    app_py_content = """from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Historial de mensajes para mantener contexto
chat_history = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'Mensaje vacío'}), 400
    
    # Guardar mensaje del usuario
    chat_history.append({'role': 'user', 'content': message})
    
    # Generar respuesta (en una aplicación real, aquí se conectaría con un modelo de IA)
    response = generate_response(message)
    
    # Guardar respuesta del chatbot
    chat_history.append({'role': 'bot', 'content': response})
    
    return jsonify({
        'response': response,
        'history': chat_history[-10:]  # Devolver los últimos 10 mensajes
    })

def generate_response(message):
    # Lógica simple de respuesta (en una aplicación real se conectaría a OpenAI, etc.)
    message = message.lower()
    
    if 'hola' in message or 'saludos' in message:
        return '¡Hola! ¿En qué puedo ayudarte hoy?'
    elif 'ayuda' in message:
        return 'Estoy aquí para ayudarte. ¿Qué necesitas saber?'
    elif 'gracias' in message:
        return 'De nada, estoy para servirte.'
    elif '?' in message:
        return 'Buena pregunta. En una implementación real, conectaría esto con OpenAI o otro modelo de IA para darte una respuesta más precisa.'
    else:
        return 'Entiendo lo que dices. Para obtener mejores respuestas, conéctame con la API de OpenAI modificando el código de este chatbot.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
"""
                else:
                    app_py_content = """from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
"""
                with open(os.path.join(app_dir, "app.py"), "w") as f:
                    f.write(app_py_content)
                    
                # Crear contenido de index.html
                if is_chatbot:
                    index_html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chatbot Moderno</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <div class="row">
            <div class="col-md-8 mx-auto">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h3 class="mb-0">Chatbot Inteligente</h3>
                    </div>
                    <div class="card-body chat-container" id="chat-messages">
                        <div class="message bot-message">
                            <div class="message-content">
                                ¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?
                            </div>
                        </div>
                    </div>
                    <div class="card-footer">
                        <div class="input-group">
                            <input type="text" id="user-input" class="form-control" placeholder="Escribe tu mensaje aquí...">
                            <button class="btn btn-primary" id="send-button">Enviar</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
</body>
</html>"""
                else:
                    index_html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mi Aplicación Flask</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="container">
        <h1>Bienvenido a mi aplicación</h1>
        <p>Esta es una aplicación Flask creada con Codestorm Assistant.</p>
    </div>
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
</body>
</html>"""
                with open(os.path.join(app_dir, "templates", "index.html"), "w") as f:
                    f.write(index_html_content)
                    
                # Crear contenido de style.css
                style_css_content = """body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

h1 {
    color: #333;
}"""
                with open(os.path.join(app_dir, "static", "css", "style.css"), "w") as f:
                    f.write(style_css_content)
                    
                # Crear contenido de main.js
                if is_chatbot:
                    main_js_content = """document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    
    // Función para agregar mensajes al chat
    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = message;
        
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        
        // Scroll al final del chat
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Función para enviar mensaje al servidor
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Mostrar mensaje del usuario
        addMessage(message, true);
        
        // Limpiar input
        userInput.value = '';
        
        try {
            // Enviar mensaje al servidor
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            
            // Mostrar respuesta del chatbot
            addMessage(data.response);
        } catch (error) {
            console.error('Error:', error);
            addMessage('Lo siento, ha ocurrido un error al procesar tu mensaje.', false);
        }
    }
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Estilos CSS adicionales para los mensajes
    const style = document.createElement('style');
    style.textContent = `
        .chat-container {
            height: 300px;
            overflow-y: auto;
            padding: 15px;
        }
        
        .message {
            margin-bottom: 15px;
            display: flex;
        }
        
        .user-message {
            justify-content: flex-end;
        }
        
        .bot-message {
            justify-content: flex-start;
        }
        
        .message-content {
            max-width: 70%;
            padding: 10px 15px;
            border-radius: 15px;
            word-break: break-word;
        }
        
        .user-message .message-content {
            background-color: #007bff;
            color: white;
            border-bottom-right-radius: 0;
        }
        
        .bot-message .message-content {
            background-color: #f1f0f0;
            color: #333;
            border-bottom-left-radius: 0;
        }
    `;
    document.head.appendChild(style);
});"""
                else:
                    main_js_content = """document.addEventListener('DOMContentLoaded', function() {
    console.log('Aplicación cargada correctamente');
});"""
                with open(os.path.join(app_dir, "static", "js", "main.js"), "w") as f:
                    f.write(main_js_content)
                    
                # Crear requirements.txt
                requirements_content = """flask==3.1.0
gunicorn==23.0.0
"""
                with open(os.path.join(app_dir, "requirements.txt"), "w") as f:
                    f.write(requirements_content)
                    
                result_messages.append(f"✅ Creada estructura básica de Flask en '{app_name}'")
                result_messages.append(f"✅ Archivos creados: app.py, templates/index.html, static/css/style.css, static/js/main.js, requirements.txt")
                
            elif framework == 'node' or framework == 'express':
                # Crear estructura básica de una aplicación Node.js/Express
                commands.append(f"cd {app_name} && touch app.js package.json")
                commands.append(f"cd {app_name} && mkdir public views routes")
                commands.append(f"cd {app_name} && mkdir public/css public/js public/images")
                commands.append(f"cd {app_name} && touch public/css/style.css public/js/main.js")
                commands.append(f"cd {app_name} && touch views/index.html routes/index.js")
                
                # Crear package.json
                package_json_content = """{
  "name": "%s",
  "version": "1.0.0",
  "description": "Aplicación Node.js creada con Codestorm Assistant",
  "main": "app.js",
  "scripts": {
    "start": "node app.js",
    "dev": "nodemon app.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  },
  "devDependencies": {
    "nodemon": "^2.0.20"
  }
}""" % app_name
                with open(os.path.join(app_dir, "package.json"), "w") as f:
                    f.write(package_json_content)
                    
                # Crear app.js para Express
                app_js_content = """const express = require('express');
const path = require('path');
const indexRoutes = require('./routes/index');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Routes
app.use('/', indexRoutes);

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});"""
                with open(os.path.join(app_dir, "app.js"), "w") as f:
                    f.write(app_js_content)
                    
                # Crear routes/index.js
                routes_content = """const express = require('express');
const path = require('path');
const router = express.Router();

router.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../views/index.html'));
});

module.exports = router;"""
                with open(os.path.join(app_dir, "routes", "index.js"), "w") as f:
                    f.write(routes_content)
                    
                # Crear index.html
                index_html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mi Aplicación Node</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <div class="container">
        <h1>Bienvenido a mi aplicación</h1>
        <p>Esta es una aplicación Node.js creada con Codestorm Assistant.</p>
    </div>
    <script src="/js/main.js"></script>
</body>
</html>"""
                with open(os.path.join(app_dir, "views", "index.html"), "w") as f:
                    f.write(index_html_content)
                
                result_messages.append(f"✅ Creada estructura básica de Node.js en '{app_name}'")
                result_messages.append(f"✅ Archivos creados: app.js, package.json, routes/index.js, views/index.html")
                result_messages.append(f"Para iniciar el servidor, ejecuta: 'cd {app_name} && npm install && npm start'")
                
            elif framework == 'react':
                result_messages.append(f"✅ Para crear una aplicación React, se recomienda usar create-react-app.")
                result_messages.append(f"Ejecuta: 'npx create-react-app {app_name}' para crear una aplicación React completa.")
                
            # Ejecutar cada comando creado
            for command in commands:
                try:
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=workspace
                    )
                    stdout, stderr = process.communicate(timeout=30)
                    status = process.returncode
                    
                    if status != 0:
                        stderr_text = stderr.decode('utf-8', errors='replace')
                        logger.warning(f"Comando '{command}' terminó con código {status}. Stderr: {stderr_text}")
                        result_messages.append(f"⚠️ Advertencia al ejecutar '{command}': {stderr_text}")
                except Exception as e:
                    logger.error(f"Error ejecutando comando '{command}': {e}")
                    result_messages.append(f"⚠️ Error ejecutando '{command}': {str(e)}")
            
            # Instrucciones finales
            if framework == 'flask':
                result_messages.append("\n🚀 Para ejecutar la aplicación Flask:")
                result_messages.append(f"1. Navega al directorio: 'cd {app_name}'")
                result_messages.append("2. Instala las dependencias: 'pip install -r requirements.txt'")
                result_messages.append("3. Inicia el servidor: 'python app.py'")
                result_messages.append("4. Abre http://localhost:5000 en tu navegador")
            elif framework == 'node' or framework == 'express':
                result_messages.append("\n🚀 Para ejecutar la aplicación Node.js:")
                result_messages.append(f"1. Navega al directorio: 'cd {app_name}'")
                result_messages.append("2. Instala las dependencias: 'npm install'")
                result_messages.append("3. Inicia el servidor: 'npm start'")
                result_messages.append("4. Abre http://localhost:3000 en tu navegador")
            
            # Añadir recomendaciones para mejoras del proyecto usando el analizador
            try:
                # Analizar el proyecto recién creado
                project_path = os.path.join(workspace, app_name)
                recommendations = project_analyzer.get_next_steps(project_path)
                
                # Añadir las recomendaciones a la respuesta
                if recommendations:
                    result_messages.append("\n📋 Recomendaciones para mejorar tu proyecto:")
                    for i, recommendation in enumerate(recommendations[:7], 1):  # Mostrar máximo 7 recomendaciones
                        result_messages.append(f"{i}. {recommendation}")
                    
                    if len(recommendations) > 7:
                        result_messages.append(f"   ... y {len(recommendations) - 7} sugerencias más.")
                        
                    result_messages.append("\nEstas sugerencias te ayudarán a seguir las mejores prácticas y mejorar tu aplicación.")
            except Exception as e:
                logger.error(f"Error al generar recomendaciones: {str(e)}")
                # No mostramos el error al usuario, simplemente continuamos sin recomendaciones
                
            # Enviar resultado combinado
            return jsonify({
                'success': True,
                'command': f"Creación de aplicación {framework}: {app_name}",
                'result': '\n'.join(result_messages),
                'app_type': app_type,
                'framework': framework,
                'app_name': app_name
            })
        
        # CASO 2: Crear una carpeta/directorio
        # Patrones para detectar intención de crear una carpeta
        create_dir_patterns = [
            r'crea\s+(?:una|la)?\s*carpeta',
            r'crea\s+(?:un|el)?\s*directorio',
            r'crear\s+(?:una|la)?\s*carpeta',
            r'crear\s+(?:un|el)?\s*directorio',
            r'nueva\s+carpeta',
            r'nuevo\s+directorio',
            r'genera\s+(?:una|la)?\s*carpeta',
            r'hacer\s+(?:una|la)?\s*carpeta'
        ]
        
        is_create_dir = any(re.search(pattern, instruction.lower()) for pattern in create_dir_patterns)
        
        if is_create_dir:
            logger.info(f"Detectada intención de crear carpeta: '{instruction}'")
            
            # Buscar el nombre de la carpeta
            dirname_patterns = [
                r'(?:llamada|nombrada|nombre|con\s+nombre|con\s+título)\s+["\']?([^"\']+)["\']?',
                r'carpeta\s+["\']?([^"\']+)["\']?',
                r'directorio\s+["\']?([^"\']+)["\']?',
                r'crea\s+(?:una|la)?\s*carpeta\s+([a-zA-Z0-9_\-\.\/]+)',
                r'crea\s+(?:un|el)?\s*directorio\s+([a-zA-Z0-9_\-\.\/]+)'
            ]
            
            dirname = None
            for pattern in dirname_patterns:
                match = re.search(pattern, instruction)
                if match:
                    dirname = match.group(1).strip()
                    break
            
            if not dirname:
                # Si no se encuentra un nombre específico, crear uno genérico
                import time
                dirname = f"nueva_carpeta_{int(time.time())}"
            
            # Asegurarse de que no hay path traversal
            if '..' in dirname or dirname.startswith('/'):
                return jsonify({
                    'success': False,
                    'error': f"Nombre de directorio inválido: {dirname}"
                }), 400
            
            # Buscar directorio padre específico
            parent_dir_match = re.search(r'(?:en|dentro\s+de)\s+(?:la\s+carpeta|el\s+directorio)\s+["\']?([^"\']+)["\']?', instruction.lower())
            
            if parent_dir_match:
                parent_dir = parent_dir_match.group(1).strip()
                # Asegurarse de que no hay path traversal
                if '..' in parent_dir or parent_dir.startswith('/'):
                    return jsonify({
                        'success': False,
                        'error': f"Nombre de directorio inválido: {parent_dir}"
                    }), 400
                    
                dir_path = os.path.join(workspace, parent_dir, dirname)
            else:
                dir_path = os.path.join(workspace, dirname)
            
            # Crear la carpeta
            try:
                os.makedirs(dir_path, exist_ok=True)
                
                rel_path = os.path.relpath(dir_path, workspace)
                
                return jsonify({
                    'success': True,
                    'dir_path': rel_path,
                    'result': f"Se ha creado la carpeta '{rel_path}' correctamente."
                })
            except Exception as e:
                logger.error(f"Error al crear carpeta {dir_path}: {e}")
                return jsonify({
                    'success': False,
                    'error': f"Error al crear carpeta: {str(e)}"
                }), 500
            
        # CASO 3: Crear un archivo
        # Patrones para detectar intención de crear un archivo
        create_file_patterns = [
            r'crea\s+(?:un|el)?\s*archivo',
            r'crea\s+(?:un|el)?\s*fichero',
            r'crear\s+(?:un|el)?\s*archivo',
            r'crear\s+(?:un|el)?\s*fichero',
            r'nuevo\s+archivo',
            r'nuevo\s+fichero',
            r'genera\s+(?:un|el)?\s*archivo',
            r'hacer\s+(?:un|el)?\s*archivo'
        ]
        
        is_create_file = any(re.search(pattern, instruction.lower()) for pattern in create_file_patterns)
        
        if is_create_file:
            logger.info(f"Detectada intención de crear archivo: '{instruction}'")
            
            # Buscar el nombre del archivo
            filename_patterns = [
                r'(?:llamado|nombrado|nombre|con\s+nombre|con\s+título)\s+["\']?([^"\']+)["\']?',
                r'archivo\s+["\']?([^"\']+)["\']?',
                r'fichero\s+["\']?([^"\']+)["\']?',
                r'crea\s+(?:un|el)?\s*([a-zA-Z0-9_\.-]+\.[a-zA-Z0-9]+)',
                r'\s([a-zA-Z0-9_\.-]+\.[a-zA-Z0-9]+)'
            ]
            
            filename = None
            for pattern in filename_patterns:
                match = re.search(pattern, instruction)
                if match:
                    filename = match.group(1).strip()
                    break
            
            if not filename:
                # Si no se encuentra un nombre específico, crear uno genérico
                extension = '.txt'
                if 'html' in instruction.lower(): extension = '.html'
                elif 'css' in instruction.lower(): extension = '.css'
                elif 'javascript' in instruction.lower() or 'js' in instruction.lower(): extension = '.js'
                elif 'python' in instruction.lower() or 'py' in instruction.lower(): extension = '.py'
                
                filename = f"nuevo_archivo{extension}"
            
            # Añadir extensión si no tiene
            if '.' not in filename:
                if 'html' in instruction.lower(): filename += '.html'
                elif 'css' in instruction.lower(): filename += '.css'
                elif 'javascript' in instruction.lower() or 'js' in instruction.lower(): filename += '.js'
                elif 'python' in instruction.lower() or 'py' in instruction.lower(): filename += '.py'
                else: filename += '.txt'
            
            # Contenido básico según el tipo de archivo
            content = ""
            ext = filename.split('.')[-1].lower()
            
            if ext in ['html', 'htm']:
                content = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Nuevo documento</title>\n</head>\n<body>\n    <h1>Nuevo documento</h1>\n    <p>Contenido del documento.</p>\n</body>\n</html>"
            elif ext == 'css':
                content = "/* Estilos CSS */\nbody {\n    margin: 0;\n    padding: 0;\n    font-family: Arial, sans-serif;\n    background-color: #f0f0f0;\n    color: #333;\n}"
            elif ext == 'js':
                content = "// Archivo JavaScript\nconsole.log('Nuevo archivo JavaScript');\n\n// Función principal\nfunction main() {\n    console.log('Iniciando aplicación...');\n}\n\n// Ejecutar cuando el documento esté listo\ndocument.addEventListener('DOMContentLoaded', main);"
            elif ext == 'py':
                content = "# Archivo Python\n\ndef main():\n    '''\n    Función principal del programa\n    '''\n    print('Hola mundo')\n\nif __name__ == '__main__':\n    main()"
            elif ext == 'md':
                content = "# Título Principal\n\n## Subtítulo\n\nEste es un archivo Markdown de ejemplo.\n\n* Punto 1\n* Punto 2\n* Punto 3\n\n```python\nprint('Código de ejemplo')\n```"
            elif ext == 'json':
                content = "{\n    \"nombre\": \"Ejemplo\",\n    \"descripcion\": \"Este es un archivo JSON de ejemplo\",\n    \"atributos\": [\n        \"simple\",\n        \"básico\",\n        \"ejemplo\"\n    ],\n    \"version\": 1.0\n}"
            else:
                content = f"Este es un archivo de texto ({ext}) creado con Codestorm Assistant.\n\nPuedes editar este archivo para añadir tu propio contenido."
            
            # Buscar directorio específico
            dir_match = re.search(r'(?:en|dentro\s+de)\s+(?:la\s+carpeta|el\s+directorio)\s+["\']?([^"\']+)["\']?', instruction.lower())
            
            if dir_match:
                dir_name = dir_match.group(1).strip()
                # Asegurarse de que no hay path traversal
                if '..' in dir_name or dir_name.startswith('/'):
                    return jsonify({
                        'success': False,
                        'error': f"Nombre de directorio inválido: {dir_name}"
                    }), 400
                    
                file_path = os.path.join(workspace, dir_name, filename)
            else:
                file_path = os.path.join(workspace, filename)
            
            # Crear el archivo
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                rel_path = os.path.relpath(file_path, workspace)
                
                return jsonify({
                    'success': True,
                    'file_path': rel_path,
                    'content': content,
                    'result': f"Se ha creado el archivo '{rel_path}' con contenido básico para {ext.upper()}."
                })
            except Exception as e:
                logger.error(f"Error al crear archivo {file_path}: {e}")
                return jsonify({
                    'success': False,
                    'error': f"Error al crear archivo: {str(e)}"
                }), 500
        
        # Respuesta genérica para instrucciones no reconocidas
        logger.info(f"Instrucción no reconocida: '{instruction}'")
        return jsonify({
            'success': True,
            'result': f"He recibido tu instrucción: '{instruction}'. Puedo ayudarte con lo siguiente:\n\n"
                      "1) Para ejecutar un comando: comienza con 'ejecuta' o 'corre'.\n"
                      "2) Para crear un archivo: usa 'crea un archivo nombre.ext'.\n"
                      "3) Para crear una carpeta: usa 'crea una carpeta nombre'.\n"
                      "4) Para construir una aplicación: 'crea una aplicación [tipo]' (ej: Flask, Node, React).\n"
        })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Tiempo de ejecución agotado (30s)'
        }), 504
    except Exception as e:
        logger.error(f"Error al procesar instrucción: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Verificar estado
@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'message': 'Aplicación funcionando correctamente',
        'diagnostic_routes': ['health', 'api/test_apis']
    })

# Ruta de prueba de APIs
@app.route('/api/test_apis', methods=['GET'])
def test_apis():
    """Prueba las conexiones a las APIs de IA para diagnóstico."""
    results = {
        'status': 'testing',
        'apis': {
            'openai': {'status': 'unknown'},
            'anthropic': {'status': 'unknown'},
            'gemini': {'status': 'unknown'}
        }
    }
    
    # Verificar OpenAI
    openai_key = os.environ.get('OPENAI_API_KEY')
    if openai_key:
        try:
            logger.info("Probando conexión con OpenAI...")
            results['apis']['openai'] = {
                'status': 'configured',
                'message': 'API key configurada, pero no se prueba la conexión en esta versión simplificada'
            }
        except Exception as e:
            error_msg = str(e)
            results['apis']['openai'] = {
                'status': 'error',
                'message': error_msg[:100] + '...' if len(error_msg) > 100 else error_msg
            }
            logger.error(f"Error al verificar OpenAI: {error_msg}")
    else:
        results['apis']['openai'] = {
            'status': 'not_configured',
            'message': 'API key no configurada'
        }
    
    # Verificar Anthropic
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    if anthropic_key:
        results['apis']['anthropic'] = {
            'status': 'configured',
            'message': 'API key configurada, pero no se prueba la conexión en esta versión simplificada'
        }
    else:
        results['apis']['anthropic'] = {
            'status': 'not_configured',
            'message': 'API key no configurada'
        }
    
    # Verificar Gemini
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if gemini_key:
        results['apis']['gemini'] = {
            'status': 'configured',
            'message': 'API key configurada, pero no se prueba la conexión en esta versión simplificada'
        }
    else:
        results['apis']['gemini'] = {
            'status': 'not_configured',
            'message': 'API key no configurada'
        }
    
    # Agregar información sobre las rutas de chat
    results['chat_endpoints'] = {
        'handle_chat': '/api/chat',
        'generate_response': '/api/generate',
        'process_code': '/api/process_code'
    }
    
    return jsonify(results)

# Servir archivos estáticos
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Servir archivos estáticos desde el directorio static."""
    return send_from_directory('static', filename)

@app.route('/workspace/<path:filename>')
def serve_workspace_file(filename):
    """Servir archivos desde el workspace del usuario."""
    return send_from_directory('user_workspaces/default', filename)

# Esta ruta ya existe en otra parte del código, eliminamos esta duplicada

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)