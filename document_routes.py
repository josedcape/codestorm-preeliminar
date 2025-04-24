"""
Rutas para el manejo de documentos y contexto en el asistente.
Proporciona funcionalidades para cargar, procesar y usar documentos como contexto.
"""

import os
import json
import logging
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename
import document_loader

logger = logging.getLogger(__name__)

# Crear el blueprint para las rutas de documentos
document_bp = Blueprint('document', __name__)

# Configurar directorio para almacenar los documentos cargados
UPLOAD_FOLDER = 'user_workspaces/context_documents'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Extensiones permitidas para los archivos
ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'doc', 'html', 'htm', 'md', 'txt', 
    'py', 'js', 'css', 'json', 'csv', 'xml', 'yml', 'yaml',
    'pptx', 'epub'
}

def allowed_file(filename):
    """Verifica si la extensión del archivo está permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@document_bp.route('/api/documents/upload', methods=['POST'])
def upload_document():
    """
    Sube un documento y lo almacena para uso posterior como contexto.
    
    Espera:
    - file: El archivo a subir
    - user_id: ID del usuario (opcional)
    
    Retorna:
    - Información sobre el documento subido
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No se ha proporcionado ningún archivo'
            }), 400
            
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nombre de archivo vacío'
            }), 400
            
        user_id = request.form.get('user_id', 'default')
        
        # Crear directorio específico para el usuario
        user_document_dir = os.path.join(UPLOAD_FOLDER, user_id)
        os.makedirs(user_document_dir, exist_ok=True)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(user_document_dir, filename)
            
            # Guardar el archivo
            file.save(file_path)
            
            # Obtener información del documento
            doc_info = document_loader.get_document_summary(file_path)
            
            if doc_info['success']:
                return jsonify({
                    'success': True,
                    'message': 'Documento subido correctamente',
                    'document': {
                        'filename': filename,
                        'path': file_path,
                        'size': doc_info['file_size'],
                        'word_count': doc_info['total_words'],
                        'preview': doc_info['text_preview'][:300] + '...' if len(doc_info['text_preview']) > 300 else doc_info['text_preview']
                    }
                })
            else:
                # Si no se pudo procesar, devolver error pero mantener el archivo
                return jsonify({
                    'success': True,
                    'message': 'Documento subido pero no se pudo procesar completamente',
                    'warning': doc_info['error'],
                    'document': {
                        'filename': filename,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                    }
                })
        else:
            return jsonify({
                'success': False,
                'error': f'Formato de archivo no permitido. Formatos soportados: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
    except Exception as e:
        logger.error(f"Error al subir documento: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al procesar el documento: {str(e)}'
        }), 500


@document_bp.route('/api/documents/list', methods=['GET'])
def list_documents():
    """
    Lista todos los documentos del usuario.
    
    Parámetros:
    - user_id: ID del usuario (opcional)
    
    Retorna:
    - Lista de documentos disponibles
    """
    try:
        user_id = request.args.get('user_id', 'default')
        user_document_dir = os.path.join(UPLOAD_FOLDER, user_id)
        
        # Asegurar que el directorio de documentos existe
        os.makedirs(user_document_dir, exist_ok=True)
        
        if not os.path.exists(user_document_dir):
            logger.warning(f"Directorio de documentos no encontrado: {user_document_dir}")
            return jsonify({
                'success': True,
                'documents': []
            })
            
        documents = []
        
        try:
            for filename in os.listdir(user_document_dir):
                file_path = os.path.join(user_document_dir, filename)
                
                if os.path.isfile(file_path) and allowed_file(filename):
                    # Obtener información básica del archivo
                    try:
                        doc_info = {
                            'filename': filename,
                            'path': file_path,
                            'size': os.path.getsize(file_path),
                            'type': os.path.splitext(filename)[1].lower(),
                            'last_modified': os.path.getmtime(file_path)
                        }
                        documents.append(doc_info)
                    except OSError as file_error:
                        logger.warning(f"Error al procesar archivo {file_path}: {str(file_error)}")
                        # Continuar con el siguiente archivo
                        continue
        except OSError as dir_error:
            logger.error(f"Error al listar directorio {user_document_dir}: {str(dir_error)}")
            # Devolver lista vacía en caso de error de directorio
            return jsonify({
                'success': True,
                'documents': []
            })
        
        # Ordenar por fecha de modificación (más reciente primero)
        documents.sort(key=lambda x: x['last_modified'], reverse=True)
        
        return jsonify({
            'success': True,
            'documents': documents
        })
    except Exception as e:
        logger.error(f"Error al listar documentos: {str(e)}")
        # Devolver un error más amigable para el cliente
        return jsonify({
            'success': False,
            'error': 'Error al listar documentos. Por favor, inténtelo de nuevo más tarde.'
        }), 500


@document_bp.route('/api/documents/info/<path:filename>', methods=['GET'])
def get_document_info(filename):
    """
    Obtiene información detallada sobre un documento específico.
    
    Parámetros:
    - filename: Nombre del archivo
    - user_id: ID del usuario (opcional)
    
    Retorna:
    - Información detallada del documento
    """
    try:
        user_id = request.args.get('user_id', 'default')
        filename = secure_filename(filename)
        file_path = os.path.join(UPLOAD_FOLDER, user_id, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'El documento no existe'
            }), 404
            
        # Obtener información del documento
        doc_info = document_loader.get_document_summary(file_path)
        
        if doc_info['success']:
            return jsonify({
                'success': True,
                'document': {
                    'filename': filename,
                    'path': file_path,
                    'size': doc_info['file_size'],
                    'type': doc_info['file_type'],
                    'word_count': doc_info['total_words'],
                    'preview': doc_info['text_preview']
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Error al procesar el documento: {doc_info["error"]}'
            }), 500
    except Exception as e:
        logger.error(f"Error al obtener información del documento: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al obtener información: {str(e)}'
        }), 500


