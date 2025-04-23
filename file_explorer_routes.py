"""
Rutas API para la exploración y manipulación de archivos dentro de repositorios.
Permite al asistente principal explorar, leer y modificar archivos específicos
dentro de una estructura de directorios.
"""

import os
import logging
import json
from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename
import file_explorer
import tempfile
import shutil

logger = logging.getLogger(__name__)

# Crear el blueprint para las rutas de exploración de archivos
file_explorer_bp = Blueprint('file_explorer', __name__)

@file_explorer_bp.route('/api/explorer/list', methods=['GET'])
def list_directory():
    """
    Lista archivos y directorios en una ruta especificada.

    Parámetros de consulta:
    - path: Ruta relativa a listar (predeterminado: '.')
    - max_depth: Profundidad máxima de la exploración (predeterminado: 2)
    - workspace_id: ID del espacio de trabajo (predeterminado: 'default')

    Retorna:
    - Lista de archivos y directorios
    """
    try:
        relative_path = request.args.get('path', '.')
        max_depth = int(request.args.get('max_depth', 2))
        workspace_id = request.args.get('workspace_id', 'default')

        # Construir ruta completa
        workspace_path = os.path.join('user_workspaces', workspace_id)
        target_path = os.path.join(workspace_path, relative_path)

        # Asegurar que no se salga del directorio del usuario (prevenir directory traversal)
        if not os.path.abspath(target_path).startswith(os.path.abspath(workspace_path)):
            return jsonify({
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del espacio de trabajo'
            }), 403

        # Verificar si el directorio existe
        if not os.path.isdir(target_path):
            return jsonify({
                'success': False,
                'error': f'El directorio "{target_path}" no existe.'
            }), 404

        # Listar el contenido del directorio
        success, items, error = file_explorer.list_directory(target_path, 1, max_depth)

        if success:
            return jsonify({
                'success': True,
                'path': relative_path,
                'items': items
            })
        else:
            return jsonify({
                'success': False,
                'error': error
            }), 404
    except ValueError as e:
        logger.error(f"Error de valor al listar directorio: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error de valor al listar el directorio: {str(e)}'
        }), 400 # Bad Request for incorrect input
    except Exception as e:
        logger.error(f"Error al listar directorio: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al listar el directorio: {str(e)}'
        }), 500


@file_explorer_bp.route('/api/explorer/file', methods=['GET'])
def get_file():
    """
    Obtiene el contenido de un archivo específico.

    Parámetros de consulta:
    - path: Ruta relativa al archivo
    - workspace_id: ID del espacio de trabajo (predeterminado: 'default')

    Retorna:
    - Contenido del archivo y tipo
    """
    try:
        relative_path = request.args.get('path')
        workspace_id = request.args.get('workspace_id', 'default')

        if not relative_path:
            return jsonify({
                'success': False,
                'error': 'Debe especificar una ruta de archivo'
            }), 400

        # Construir ruta completa
        workspace_path = os.path.join('user_workspaces', workspace_id)
        file_path = os.path.join(workspace_path, relative_path)

        # Asegurar que no se salga del directorio del usuario
        if not os.path.abspath(file_path).startswith(os.path.abspath(workspace_path)):
            return jsonify({
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del espacio de trabajo'
            }), 403

        # Obtener el contenido del archivo
        success, content, file_type = file_explorer.get_file_content(file_path)

        if success:
            return jsonify({
                'success': True,
                'path': relative_path,
                'content': content,
                'file_type': file_type
            })
        else:
            return jsonify({
                'success': False,
                'error': content  # En caso de error, content contiene el mensaje de error
            }), 404
    except Exception as e:
        logger.error(f"Error al obtener archivo: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al obtener el archivo: {str(e)}'
        }), 500


