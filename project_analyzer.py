"""
Analizador de proyectos para Codestorm Assistant.
Este módulo proporciona funciones para analizar proyectos y generar recomendaciones útiles.
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def analyze_project_structure(project_path):
    """
    Analiza la estructura de un proyecto y devuelve información sobre su tipo y estado.
    
    Args:
        project_path: Ruta al directorio del proyecto
        
    Returns:
        dict: Información del proyecto incluyendo tipo, archivos presentes y recomendaciones
    """
    # Obtener lista de archivos en el proyecto
    files = []
    for root, dirs, filenames in os.walk(project_path):
        # Eliminar directorios que queremos ignorar
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'venv' and d != 'node_modules' and d != '__pycache__']
        
        for filename in filenames:
            if not filename.startswith('.'):
                rel_path = os.path.relpath(os.path.join(root, filename), project_path)
                files.append(rel_path)
    
    # Detectar tipo de proyecto
    project_type = detect_project_type(files, project_path)
    
    # Analizar según el tipo de proyecto
    if project_type == 'flask':
        return analyze_flask_project(files, project_path)
    elif project_type == 'node':
        return analyze_node_project(files, project_path)
    elif project_type == 'react':
        return analyze_react_project(files, project_path)
    else:
        # Para proyectos desconocidos, devolver información básica
        return {
            'project_type': 'unknown',
            'files': files,
            'recommendations': [
                'No se pudo determinar el tipo de proyecto.',
                'Considera añadir archivos de configuración estándar como package.json o requirements.txt.',
                'Si es un proyecto web, añade un archivo index.html o app.py.'
            ],
            'missing_files': []
        }

def detect_project_type(files, project_path):
    """
    Detecta el tipo de proyecto basado en los archivos presentes.
    
    Args:
        files: Lista de archivos en el proyecto
        project_path: Ruta al directorio del proyecto
        
    Returns:
        str: Tipo de proyecto (flask, node, react, unknown)
    """
    # Check for Flask/Python project
    if any('app.py' in f for f in files) or any('requirements.txt' in f for f in files) or any(f.endswith('.py') for f in files):
        return 'flask'
    
    # Check for Node.js project
    if any('package.json' in f for f in files):
        # Check if it's a React project
        if any('react' in f.lower() for f in files) or any('jsx' in f.lower() for f in files):
            return 'react'
        return 'node'
    
    # More types can be added as needed
    return 'unknown'

def analyze_flask_project(files, project_path):
    """
    Analiza un proyecto Flask y genera recomendaciones.
    
    Args:
        files: Lista de archivos en el proyecto
        project_path: Ruta al directorio del proyecto
        
    Returns:
        dict: Información y recomendaciones del proyecto Flask
    """
    missing_files = []
    recommendations = []
    
    # Verificar archivos clave
    if not any('app.py' in f for f in files) and not any('main.py' in f for f in files):
        missing_files.append('app.py o main.py (archivo principal)')
        recommendations.append('Crea un archivo principal (app.py o main.py) para iniciar tu aplicación Flask.')
    
    if not any('requirements.txt' in f for f in files):
        missing_files.append('requirements.txt')
        recommendations.append('Añade un archivo requirements.txt para gestionar las dependencias del proyecto.')
    
    if not any(os.path.join('templates', '') in f for f in files):
        missing_files.append('carpeta templates/')
        recommendations.append('Crea una carpeta templates/ para almacenar tus plantillas HTML.')
    
    if not any(os.path.join('static', '') in f for f in files):
        missing_files.append('carpeta static/')
        recommendations.append('Crea una carpeta static/ para recursos estáticos (CSS, JS, imágenes).')
    
    # Verificar si hay modelos o una base de datos
    has_models = any('models.py' in f for f in files)
    has_database = any('database.py' in f for f in files) or any('db.py' in f for f in files)
    
    if not has_models and not has_database:
        recommendations.append('Considera añadir modelos y configuración de base de datos si tu aplicación lo requiere.')
    
    # Verificar estructura de pruebas
    if not any('test_' in f for f in files) and not any('tests/' in f for f in files):
        missing_files.append('pruebas unitarias (tests)')
        recommendations.append('Añade pruebas unitarias para validar la funcionalidad de tu aplicación.')
    
    # Verificar archivo de configuración
    if not any('config.py' in f for f in files):
        missing_files.append('config.py')
        recommendations.append('Crea un archivo config.py para gestionar la configuración de tu aplicación.')
    
    # Verificar si hay un archivo .env
    if not any('.env' in f for f in files):
        missing_files.append('.env')
        recommendations.append('Usa un archivo .env para almacenar variables de entorno sensibles.')
    
    return {
        'project_type': 'flask',
        'files': files,
        'recommendations': recommendations,
        'missing_files': missing_files
    }

def analyze_node_project(files, project_path):
    """
    Analiza un proyecto Node.js y genera recomendaciones.
    
    Args:
        files: Lista de archivos en el proyecto
        project_path: Ruta al directorio del proyecto
        
    Returns:
        dict: Información y recomendaciones del proyecto Node.js
    """
    missing_files = []
    recommendations = []
    
    # Verificar archivos clave
    if not any('package.json' in f for f in files):
        missing_files.append('package.json')
        recommendations.append('Crea un archivo package.json para gestionar las dependencias del proyecto.')
    
    if not any('index.js' in f for f in files) and not any('server.js' in f for f in files) and not any('app.js' in f for f in files):
        missing_files.append('archivo principal (index.js, server.js o app.js)')
        recommendations.append('Crea un archivo principal para iniciar tu aplicación Node.js.')
    
    # Verificar estructura de carpetas
    if not any(os.path.join('public', '') in f for f in files):
        missing_files.append('carpeta public/')
        recommendations.append('Crea una carpeta public/ para recursos estáticos (HTML, CSS, JS, imágenes).')
    
    if not any(os.path.join('routes', '') in f for f in files):
        missing_files.append('carpeta routes/')
        recommendations.append('Organiza tus rutas en una carpeta routes/ para mejor estructura.')
    
    # Verificar configuración
    if not any('.env' in f for f in files):
        missing_files.append('.env')
        recommendations.append('Usa un archivo .env para almacenar variables de entorno sensibles.')
    
    # Verificar estructura de pruebas
    if not any('test' in f for f in files) and not any('tests/' in f for f in files):
        missing_files.append('pruebas unitarias (tests)')
        recommendations.append('Añade pruebas unitarias para validar la funcionalidad de tu aplicación.')
    
    return {
        'project_type': 'node',
        'files': files,
        'recommendations': recommendations,
        'missing_files': missing_files
    }

def analyze_react_project(files, project_path):
    """
    Analiza un proyecto React y genera recomendaciones.
    
    Args:
        files: Lista de archivos en el proyecto
        project_path: Ruta al directorio del proyecto
        
    Returns:
        dict: Información y recomendaciones del proyecto React
    """
    missing_files = []
    recommendations = []
    
    # Verificar archivos clave
    if not any('package.json' in f for f in files):
        missing_files.append('package.json')
        recommendations.append('Crea un archivo package.json para gestionar las dependencias del proyecto.')
    
    if not any(os.path.join('src', 'App.js') in f or os.path.join('src', 'App.jsx') in f for f in files):
        missing_files.append('src/App.js o src/App.jsx')
        recommendations.append('Crea un componente App.js principal en la carpeta src/.')
    
    if not any(os.path.join('public', 'index.html') in f for f in files):
        missing_files.append('public/index.html')
        recommendations.append('Añade un archivo index.html en la carpeta public/.')
    
    # Verificar estructura de componentes
    if not any(os.path.join('src', 'components', '') in f for f in files):
        missing_files.append('carpeta src/components/')
        recommendations.append('Organiza tus componentes en una carpeta src/components/ para mejor estructura.')
    
    # Verificar configuración de rutas
    has_router = False
    if any('package.json' in f for f in files):
        try:
            with open(os.path.join(project_path, 'package.json'), 'r') as f:
                package_data = json.load(f)
                dependencies = package_data.get('dependencies', {})
                if 'react-router-dom' in dependencies:
                    has_router = True
        except Exception as e:
            logger.error(f"Error al leer package.json: {e}")
    
    if not has_router:
        recommendations.append('Considera añadir react-router-dom para gestionar la navegación en tu aplicación.')
    
    # Verificar estado global
    has_redux = False
    has_context = any('context' in f.lower() for f in files)
    
    if any('package.json' in f for f in files):
        try:
            with open(os.path.join(project_path, 'package.json'), 'r') as f:
                package_data = json.load(f)
                dependencies = package_data.get('dependencies', {})
                if 'redux' in dependencies or 'react-redux' in dependencies:
                    has_redux = True
        except Exception as e:
            logger.error(f"Error al leer package.json: {e}")
    
    if not has_redux and not has_context:
        recommendations.append('Considera implementar un sistema de gestión de estado (Redux o Context API).')
    
    return {
        'project_type': 'react',
        'files': files,
        'recommendations': recommendations,
        'missing_files': missing_files
    }

def get_next_steps(project_path):
    """
    Genera sugerencias de próximos pasos para continuar desarrollando el proyecto.
    
    Args:
        project_path: Ruta al directorio del proyecto
        
    Returns:
        list: Lista de sugerencias para los próximos pasos
    """
    project_info = analyze_project_structure(project_path)
    project_type = project_info.get('project_type', 'unknown')
    recommendations = []
    
    # Sugerencias genéricas para cualquier proyecto
    recommendations.append('Revisa y completa la documentación del proyecto.')
    recommendations.append('Asegúrate de que el código sigue buenas prácticas y estándares de codificación.')
    
    # Recomendaciones para configuración inicial y archivos frontend según tipo de proyecto
    if project_type == 'flask':
        # Verificar configuración
        if not any(f == 'config.py' or f == '.env' for f in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, f))):
            recommendations.append('Crea un archivo config.py con las configuraciones de desarrollo, prueba y producción.')
            recommendations.append('Configura un archivo .env para variables de entorno sensibles (claves API, configuración DB).')
        
        # Archivos de estilo/frontend
        if not os.path.exists(os.path.join(project_path, 'static', 'css')):
            recommendations.append('Crea una estructura de carpetas para estilos en static/css/ con archivos style.css y normalize.css.')
            recommendations.append('Considera implementar Bootstrap o Tailwind CSS para un diseño responsive.')
        
        recommendations.append('Configura el manejo de errores y páginas 404 personalizadas.')
        recommendations.append('Implementa autenticación y autorización de usuarios si es necesario.')
        recommendations.append('Añade validación de formularios y datos de entrada.')
        recommendations.append('Optimiza las consultas a la base de datos para mejorar el rendimiento.')
        recommendations.append('Configura un sistema de migraciones para la base de datos.')
        recommendations.append('Crea plantillas base.html y layout.html para mantener consistencia visual.')
        
    elif project_type == 'node':
        # Verificar configuración
        if not any(f == '.env' or f == 'config.js' for f in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, f))):
            recommendations.append('Crea un archivo config.js para diferentes entornos (dev, test, production).')
            recommendations.append('Configura dotenv para cargar variables de entorno desde un archivo .env.')
        
        # Archivos de estilo/frontend
        if not os.path.exists(os.path.join(project_path, 'public', 'css')):
            recommendations.append('Crea una estructura para archivos estáticos en public/css/ con main.css y reset.css.')
            recommendations.append('Implementa una solución CSS como Bootstrap, Bulma o Tailwind para una UI profesional.')
        
        recommendations.append('Implementa un sistema de logging para monitorear la aplicación.')
        recommendations.append('Configura middleware para manejar autenticación y autorización.')
        recommendations.append('Añade validación de datos en los endpoints de la API.')
        recommendations.append('Considera implementar documentación de la API con Swagger o similar.')
        recommendations.append('Optimiza las consultas a la base de datos y usa pooling de conexiones.')
        recommendations.append('Implementa plantillas EJS o Pug si necesitas renderizar vistas en el servidor.')
        
    elif project_type == 'react':
        # Verificar configuración
        if not any(f == '.env' or f == '.env.development' for f in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, f))):
            recommendations.append('Crea archivos .env.development y .env.production para variables de entorno según el entorno.')
            recommendations.append('Configura un archivo jsconfig.json o tsconfig.json para mejorar la experiencia de desarrollo.')
        
        # Archivos de estilo/frontend
        css_approaches = ['styled-components', 'emotion', 'tailwind', 'css modules']
        has_css_approach = False
        
        try:
            if os.path.exists(os.path.join(project_path, 'package.json')):
                with open(os.path.join(project_path, 'package.json'), 'r') as f:
                    package_data = json.load(f)
                    dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
                    has_css_approach = any(css in dependencies for css in css_approaches)
        except Exception:
            pass
            
        if not has_css_approach:
            recommendations.append('Implementa una librería de estilos como styled-components, emotion o tailwind.')
            recommendations.append('Establece un sistema de diseño con variables CSS para colores, espaciado y tipografía.')
        
        recommendations.append('Crea un directorio src/styles/ para guardar variables de tema, mixins y estilos globales.')
        recommendations.append('Implementa pruebas de componentes con React Testing Library o Jest.')
        recommendations.append('Optimiza el rendimiento usando React.memo o useMemo donde sea apropiado.')
        recommendations.append('Implementa lazy loading para componentes grandes o rutas menos usadas.')
        recommendations.append('Añade soporte para temas o modo oscuro.')
        recommendations.append('Considera usar TypeScript para mejorar la robustez del código.')
    
    # Sugerencias comunes para proyectos web
    if project_type in ['flask', 'node', 'react']:
        recommendations.append('Implementa pruebas automatizadas y configuración CI/CD.')
        recommendations.append('Configura linting y formateo automático del código.')
        recommendations.append('Añade soporte para internacionalización si es necesario.')
        recommendations.append('Optimiza para dispositivos móviles y asegura la accesibilidad.')
        recommendations.append('Implementa un sistema de componentes reutilizables para la interfaz de usuario.')
        recommendations.append('Añade un favicon.ico y configura los metadatos Open Graph para compartir en redes sociales.')
    
    return recommendations