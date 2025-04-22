import os
import logging
import subprocess
from flask import Flask, request, jsonify, render_template_string
from pathlib import Path

# Configuración de logging
logging.basicConfig(level=logging.INFO)

# Crear aplicación Flask
app = Flask(__name__)

@app.route('/')
def home():
    """Página de inicio simple."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Codestorm Assistant - API Simplificada</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #0c1729;
                color: #e0e0e0;
            }
            h1 {
                color: #f5cc7f;
                border-bottom: 1px solid #f5cc7f;
                padding-bottom: 10px;
            }
            h2 {
                color: #7fccf5;
                margin-top: 30px;
            }
            pre {
                background-color: #1c2739;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
            }
            .endpoint {
                border-left: 3px solid #7fccf5;
                padding-left: 15px;
                margin: 20px 0;
            }
            code {
                background-color: #1c2739;
                padding: 2px 5px;
                border-radius: 3px;
                font-family: monospace;
            }
            .method {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 3px;
                margin-right: 10px;
                font-weight: bold;
            }
            .get {
                background-color: #4CAF50;
                color: white;
            }
            .post {
                background-color: #2196F3;
                color: white;
            }
        </style>
    </head>
    <body>
        <h1>Codestorm Assistant - API Simplificada</h1>
        
        <p>Esta es una versión simplificada de la API de Codestorm Assistant que proporciona
        funcionalidades básicas para ejecutar comandos y gestionar archivos.</p>
        
        <h2>Endpoints Disponibles</h2>
        
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/execute_command</h3>
            <p>Ejecuta un comando en la terminal.</p>
            <p><strong>Ejemplo de solicitud:</strong></p>
            <pre>
{
  "command": "ls -la"
}
            </pre>
        </div>
        
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/create_file</h3>
            <p>Crea un archivo con el contenido especificado.</p>
            <p><strong>Ejemplo de solicitud:</strong></p>
            <pre>
{
  "file_path": "example.html",
  "content": "&lt;!DOCTYPE html&gt;\\n&lt;html&gt;\\n&lt;head&gt;\\n    &lt;title&gt;Example&lt;/title&gt;\\n&lt;/head&gt;\\n&lt;body&gt;\\n    &lt;h1&gt;Hello World&lt;/h1&gt;\\n&lt;/body&gt;\\n&lt;/html&gt;"
}
            </pre>
        </div>
        
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/list_files</h3>
            <p>Lista todos los archivos en el workspace.</p>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/health')
def health():
    """Health check route for deployment."""
    return "OK"

@app.route('/api/execute_command', methods=['POST'])
def execute_command_api():
    """API simple para ejecutar comandos directamente."""
    try:
        data = request.json
        command = data.get('command', '')
        
        if not command:
            return jsonify({'error': 'No command provided'}), 400
            
        # Ejecutar el comando
        workspace_path = Path('user_workspaces/default')
        if not workspace_path.exists():
            workspace_path.mkdir(parents=True, exist_ok=True)
            
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(workspace_path)
        )
        
        # Obtener stdout y stderr
        stdout, stderr = process.communicate(timeout=30)
        status = process.returncode
        
        return jsonify({
            'success': status == 0,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
            'status': status
        })
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'Command execution timed out (30s)'
        }), 500
    except Exception as e:
        logging.error(f"Error executing command: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/create_file', methods=['POST'])
def create_file_api():
    """API simple para crear archivos."""
    try:
        data = request.json
        file_path = data.get('file_path', '')
        content = data.get('content', '')
        
        if not file_path:
            return jsonify({'error': 'No file path provided'}), 400
            
        # Crear archivo
        workspace_path = Path('user_workspaces/default')
        if not workspace_path.exists():
            workspace_path.mkdir(parents=True, exist_ok=True)
            
        target_file = (workspace_path / file_path).resolve()
        
        # Verificar path traversal
        if not str(target_file).startswith(str(workspace_path.resolve())):
            return jsonify({
                'success': False,
                'message': 'Access denied: Cannot access files outside workspace'
            }), 403
            
        # Crear directorios si no existen
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Escribir el archivo
        with open(target_file, 'w') as f:
            f.write(content)
            
        return jsonify({
            'success': True,
            'message': f'File {file_path} created successfully'
        })
    except Exception as e:
        logging.error(f"Error creating file: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/list_files', methods=['GET'])
def list_files_api():
    """API simple para listar archivos del workspace."""
    try:
        workspace_path = Path('user_workspaces/default')
        if not workspace_path.exists():
            workspace_path.mkdir(parents=True, exist_ok=True)
            
        files = []
        for item in workspace_path.glob('**/*'):
            if item.is_file():
                files.append({
                    'path': str(item.relative_to(workspace_path)),
                    'size': item.stat().st_size,
                    'is_dir': False
                })
            elif item.is_dir():
                files.append({
                    'path': str(item.relative_to(workspace_path)),
                    'is_dir': True
                })
                
        return jsonify({
            'success': True,
            'files': files
        })
    except Exception as e:
        logging.error(f"Error listing files: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
            
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)