@file_explorer_bp.route('/api/explorer/file', methods=['POST'])
def update_file():
    """
    Actualiza el contenido de un archivo existente.

    Espera:
    - path: Ruta relativa al archivo
    - content: Nuevo contenido para el archivo
    - workspace_id: ID del espacio de trabajo (predeterminado: 'default')

    Retorna:
    - Confirmación de actualización
    """
    try:
        data = request.json
        relative_path = data.get('path')
        content = data.get('content')
        workspace_id = data.get('workspace_id', 'default')

        if not relative_path or content is None:
            return jsonify({
                'success': False,
                'error': 'Debe especificar una ruta de archivo y contenido'
            }), 400

        # Construir ruta completa
        workspace_path = os.path.join('user_workspaces', workspace_id)
        file_path = os.path.join(workspace_path, relative_path)

        # Asegurar que no se salga del directorio del usuario
        if not os.path.abspath(file_path).startswith(os.path.abspath(workspace_path)):
            return jsonify({
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del espacio de trabajo'
            }), 403

        # Actualizar el archivo
        success, message = file_explorer.update_file_content(file_path, content)

        if success:
            # Registro de actividad (opcional)
            logger.info(f"Archivo actualizado: {file_path}")

            return jsonify({
                'success': True,
                'path': relative_path,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 404
    except Exception as e:
        logger.error(f"Error al actualizar archivo: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al actualizar el archivo: {str(e)}'
        }), 500


@file_explorer_bp.route('/api/explorer/file', methods=['PUT'])
def create_file():
    """
    Crea un nuevo archivo con el contenido especificado.

    Espera:
    - path: Ruta relativa al nuevo archivo
    - content: Contenido para el archivo
    - workspace_id: ID del espacio de trabajo (predeterminado: 'default')

    Retorna:
    - Confirmación de creación
    """
    try:
        data = request.json
        relative_path = data.get('path')
        content = data.get('content', '')
        workspace_id = data.get('workspace_id', 'default')

        if not relative_path:
            return jsonify({
                'success': False,
                'error': 'Debe especificar una ruta de archivo'
            }), 400

        # Construir ruta completa
        workspace_path = os.path.join('user_workspaces', workspace_id)
        file_path = os.path.join(workspace_path, relative_path)

        # Asegurar que no se salga del directorio del usuario
        if not os.path.abspath(file_path).startswith(os.path.abspath(workspace_path)):
            return jsonify({
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del espacio de trabajo'
            }), 403

        # Crear el archivo
        success, message = file_explorer.create_file(file_path, content)

        if success:
            # Registro de actividad (opcional)
            logger.info(f"Archivo creado: {file_path}")

            return jsonify({
                'success': True,
                'path': relative_path,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
    except Exception as e:
        logger.error(f"Error al crear archivo: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al crear el archivo: {str(e)}'
        }), 500


@file_explorer_bp.route('/api/explorer/search', methods=['GET'])
def search_files():
    """
    Busca archivos o directorios en el espacio de trabajo.

    Parámetros de consulta:
    - query: Texto a buscar
    - type: Tipo de búsqueda ('name', 'content', 'extension')
    - path: Ruta base para la búsqueda (predeterminado: '.')
    - workspace_id: ID del espacio de trabajo (predeterminado: 'default')

    Retorna:
    - Lista de archivos/directorios encontrados
    """
    try:
        query = request.args.get('query')
        search_type = request.args.get('type', 'name')
        relative_path = request.args.get('path', '.')
        workspace_id = request.args.get('workspace_id', 'default')

        if not query:
            return jsonify({
                'success': False,
                'error': 'Debe especificar un texto de búsqueda'
            }), 400

        # Construir ruta completa
        workspace_path = os.path.join('user_workspaces', workspace_id)
        search_path = os.path.join(workspace_path, relative_path)

        # Asegurar que no se salga del directorio del usuario
        if not os.path.abspath(search_path).startswith(os.path.abspath(workspace_path)):
            return jsonify({
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del espacio de trabajo'
            }), 403

        # Realizar la búsqueda
        success, found_items, error = file_explorer.find_file(search_path, query, search_type)

        if success:
            # Convertir rutas absolutas a relativas
            relative_items = []
            for item in found_items:
                if item.startswith(workspace_path):
                    relative_items.append(os.path.relpath(item, workspace_path))
                else:
                    relative_items.append(item)

            return jsonify({
                'success': True,
                'query': query,
                'type': search_type,
                'base_path': relative_path,
                'results': relative_items,
                'count': len(relative_items)
            })
        else:
            return jsonify({
                'success': False,
                'error': error
            }), 500
    except Exception as e:
        logger.error(f"Error al buscar archivos: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al buscar archivos: {str(e)}'
        }), 500


@file_explorer_bp.route('/api/explorer/analyze', methods=['GET'])
def analyze_project():
    """
    Analiza la estructura general de un proyecto.

    Parámetros de consulta:
    - path: Ruta relativa al proyecto (predeterminado: '.')
    - workspace_id: ID del espacio de trabajo (predeterminado: 'default')
    - max_depth: Profundidad máxima de análisis (predeterminado: 3)

    Retorna:
    - Información estructurada sobre el proyecto
    """
    try:
        relative_path = request.args.get('path', '.')
        workspace_id = request.args.get('workspace_id', 'default')
        max_depth = int(request.args.get('max_depth', 3))

        # Construir ruta completa
        workspace_path = os.path.join('user_workspaces', workspace_id)
        project_path = os.path.join(workspace_path, relative_path)

        # Asegurar que no se salga del directorio del usuario
        if not os.path.abspath(project_path).startswith(os.path.abspath(workspace_path)):
            return jsonify({
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del espacio de trabajo'
            }), 403

        # Analizar el proyecto
        analysis = file_explorer.analyze_project_structure(project_path, max_depth)

        # Convertir rutas absolutas a relativas en el resultado
        if analysis.get('success', False) and 'important_files' in analysis:
            relative_files = []
            for item in analysis['important_files']:
                if item.startswith(workspace_path):
                    relative_files.append(os.path.relpath(item, workspace_path))
                else:
                    relative_files.append(item)
            analysis['important_files'] = relative_files

        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Error al analizar proyecto: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al analizar el proyecto: {str(e)}'
        }), 500


