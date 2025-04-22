"""
Rutas de diagnóstico para Codestorm Assistant.
Estas rutas proporcionan información sobre el estado de la aplicación y las conexiones a las APIs.
"""
import os
import logging
from flask import jsonify
import openai
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai

def register_diagnostic_routes(app):
    """Registra las rutas de diagnóstico en la aplicación Flask."""
    
    @app.route('/health')
    def health():
        """Health check route for deployment."""
        return jsonify({
            'status': 'ok', 
            'message': 'Aplicación funcionando correctamente',
            'diagnostic_routes': ['health', 'api/test_apis']
        })

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
                logging.info("Probando conexión con OpenAI...")
                client = OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Say 'OpenAI connection successful' in Spanish."}
                    ],
                    max_tokens=20
                )
                results['apis']['openai'] = {
                    'status': 'connected',
                    'message': 'Conexión exitosa'
                }
                logging.info("Conexión con OpenAI exitosa.")
            except Exception as e:
                error_msg = str(e)
                results['apis']['openai'] = {
                    'status': 'error',
                    'message': error_msg[:100] + '...' if len(error_msg) > 100 else error_msg
                }
                logging.error(f"Error al conectar con OpenAI: {error_msg}")
        else:
            results['apis']['openai'] = {
                'status': 'not_configured',
                'message': 'API key no configurada'
            }
        
        # Verificar Anthropic
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        if anthropic_key:
            try:
                logging.info("Probando conexión con Anthropic...")
                client = Anthropic(api_key=anthropic_key)
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=20,
                    messages=[
                        {"role": "user", "content": "Say 'Anthropic connection successful' in Spanish."}
                    ]
                )
                results['apis']['anthropic'] = {
                    'status': 'connected',
                    'message': 'Conexión exitosa'
                }
                logging.info("Conexión con Anthropic exitosa.")
            except Exception as e:
                error_msg = str(e)
                results['apis']['anthropic'] = {
                    'status': 'error',
                    'message': error_msg[:100] + '...' if len(error_msg) > 100 else error_msg
                }
                logging.error(f"Error al conectar con Anthropic: {error_msg}")
        else:
            results['apis']['anthropic'] = {
                'status': 'not_configured',
                'message': 'API key no configurada'
            }
        
        # Verificar Gemini
        gemini_key = os.environ.get('GEMINI_API_KEY')
        if gemini_key:
            try:
                logging.info("Probando conexión con Gemini...")
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content("Say 'Gemini connection successful' in Spanish.")
                results['apis']['gemini'] = {
                    'status': 'connected',
                    'message': 'Conexión exitosa'
                }
                logging.info("Conexión con Gemini exitosa.")
            except Exception as e:
                error_msg = str(e)
                results['apis']['gemini'] = {
                    'status': 'error',
                    'message': error_msg[:100] + '...' if len(error_msg) > 100 else error_msg
                }
                logging.error(f"Error al conectar con Gemini: {error_msg}")
        else:
            results['apis']['gemini'] = {
                'status': 'not_configured',
                'message': 'API key no configurada'
            }
        
        # Actualizar estado general
        all_connected = all(api['status'] == 'connected' for api in results['apis'].values())
        any_connected = any(api['status'] == 'connected' for api in results['apis'].values())
        
        if all_connected:
            results['status'] = 'all_ok'
        elif any_connected:
            results['status'] = 'partial_ok'
        else:
            results['status'] = 'all_failed'
        
        return jsonify(results)