"""
Módulo para rutas de análisis de proyectos en Codestorm Assistant.
Este módulo proporciona endpoints para analizar proyectos y generar recomendaciones.
"""

import os
import json
import logging
from flask import jsonify, request
import project_analyzer

logger = logging.getLogger(__name__)

def register_analyzer_routes(app, get_workspace_fn):
    """
    Registra las rutas de análisis de proyectos en la aplicación Flask.
    
    Args:
        app: La aplicación Flask
        get_workspace_fn: Función para obtener el workspace del usuario
    """
    
    @app.route('/api/analyze_project', methods=['GET'])
    def api_analyze_project():
        """
        API para analizar la estructura de un proyecto y obtener recomendaciones.
        
        Parámetros:
            - project_path: Ruta al proyecto a analizar (relativa al workspace)
            - user_id: ID del usuario
        
        Retorna:
            - project_type: Tipo de proyecto detectado
            - recommendations: Lista de recomendaciones
            - missing_files: Lista de archivos que faltan
            - files: Lista de archivos encontrados
        """
        try:
            project_path = request.args.get('project_path', '.')
            user_id = request.args.get('user_id', 'default')
            
            workspace = get_workspace_fn(user_id)
            
            # Normalizar y verificar la ruta del proyecto
            if project_path.startswith('/'):
                project_path = project_path[1:]
            
            target_path = os.path.normpath(os.path.join(workspace, project_path))
            
            # Verificar que la ruta está dentro del workspace
            if not target_path.startswith(os.path.normpath(workspace)):
                logger.warning(f"Intento de acceso a directorio fuera del workspace: {project_path}")
                return jsonify({
                    'success': False,
                    'error': 'Ruta inválida'
                }), 400
            
            # Verificar que el directorio existe
            if not os.path.exists(target_path) or not os.path.isdir(target_path):
                return jsonify({
                    'success': False,
                    'error': f"La ruta {project_path} no existe o no es un directorio"
                }), 404
            
            # Analizar el proyecto
            analysis = project_analyzer.analyze_project_structure(target_path)
            next_steps = project_analyzer.get_next_steps(target_path)
            
            # Añadir los siguientes pasos a la respuesta
            analysis['next_steps'] = next_steps
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Error al analizar proyecto: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
            
    @app.route('/api/get_recommendations', methods=['GET'])
    def api_get_recommendations():
        """
        API para obtener recomendaciones de desarrollo para un proyecto.
        
        Parámetros:
            - project_path: Ruta al proyecto (relativa al workspace)
            - user_id: ID del usuario
        
        Retorna:
            - recommendations: Lista de recomendaciones
        """
        try:
            project_path = request.args.get('project_path', '.')
            user_id = request.args.get('user_id', 'default')
            
            workspace = get_workspace_fn(user_id)
            
            # Normalizar y verificar la ruta del proyecto
            if project_path.startswith('/'):
                project_path = project_path[1:]
                
            target_path = os.path.normpath(os.path.join(workspace, project_path))
            
            # Verificar que la ruta está dentro del workspace
            if not target_path.startswith(os.path.normpath(workspace)):
                logger.warning(f"Intento de acceso a directorio fuera del workspace: {project_path}")
                return jsonify({
                    'success': False,
                    'error': 'Ruta inválida'
                }), 400
                
            # Verificar que el directorio existe
            if not os.path.exists(target_path) or not os.path.isdir(target_path):
                return jsonify({
                    'success': False,
                    'error': f"La ruta {project_path} no existe o no es un directorio"
                }), 404
                
            # Obtener recomendaciones
            next_steps = project_analyzer.get_next_steps(target_path)
            
            return jsonify({
                'success': True,
                'recommendations': next_steps
            })
            
        except Exception as e:
            logger.error(f"Error al obtener recomendaciones: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500