@file_explorer_bp.route('/api/explorer/compress', methods=['POST'])
def compress_to_zip():
    """
    Comprime un archivo o directorio en formato ZIP.

    Espera:
    - path: Ruta relativa al archivo o directorio a comprimir
    - output_path: (Opcional) Ruta relativa donde guardar el archivo ZIP
    - include_root: (Opcional) Si se debe incluir el directorio raíz en el ZIP (predeterminado: True)
    - workspace_id: ID del espacio de trabajo (predeterminado: 'default')

    Retorna:
    - Confirmación de compresión y ruta del archivo ZIP generado
    """
    try:
        data = request.json
        relative_path = data.get('path')
        relative_output_path = data.get('output_path')
        include_root = data.get('include_root', True)
        workspace_id = data.get('workspace_id', 'default')

        if not relative_path:
            return jsonify({
                'success': False,
                'error': 'Debe especificar una ruta a comprimir'
            }), 400

        # Construir rutas completas
        workspace_path = os.path.join('user_workspaces', workspace_id)
        source_path = os.path.join(workspace_path, relative_path)

        # Si se especificó una ruta de salida, construirla
        if relative_output_path:
            output_zip_path = os.path.join(workspace_path, relative_output_path)
        else:
            # Si no se especificó una ruta de salida, usar una por defecto
            if os.path.isdir(source_path):
                output_zip_path = source_path.rstrip(os.path.sep) + '.zip'
            else:
                output_zip_path = source_path + '.zip'

        # Asegurar que no se salga del directorio del usuario
        if not os.path.abspath(source_path).startswith(os.path.abspath(workspace_path)):
            response = jsonify({
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del espacio de trabajo'
            })
            response.headers['Content-Type'] = 'application/json'
            return response, 403

        # Comprimir en ZIP
        success, message = file_explorer.create_zip_archive(source_path, output_zip_path, include_root)

        if success:
            # Obtener la ruta relativa del archivo ZIP generado
            if output_zip_path:
                result_path = os.path.relpath(output_zip_path, workspace_path)
            else:
                if os.path.isdir(source_path):
                    result_path = os.path.relpath(source_path + '.zip', workspace_path)
                else:
                    result_path = os.path.relpath(source_path + '.zip', workspace_path)

            return jsonify({
                'success': True,
                'message': message,
                'zip_path': result_path
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
    except Exception as e:
        logger.error(f"Error al comprimir en ZIP: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al comprimir en ZIP: {str(e)}'
        }), 500


@file_explorer_bp.route('/api/explorer/extract', methods=['POST'])
def extract_compressed():
    """
    Extrae un archivo comprimido (ZIP o RAR).

    Espera:
    - path: Ruta relativa al archivo comprimido
    - extract_dir: (Opcional) Ruta relativa donde extraer el contenido
    - workspace_id: ID del espacio de trabajo (predeterminado: 'default')

    Retorna:
    - Confirmación de extracción y lista de archivos extraídos
    """
    try:
        data = request.json
        relative_path = data.get('path')
        relative_extract_dir = data.get('extract_dir')
        workspace_id = data.get('workspace_id', 'default')

        if not relative_path:
            return jsonify({
                'success': False,
                'error': 'Debe especificar una ruta de archivo comprimido'
            }), 400

        # Construir rutas completas
        workspace_path = os.path.join('user_workspaces', workspace_id)
        file_path = os.path.join(workspace_path, relative_path)

        # Si se especificó un directorio de extracción, construirlo
        extract_dir = None
        if relative_extract_dir:
            extract_dir = os.path.join(workspace_path, relative_extract_dir)

        # Asegurar que no se salga del directorio del usuario
        if not os.path.abspath(file_path).startswith(os.path.abspath(workspace_path)):
            response = jsonify({
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del espacio de trabajo'
            })
            response.headers['Content-Type'] = 'application/json'
            return response, 403

        # Extraer archivo comprimido
        success, message, extracted_files = file_explorer.extract_compressed_file(file_path, extract_dir)

        if success:
            # Obtener la ruta relativa del directorio de extracción
            if extract_dir:
                extract_rel_path = os.path.relpath(extract_dir, workspace_path)
            else:
                # Si no se especificó, se creó uno junto al archivo
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                extract_rel_path = os.path.join(os.path.dirname(relative_path), file_name)

            return jsonify({
                'success': True,
                'message': message,
                'extract_path': extract_rel_path,
                'files': extracted_files
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
    except Exception as e:
        logger.error(f"Error al extraer archivo comprimido: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al extraer archivo comprimido: {str(e)}'
        }), 500


@file_explorer_bp.route('/api/explorer/download', methods=['GET'])
def download_file_or_dir():
    """
    Descarga un archivo o directorio (comprimido en ZIP).

    Parámetros de consulta:
    - path: Ruta relativa al archivo o directorio
    - workspace_id: ID del espacio de trabajo (predeterminado: 'default')

    Retorna:
    - El archivo para descarga, o un archivo ZIP para directorios
    """
    try:
        relative_path = request.args.get('path')
        workspace_id = request.args.get('workspace_id', 'default')

        if not relative_path:
            return jsonify({
                'success': False,
                'error': 'Debe especificar una ruta para descargar'
            }), 400

        # Construir ruta completa
        workspace_path = os.path.join('user_workspaces', workspace_id)
        file_path = os.path.join(workspace_path, relative_path)

        # Asegurar que no se salga del directorio del usuario
        if not os.path.abspath(file_path).startswith(os.path.abspath(workspace_path)):
            return jsonify({
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del espacio de trabajo'
            }), 403

        # Verificar si existe
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': f'La ruta {relative_path} no existe'
            }), 404

        # Si es un archivo, simplemente descargarlo
        if os.path.isfile(file_path):
            return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

        # Si es un directorio, comprimirlo primero
        if os.path.isdir(file_path):
            # Crear un archivo ZIP temporal
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                temp_zip_path = temp_file.name

            # Comprimir el directorio
            success, message = file_explorer.create_zip_archive(file_path, temp_zip_path, True)

            if success:
                # Establecer nombre de descarga para el ZIP
                dir_name = os.path.basename(file_path.rstrip(os.path.sep))
                download_name = f"{dir_name}.zip"

                # Enviar el archivo y programar su eliminación después
                return send_file(
                    temp_zip_path,
                    as_attachment=True,
                    download_name=download_name,
                    # Eliminar archivo temporal después de enviarlo
                    # Este parámetro no funciona en Flask antiguo, pero sí en versiones recientes
                    max_age=0
                )
            else:
                # Limpiar si hubo error
                if os.path.exists(temp_zip_path):
                    os.unlink(temp_zip_path)

                return jsonify({
                    'success': False,
                    'error': f'Error al comprimir el directorio: {message}'
                }), 500

        # Ni archivo ni directorio (no debería llegar aquí)
        return jsonify({
            'success': False,
            'error': f'La ruta {relative_path} no es un archivo ni directorio válido'
        }), 400
    except Exception as e:
        logger.error(f"Error al descargar: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al descargar: {str(e)}'
        }), 500