@document_bp.route('/api/documents/delete/<path:filename>', methods=['DELETE'])
def delete_document(filename):
    """
    Elimina un documento específico.
    
    Parámetros:
    - filename: Nombre del archivo
    - user_id: ID del usuario (opcional)
    
    Retorna:
    - Confirmación de eliminación
    """
    try:
        user_id = request.args.get('user_id', 'default')
        filename = secure_filename(filename)
        file_path = os.path.join(UPLOAD_FOLDER, user_id, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'El documento no existe'
            }), 404
            
        # Eliminar el archivo
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': f'Documento {filename} eliminado correctamente'
        })
    except Exception as e:
        logger.error(f"Error al eliminar documento: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al eliminar documento: {str(e)}'
        }), 500


@document_bp.route('/api/documents/content/<path:filename>', methods=['GET'])
def get_document_content(filename):
    """
    Obtiene el contenido extraído de un documento.
    
    Parámetros:
    - filename: Nombre del archivo
    - user_id: ID del usuario (opcional)
    - raw: Si se debe devolver el archivo sin procesar (opcional)
    
    Retorna:
    - Contenido del documento
    """
    try:
        user_id = request.args.get('user_id', 'default')
        raw = request.args.get('raw', 'false').lower() == 'true'
        
        filename = secure_filename(filename)
        file_path = os.path.join(UPLOAD_FOLDER, user_id, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'El documento no existe'
            }), 404
            
        if raw:
            # Devolver el archivo sin procesar
            return send_file(file_path)
        else:
            # Procesar y devolver el contenido extraído
            result = document_loader.load_document_as_context(file_path)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'content': result['context']['content'],
                    'word_count': result['context']['word_count'],
                    'source': result['context']['source']
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Error al extraer contenido: {result["error"]}'
                }), 500
    except Exception as e:
        logger.error(f"Error al obtener contenido del documento: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al obtener contenido: {str(e)}'
        }), 500


