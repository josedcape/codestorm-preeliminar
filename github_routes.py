"""
Rutas para el manejo de repositorios de GitHub en el asistente.
Proporciona funcionalidades para clonar repositorios completos.
"""

import os
import logging
from flask import Blueprint, jsonify, request
import github_repo_manager

# Configurar el logger
logger = logging.getLogger(__name__)

# Crear un Blueprint para las rutas de GitHub
github_bp = Blueprint('github', __name__)

@github_bp.route('/api/github/clone', methods=['POST'])
def clone_github_repository():
    """
    Clona un repositorio de GitHub en el workspace del usuario.
    
    Espera:
    - repo_url: URL del repositorio a clonar
    - branch: Rama específica (opcional)
    - user_id: ID del usuario (opcional)
    
    Retorna:
    - Información sobre el repositorio clonado
    """
    try:
        data = request.json
        repo_url = data.get('repo_url')
        branch = data.get('branch')
        user_id = data.get('user_id', 'default')
        
        if not repo_url:
            return jsonify({
                'success': False,
                'error': 'No se ha proporcionado una URL de repositorio'
            }), 400
            
        # Crear directorio para los repositorios del usuario
        workspace_dir = os.path.join('user_workspaces', user_id)
        os.makedirs(workspace_dir, exist_ok=True)
        
        # Clonar el repositorio
        result = github_repo_manager.clone_github_repository(repo_url, workspace_dir, branch)
        
        if not result['success']:
            return jsonify(result), 400
            
        # Analizar repositorio clonado para obtener información
        repo_info = github_repo_manager.analyze_github_repository(result['path'])
        
        if not repo_info['success']:
            return jsonify(repo_info), 500
            
        # Combinar resultados
        response = {
            'success': True,
            'message': result['message'],
            'repo_path': result['path'],
            'repo_name': result['repo_name'],
            'repo_info': repo_info
        }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error al clonar repositorio de GitHub: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error al procesar la solicitud: {str(e)}"
        }), 500


@github_bp.route('/api/github/delete', methods=['DELETE'])
def delete_github_repository():
    """
    Elimina un repositorio GitHub previamente clonado.
    
    Espera:
    - repo_path: Ruta al repositorio clonado
    - user_id: ID del usuario (opcional)
    
    Retorna:
    - Resultado de la operación
    """
    try:
        data = request.json
        repo_path = data.get('repo_path')
        user_id = data.get('user_id', 'default')
        
        if not repo_path:
            return jsonify({
                'success': False,
                'error': 'No se ha proporcionado una ruta de repositorio'
            }), 400
            
        # Validar que la ruta está dentro del workspace del usuario
        workspace_dir = os.path.join('user_workspaces', user_id)
        if not repo_path.startswith(workspace_dir):
            repo_path = os.path.join(workspace_dir, repo_path)
            
        # Eliminar el repositorio
        result = github_repo_manager.delete_github_repository(repo_path)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error al eliminar repositorio de GitHub: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error al procesar la solicitud: {str(e)}"
        }), 500


@github_bp.route('/api/github/analyze', methods=['POST'])
def analyze_github_repository():
    """
    Analiza un repositorio GitHub clonado.
    
    Espera:
    - repo_path: Ruta al repositorio clonado
    - user_id: ID del usuario (opcional)
    
    Retorna:
    - Información detallada sobre el repositorio
    """
    try:
        data = request.json
        repo_path = data.get('repo_path')
        user_id = data.get('user_id', 'default')
        
        if not repo_path:
            return jsonify({
                'success': False,
                'error': 'No se ha proporcionado una ruta de repositorio'
            }), 400
            
        # Validar que la ruta está dentro del workspace del usuario
        workspace_dir = os.path.join('user_workspaces', user_id)
        if not repo_path.startswith(workspace_dir):
            repo_path = os.path.join(workspace_dir, repo_path)
            
        # Analizar el repositorio
        result = github_repo_manager.analyze_github_repository(repo_path)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error al analizar repositorio de GitHub: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error al procesar la solicitud: {str(e)}"
        }), 500


def register_github_routes(app):
    """Registra las rutas de GitHub en la aplicación Flask."""
    app.register_blueprint(github_bp)