@file_explorer_bp.route('/api/explorer/upload', methods=['POST'])
def upload_file():
    """
    Sube un archivo al espacio de trabajo.

    Form data:
    - file: Archivo a subir
    - path: Ruta relativa donde guardar el archivo (predeterminado: '.')
    - workspace_id: ID del espacio de trabajo (predeterminado: 'default')
    - extract: Si es True y el archivo es ZIP o RAR, extraerlo automáticamente

    Retorna:
    - Confirmación de carga y ruta del archivo
    """
    try:
        # Verificar si hay un archivo en la solicitud
        if 'file' not in request.files:
            response = jsonify({
                'success': False,
                'error': 'No se ha enviado ningún archivo'
            })
            response.headers['Content-Type'] = 'application/json'
            return response, 400

        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            response = jsonify({
                'success': False,
                'error': 'Nombre de archivo vacío'
            })
            response.headers['Content-Type'] = 'application/json'
            return response, 400

        relative_path = request.form.get('path', '.')
        workspace_id = request.form.get('workspace_id', 'default')
        extract = request.form.get('extract', 'false').lower() == 'true'

        # Construir ruta completa
        workspace_path = os.path.join('user_workspaces', workspace_id)
        target_dir = os.path.join(workspace_path, relative_path)

        # Asegurar que no se salga del directorio del usuario
        if not os.path.abspath(target_dir).startswith(os.path.abspath(workspace_path)):
            response = jsonify({
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del espacio de trabajo'
            })
            response.headers['Content-Type'] = 'application/json'
            return response, 403

        # Asegurar que el directorio exista
        os.makedirs(target_dir, exist_ok=True)

        # Guardar el archivo usando un método más eficiente para archivos grandes
        filename = secure_filename(uploaded_file.filename)
        file_path = os.path.join(target_dir, filename)

        # Guardar el archivo para mejor manejo de memoria
        try:
            # Usar el método save proporcionado por werkzeug, que maneja internamente los archivos grandes
            uploaded_file.save(file_path)
            logger.info(f"Archivo {filename} guardado correctamente en {file_path}")
        except Exception as save_error:
            logger.error(f"Error al guardar archivo: {str(save_error)}")
            response = jsonify({
                'success': False,
                'error': f'Error al guardar archivo: {str(save_error)}'
            })
            response.headers['Content-Type'] = 'application/json'
            return response, 500

        # Si es archivo comprimido y se solicitó extracción (que ahora siempre es falso por defecto)
        file_ext = os.path.splitext(filename)[1].lower()
        if extract and file_ext in ['.zip']:
            # Extraer archivo
            try:
                success, message, extracted_files = file_explorer.extract_compressed_file(file_path)

                if success:
                    # Obtener la ruta relativa del directorio de extracción
                    file_name = os.path.splitext(filename)[0]
                    extract_rel_path = os.path.join(relative_path, file_name)

                    response = jsonify({
                        'success': True,
                        'message': f'Archivo subido y extraído: {filename}',
                        'file_path': os.path.join(relative_path, filename),
                        'extract_path': extract_rel_path,
                        'extracted': True,
                        'files': extracted_files
                    })
                    response.headers['Content-Type'] = 'application/json'
                    return response
                else:
                    response = jsonify({
                        'success': True,
                        'message': f'Archivo subido pero no se pudo extraer: {message}',
                        'file_path': os.path.join(relative_path, filename),
                        'extracted': False
                    })
                    response.headers['Content-Type'] = 'application/json'
                    return response
            except Exception as extract_error:
                logger.error(f"Error al extraer archivo: {str(extract_error)}")
                # Continuamos con el flujo normal, el archivo se subió pero no se pudo extraer

        # Archivo normal (no comprimido o sin extracción)
        response = jsonify({
            'success': True,
            'message': f'Archivo subido: {filename}',
            'file_path': os.path.join(relative_path, filename),
            'extracted': False
        })
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        logger.error(f"Error al subir archivo: {str(e)}")
        response = jsonify({
            'success': False,
            'error': f'Error al subir archivo: {str(e)}'
        })
        response.headers['Content-Type'] = 'application/json'
        return response, 500