@document_bp.route('/api/chat/with-context', methods=['POST'])
def chat_with_context():
    """
    Procesa un mensaje de chat utilizando un documento como contexto.
    Si el documento no es extenso, devolverá el contenido directamente para
    que el cliente lo incorpore en el chat.
    
    Espera:
    - message: Mensaje del usuario
    - document_filename: Nombre del documento a usar como contexto
    - agent_id: ID del agente a utilizar (opcional)
    - user_id: ID del usuario (opcional)
    - document_already_processed: Booleano que indica si el documento ya fue procesado (opcional)
    - context: Contexto previo de la conversación (opcional)
    
    Retorna:
    - Respuesta del asistente considerando el contexto del documento
      o el contenido del documento para su inclusión en el chat
    """
    try:
        data = request.json
        message = data.get('message')
        document_filename = data.get('document_filename')
        agent_id = data.get('agent_id', 'general')
        user_id = data.get('user_id', 'default')
        document_already_processed = data.get('document_already_processed', False)
        conversation_context = data.get('context', [])
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'No se ha proporcionado un mensaje'
            }), 400
            
        if not document_filename:
            return jsonify({
                'success': False,
                'error': 'No se ha especificado un documento como contexto'
            }), 400
        
        # Si el documento ya fue procesado, usar el contexto de la conversación previa
        if document_already_processed and conversation_context:
            logger.info(f"Usando contexto existente para documento ya procesado: {document_filename}")
            
            # Para documentos ya procesados, usar el contexto de conversación para responder
            import agents_utils
            
            # Extraer el contenido del documento del historial de conversación
            document_content = ""
            for msg in conversation_context:
                if msg.get('role') == 'assistant' and f"He extraído el contenido del documento '{document_filename}'" in msg.get('content', ''):
                    document_content = msg.get('content', '')
                    break
            
            # Construir un contexto de documento sintético
            document_context = {
                'content': document_content,
                'source': document_filename,
                'word_count': len(document_content.split())
            }
            
            # Generar respuesta usando el agente con el contexto del documento
            response_result = agents_utils.generate_response(
                user_message=message,
                agent_id=agent_id,
                context=conversation_context,
                model="openai",  # Se podría hacer configurable
                document_context=document_context
            )
            
            if not response_result['success']:
                error_msg = response_result.get('error', 'Error al generar respuesta')
                logger.warning(f"Error en generate_response: {error_msg}.")
                
                return jsonify({
                    'success': False,
                    'error': f'Error al generar respuesta: {error_msg}'
                }), 500
                
            response = response_result['response']
            
            return jsonify({
                'success': True,
                'message': message,
                'response': response,
                'document': {
                    'filename': document_filename,
                    'processed': True
                },
                'agent_id': agent_id
            })
            
        # Si es la primera vez que se procesa, cargar el documento
        filename = secure_filename(document_filename)
        file_path = os.path.join(UPLOAD_FOLDER, user_id, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'El documento especificado no existe'
            }), 404
            
        # Obtener el contexto del documento
        context_result = document_loader.load_document_as_context(file_path)
        
        if not context_result['success']:
            return jsonify({
                'success': False,
                'error': f'Error al cargar el documento como contexto: {context_result["error"]}'
            }), 500
            
        # Construir el contexto del documento 
        document_context = context_result['context']
        word_count = document_context['word_count']
        
        # Determinar si el documento es lo suficientemente pequeño para mostrarlo directamente
        # (menos de 1000 palabras se considera pequeño)
        MAX_WORDS_FOR_DIRECT_DISPLAY = 1000
        
        if word_count <= MAX_WORDS_FOR_DIRECT_DISPLAY:
            # Para documentos pequeños, devolver el contenido para mostrarlo directamente
            return jsonify({
                'success': True,
                'message': message,
                'use_direct_content': True,
                'document_content': document_context['content'],
                'document': {
                    'filename': document_filename,
                    'word_count': word_count
                },
                'agent_id': agent_id,
                'response': f"He extraído el contenido del documento '{document_filename}' (contiene {word_count} palabras). Aquí está el contenido completo:\n\n{document_context['content']}\n\nPuedes hacerme preguntas específicas sobre este documento."
            })
        
        # Para documentos más grandes, seguir usando el modelo IA
        import agents_utils
        
        # Generar respuesta usando el agente con el contexto del documento
        response_result = agents_utils.generate_response(
            user_message=message,
            agent_id=agent_id,
            model="openai",  # Se podría hacer configurable
            document_context=document_context
        )
        
        if not response_result['success']:
            # En caso de error con la API, también mostrar el contenido directamente
            # pero con un mensaje de error al inicio
            error_msg = response_result.get('error', 'Error al generar respuesta con el documento como contexto')
            logger.warning(f"Error en generate_response: {error_msg}. Mostrando contenido directo como alternativa.")
            
            return jsonify({
                'success': True,
                'message': message,
                'use_direct_content': True,
                'document_content': document_context['content'],
                'document': {
                    'filename': document_filename,
                    'word_count': word_count
                },
                'agent_id': agent_id,
                'response': f"Hubo un problema al procesar este documento con el asistente IA ({error_msg}), pero he extraído el contenido del documento '{document_filename}' (contiene {word_count} palabras). Aquí está el contenido completo:\n\n{document_context['content']}\n\nPuedes hacerme preguntas específicas sobre este documento."
            })
            
        response = response_result['response']
        
        return jsonify({
            'success': True,
            'message': message,
            'response': response,
            'document': {
                'filename': document_filename,
                'word_count': word_count
            },
            'agent_id': agent_id
        })
    except Exception as e:
        logger.error(f"Error en chat con contexto: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al procesar el chat con contexto: {str(e)}'
        }), 500


def register_document_routes(app):
    """Registra las rutas de documentos en la aplicación Flask."""
    app.register_blueprint(document_bp)