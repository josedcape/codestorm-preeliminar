# Funciones para descarga de archivos y directorios
import os
import logging
import zipfile
import io
import shutil
import subprocess
from pathlib import Path
from flask import request, jsonify, send_file, session
import requests

def download_file_route(app, get_user_workspace):
    @app.route('/api/download_file/<path:file_path>')
    def download_file(file_path):
        """Download a single file from the workspace."""
        try:
            # Get the user workspace
            user_id = session.get('user_id', 'default')
            workspace_path = get_user_workspace(user_id)
            
            # Process the filepath to prevent directory traversal
            file_path = file_path.replace('..', '')
            target_path = (workspace_path / file_path).resolve()
            
            # Ensure we don't access anything outside the workspace
            if not str(target_path).startswith(str(workspace_path.resolve())):
                return jsonify({'error': 'Access denied: Cannot access files outside workspace'}), 403
                
            if not target_path.exists():
                return jsonify({'error': 'El archivo no existe'}), 404
                
            if target_path.is_dir():
                return jsonify({'error': 'No se puede descargar un directorio. Use la opción de descargar como ZIP'}), 400
            
            # Return the file for download
            return send_file(target_path, as_attachment=True)
            
        except Exception as e:
            logging.error(f"Error downloading file: {str(e)}")
            return jsonify({'error': str(e)}), 500

def download_directory_route(app, get_user_workspace):
    @app.route('/api/download_directory/<path:directory_path>')
    def download_directory(directory_path):
        """Download a directory as a ZIP file."""
        try:
            # Get the user workspace
            user_id = session.get('user_id', 'default')
            workspace_path = get_user_workspace(user_id)
            
            # Process the filepath to prevent directory traversal
            directory_path = directory_path.replace('..', '')
            target_path = (workspace_path / directory_path).resolve()
            
            # Ensure we don't access anything outside the workspace
            if not str(target_path).startswith(str(workspace_path.resolve())):
                return jsonify({'error': 'Access denied: Cannot access directories outside workspace'}), 403
                
            if not target_path.exists() or not target_path.is_dir():
                return jsonify({'error': 'El directorio no existe'}), 404
                
            # Create an in-memory ZIP file
            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Walk through the directory and add all files
                base_dir_name = target_path.name
                base_path = target_path.parent
                
                for root, dirs, files in os.walk(target_path):
                    # Get the relative path from the base directory
                    rel_path = os.path.relpath(root, base_path)
                    
                    # Add each file to the ZIP
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.join(rel_path, file)
                        zipf.write(file_path, arc_name)
            
            # Reset file pointer to beginning
            memory_file.seek(0)
            
            # Create a filename for the ZIP
            zip_filename = f"{base_dir_name}.zip"
            
            # Send the ZIP file
            return send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name=zip_filename
            )
            
        except Exception as e:
            logging.error(f"Error downloading directory: {str(e)}")
            return jsonify({'error': str(e)}), 500

def clone_repository_route(app, get_user_workspace, socketio):
    @app.route('/api/clone_repository', methods=['POST'])
    def clone_repository():
        """Clone a Git repository into the user workspace."""
        try:
            data = request.json
            repo_url = data.get('repo_url')
            
            if not repo_url:
                return jsonify({'error': 'No se proporcionó la URL del repositorio'}), 400
                
            # Get the user workspace
            user_id = session.get('user_id', 'default')
            workspace_path = get_user_workspace(user_id)
            
            # Extract repo name from URL
            repo_name = repo_url.split('/')[-1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
                
            target_path = workspace_path / repo_name
            
            # Check if directory already exists
            if target_path.exists():
                return jsonify({'error': f'Ya existe un directorio con el nombre {repo_name}'}), 400
                
            # Clone the repository using subprocess instead of GitPython
            try:
                process = subprocess.Popen(
                    ["git", "clone", repo_url, str(target_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(timeout=60)
                
                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8', errors='replace')
                    return jsonify({'error': f'Error al clonar el repositorio: {error_msg}'}), 500
            except Exception as e:
                return jsonify({'error': f'Error al clonar el repositorio: {str(e)}'}), 500
                
            # Notify clients
            file_data = {
                'path': repo_name,
                'name': repo_name,
                'type': 'directory'
            }
            socketio.emit('file_created', file_data, room=user_id)
            
            return jsonify({
                'success': True, 
                'message': f'Repositorio clonado correctamente en {repo_name}',
                'repo_path': repo_name
            })
            
        except Exception as e:
            logging.error(f"Error cloning repository: {str(e)}")
            return jsonify({'error': str(e)}), 500

def register_download_routes(app, get_user_workspace, socketio):
    """Register all download related routes."""
    download_file_route(app, get_user_workspace)
    download_directory_route(app, get_user_workspace)
    clone_repository_route(app, get_user_workspace, socketio)