@file_explorer_bp.route('/api/explorer/delete', methods=['POST', 'DELETE'])
def delete_file_or_directory():
    """Delete a file or directory."""
    try:
        # Log the incoming request for debugging
        logger.debug(f"Delete request: Method={request.method}, Content-Type={request.content_type}")
        
        # Handle both JSON and query parameters for maximum flexibility
        if request.method == 'DELETE':
            # For DELETE requests, typically path is in query parameters
            path = request.args.get('path', '')
            if not path and request.is_json:
                # If no path in query params but we have JSON body
                try:
                    data = request.get_json(force=True)
                    path = data.get('path', '')
                except Exception as e:
                    logger.error(f"Error parsing JSON in DELETE request: {str(e)}")
        else:  # POST
            # For POST requests, typically path is in JSON body
            try:
                if request.is_json:
                    data = request.get_json(force=True)
                    path = data.get('path', '')
                else:
                    # For form data
                    path = request.form.get('path', '')
            except Exception as e:
                logger.error(f"Error parsing request data: {str(e)}")
                path = ''
                
        # Log the path we're trying to delete
        logger.debug(f"Attempting to delete path: {path}")
            
        # Get workspace ID from either JSON or query params
        workspace_id = request.args.get('workspace_id', 'default')
        
        if not path:
            logger.error("No path provided for deletion")
            return jsonify({'error': 'No path provided'}), 400

        # Get the user workspace
        workspace_path = os.path.join('user_workspaces', workspace_id)
        
        # Limpiar y normalizar la ruta
        # Eliminar posibles referencias a workspace en la ruta
        if path.startswith('user_workspaces/'):
            path = path[path.find('/', 15) + 1:]  # Saltar después de "user_workspaces/default/"
        
        # Eliminar './' al inicio si existe
        path = path.lstrip('./')
        
        # Build target path correctamente
        target_path = os.path.join(workspace_path, path)
        logger.debug(f"Target path for deletion: {target_path}")

        # Verify path is within workspace
        if not os.path.abspath(target_path).startswith(os.path.abspath(workspace_path)):
            logger.error(f"Access denied: Path {target_path} outside workspace {workspace_path}")
            return jsonify({'error': 'Access denied: Path outside workspace'}), 403

        if os.path.exists(target_path):
            try:
                if os.path.isdir(target_path):
                    shutil.rmtree(target_path)
                    logger.info(f"Successfully deleted directory: {target_path}")
                else:
                    os.remove(target_path)
                    logger.info(f"Successfully deleted file: {target_path}")
                return jsonify({'success': True, 'message': f'Deleted {path}'})
            except PermissionError as pe:
                logger.error(f"Permission denied when deleting {target_path}: {str(pe)}")
                return jsonify({'error': 'Permission denied'}), 403
            except Exception as e:
                logger.error(f"Error during deletion of {target_path}: {str(e)}")
                return jsonify({'error': str(e)}), 500
        else:
            logger.error(f"Path not found for deletion: {target_path}")
            return jsonify({'error': 'Path not found'}), 404

    except Exception as e:
        logger.error(f"Unexpected error in delete_file_or_directory: {str(e)}")
        return jsonify({'error': str(e)}), 500

