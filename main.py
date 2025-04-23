"""
Punto de entrada principal para la aplicación Codestorm Assistant.
Este archivo configura la aplicación Flask y registra todas las rutas.
"""

import os
import logging
from flask import Flask, render_template #Added flask import
from routes_analyzer import register_analyzer_routes
from document_routes import register_document_routes
from github_routes import register_github_routes
from file_explorer_routes import register_file_explorer_routes
from constructor_routes import init_constructor_routes
from simple_test import app, get_user_workspace

# Configurar logging para este módulo
logger = logging.getLogger(__name__)

# Crear carpetas necesarias para la aplicación
os.makedirs('user_workspaces/context_documents', exist_ok=True)

# Registrar las rutas del analizador de proyectos
register_analyzer_routes(app, get_user_workspace)

# Registrar las rutas para manejo de documentos
try:
    register_document_routes(app)
    logger.info("Rutas de documentos registradas correctamente")
except Exception as e:
    logger.error(f"Error al registrar rutas de documentos: {str(e)}")

# Registrar las rutas para manejo de repositorios GitHub
try:
    register_github_routes(app)
    logger.info("Rutas de GitHub registradas correctamente")
except Exception as e:
    logger.error(f"Error al registrar rutas de GitHub: {str(e)}")

# Registrar las rutas para exploración de archivos
try:
    register_file_explorer_routes(app)
    logger.info("Rutas de exploración de archivos registradas correctamente")
except Exception as e:
    logger.error(f"Error al registrar rutas de exploración de archivos: {str(e)}")

# Registrar las rutas para el Constructor de Tareas
try:
    init_constructor_routes(app)
    logger.info("Rutas del Constructor de Tareas registradas correctamente")
except Exception as e:
    logger.error(f"Error al registrar rutas del Constructor de Tareas: {str(e)}")

#Added code corrector routes.  Assumed these functions are defined elsewhere and accessible to app.
@app.route('/code_corrector')
def code_corrector():
    """Render the code corrector page."""
    return render_template('code_corrector.html')

@app.route('/code_corrector/')
def code_corrector_slash():
    """Redirect to ensure both with and without trailing slash work."""
    return render_template('code_corrector.html')


# Solo ejecutar la aplicación si este archivo es el punto de entrada
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)