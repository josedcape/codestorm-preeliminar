import os
import logging
import subprocess
from flask import Flask, request, jsonify
from pathlib import Path

# Configuración de logging
logging.basicConfig(level=logging.INFO)

# Crear aplicación Flask
app = Flask(__name__)

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
    # Para desarrollo local, se puede ejecutar directamente
    app.run(host='0.0.0.0', port=5001, debug=True)