@file_explorer_bp.route('/api/explorer/upload_chunk', methods=['POST'])
def upload_chunk():
    """
    Sube un fragmento de archivo al espacio de trabajo.
    Esta ruta está diseñada para subir archivos grandes en fragmentos.

    Form data:
    - chunk: Fragmento de archivo a subir
    - filename: Nombre del archivo a crear
    - index: Índice del fragmento (iniciando en 0)
    - total_chunks: Número total de fragmentos
    - path: Ruta relativa donde guardar el archivo (predeterminado: '.')
    - workspace_id: ID del espacio de trabajo (predeterminado: 'default')

    Retorna:
    - Confirmación de carga del fragmento o del archivo completo
    """
    try:
        # Verificar si hay un fragmento de archivo en la solicitud
        if 'chunk' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No se ha enviado ningún fragmento de archivo'
            }), 400

        chunk = request.files['chunk']
        if chunk.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nombre de archivo vacío'
            }), 400

        # Obtener parámetros
        filename = request.form.get('filename', '')
        chunk_index = int(request.form.get('index', 0))
        total_chunks = int(request.form.get('total_chunks', 1))
        relative_path = request.form.get('path', '.')
        workspace_id = request.form.get('workspace_id', 'default')

        if not filename:
            return jsonify({
                'success': False,
                'error': 'El nombre del archivo es obligatorio'
            }), 400

        # Construir ruta completa
        workspace_path = os.path.join('user_workspaces', workspace_id)
        target_dir = os.path.join(workspace_path, relative_path)

        # Asegurar que no se salga del directorio del usuario
        if not os.path.abspath(target_dir).startswith(os.path.abspath(workspace_path)):
            return jsonify({
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del espacio de trabajo'
            }), 403

        # Asegurar que el directorio exista
        os.makedirs(target_dir, exist_ok=True)

        # Carpeta temporal para almacenar fragmentos
        temp_dir = os.path.join(target_dir, '.temp_chunks', secure_filename(filename))
        os.makedirs(temp_dir, exist_ok=True)

        # Guardar el fragmento
        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
        chunk.save(chunk_path)

        # Verificar si es el último fragmento
        chunks_dir = os.path.join(target_dir, '.temp_chunks', secure_filename(filename))
        chunks = os.listdir(chunks_dir)

        # Si tenemos todos los fragmentos, unirlos
        if len(chunks) == total_chunks:
            # Construir el archivo final
            final_path = os.path.join(target_dir, secure_filename(filename))
            with open(final_path, 'wb') as final_file:
                for i in range(total_chunks):
                    chunk_file_path = os.path.join(temp_dir, f"chunk_{i}")
                    with open(chunk_file_path, 'rb') as cf:
                        final_file.write(cf.read())

            # Limpiar fragmentos temporales
            import shutil
            shutil.rmtree(temp_dir)

            # Verificar si es un archivo ZIP y necesita extracción
            file_ext = os.path.splitext(filename)[1].lower()

            return jsonify({
                'success': True,
                'message': f'Archivo "{filename}" creado correctamente desde {total_chunks} fragmentos',
                'file_path': os.path.join(relative_path, secure_filename(filename)),
                'completed': True,
                'is_zip': file_ext == '.zip'
            })
        else:
            # No es el último fragmento
            return jsonify({
                'success': True,
                'message': f'Fragmento {chunk_index+1}/{total_chunks} recibido',
                'completed': False,
                'chunks_received': len(chunks),
                'total_chunks': total_chunks
            })

    except Exception as e:
        logger.error(f"Error al subir fragmento: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al subir fragmento: {str(e)}'
        }), 500

def register_file_explorer_routes(app):
    """Registra las rutas de exploración de archivos en la aplicación Flask."""
    app.register_blueprint(file_explorer_bp)
    logger.info("Rutas de exploración de archivos registradas correctamente")