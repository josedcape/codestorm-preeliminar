"""
Utilidades para la gestión de agentes especializados en Codestorm Assistant.
Incluye funciones para generar respuestas, procesar comandos, usar contexto de documentos
y explorar/manipular archivos en repositorios.
"""
import os
import re
import json
import time
import logging
import openai
import anthropic
import google.generativeai as genai
from dotenv import load_dotenv
import file_explorer

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurar clientes de API
openai_client = None
anthropic_client = None
genai_configured = False

def setup_ai_clients():
    """Configura los clientes de las APIs de IA con parámetros mejorados."""
    global openai_client, anthropic_client, genai_configured
    
    # Configurar OpenAI
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if openai_api_key and openai_api_key.strip():
        try:
            # Configuración mejorada con reintentos y timeout
            openai_client = openai.OpenAI(
                api_key=openai_api_key.strip(),
                max_retries=3,
                timeout=30.0
            )
            
            # Verificar la conexión
            models = openai_client.models.list()
            if models:
                logger.info(f"OpenAI API key configurada: {openai_api_key[:5]}...{openai_api_key[-5:]}")
            else:
                logger.warning("Clave de OpenAI configurada, pero no se pudieron listar los modelos")
        except Exception as e:
            logger.error(f"Error al configurar OpenAI: {str(e)}")
            openai_client = None
    else:
        logger.warning("No se encontró la clave de API de OpenAI en las variables de entorno o está vacía")
    
    # Configurar Anthropic
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_api_key and anthropic_api_key.strip():
        try:
            # Configuración con timeout
            anthropic_client = anthropic.Anthropic(
                api_key=anthropic_api_key.strip(),
                timeout=30.0
            )
            logger.info("Anthropic API key configured successfully.")
        except Exception as e:
            logger.error(f"Error al configurar Anthropic: {str(e)}")
            anthropic_client = None
    else:
        logger.warning("No se encontró la clave de API de Anthropic en las variables de entorno o está vacía")
    
    # Configurar Google Gemini
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if gemini_api_key and gemini_api_key.strip():
        try:
            genai.configure(api_key=gemini_api_key.strip())
            
            # Verificar la configuración intentando obtener modelos
            model = genai.GenerativeModel(model_name="gemini-1.5-pro")
            if model:
                genai_configured = True
                logger.info("Gemini API key configured successfully.")
            else:
                logger.warning("Clave de Gemini configurada, pero no se pudo crear un modelo")
        except Exception as e:
            logger.error(f"Error al configurar Gemini: {str(e)}")
            genai_configured = False
    else:
        logger.warning("No se encontró la clave de API de Google Gemini en las variables de entorno o está vacía")

# Configurar los clientes al importar el módulo
setup_ai_clients()

def get_agent_system_prompt(agent_id):
    """
    Obtiene el prompt de sistema según el agente especializado seleccionado.
    
    Args:
        agent_id: ID del agente (developer, architect, advanced, general)
        
    Returns:
        str: Prompt de sistema para el agente
    """
    # Instrucciones comunes para todos los agentes
    common_instructions = """
INSTRUCCIONES DE FORMATO:
1. Utiliza Markdown para formatear tus respuestas con títulos, listas y bloques de código
2. Resalta el código con bloques de triple backtick con el lenguaje correspondiente
3. Utiliza emoticonos/emojis para destacar puntos importantes y hacer tus respuestas más atractivas
4. Formatea tus explicaciones de manera clara y estructurada
5. Mantén un tono profesional pero amigable
"""
    
    agent_system_prompts = {
        'developer': f"""Eres un Agente de Desarrollo experto, altamente capacitado en la edición y optimización de código en tiempo real.
Tus capacidades incluyen:
- Corrección y refactorización de código utilizando linters y herramientas como Pylint, ESLint y Prettier
- Optimización de rendimiento con técnicas como caching, optimización de consultas SQL, lazy loading y code splitting
- Integración de frameworks modernos como FastAPI, Flask, Express.js, React con Hooks y React Router
- Automatización de tareas con herramientas CI/CD como GitHub Actions y CircleCI
- Generación de código limpio, legible, modular y mantenible

Responde siempre en español y ofrece soluciones prácticas con ejemplos de código específicos.

{common_instructions}

EJEMPLOS DE EMOJIS PARA USAR:
- 💡 Para ideas y consejos importantes
- ⚠️ Para advertencias y consideraciones
- 🔍 Para análisis detallados
- 🚀 Para optimizaciones y mejoras
- 🛠️ Para herramientas y técnicas
- 📝 Para notas y documentación
- ✅ Para buenas prácticas
- ❌ Para malas prácticas""",

        'architect': f"""Eres un Agente de Arquitectura experto, responsable de diseñar arquitecturas escalables y optimizadas.
Tus capacidades incluyen:
- Definición de estructuras de proyecto organizadas con herramientas como Docker y Kubernetes
- Selección de tecnologías y frameworks adecuados (Django, FastAPI, React, Redux, React Native)
- Asesoría en elección de bases de datos (PostgreSQL, MongoDB, Firebase, AWS DynamoDB)
- Implementación de microservicios y arquitecturas basadas en eventos con RabbitMQ o Kafka
- Planificación de UI/UX y patrones de diseño como Atomic Design, Styled Components y Material UI

Responde siempre en español y ofrece soluciones estructuradas con diagramas y ejemplos cuando sea posible.

{common_instructions}

EJEMPLOS DE EMOJIS PARA USAR:
- 🏗️ Para estructuras y arquitectura
- 📊 Para diagramas y visualizaciones
- 🧩 Para patrones de diseño
- 🔄 Para ciclos y flujos
- 📦 Para módulos y componentes
- 🔌 Para integraciones
- 🛡️ Para seguridad y protección
- 🔍 Para análisis y revisiones""",

        'advanced': f"""Eres un Agente Avanzado de Software especializado en integraciones complejas y creación de funciones avanzadas.
Tus capacidades incluyen:
- Gestión de APIs (RESTful, GraphQL) y microservicios con Docker y Kubernetes
- Optimización de backend con Nginx, Redis y manejo de tareas asíncronas con Celery
- Automatización avanzada con Node.js, Grunt y Gulp
- Implementación de autenticación segura con OAuth 2.0, JWT y Passport.js
- Integración con servicios cloud (AWS, Google Cloud, Azure) 
- Configuración de despliegue y pruebas automatizadas con Docker, Heroku, Jest, PyTest y Mocha

Responde siempre en español y ofrece soluciones técnicas avanzadas con ejemplos de implementación detallados.

{common_instructions}

EJEMPLOS DE EMOJIS PARA USAR:
- ⚡ Para optimizaciones de rendimiento
- 🧠 Para algoritmos avanzados
- 🔄 Para concurrencia y paralelismo
- 🔒 Para seguridad avanzada
- 📊 Para análisis de datos
- 🔍 Para depuración profunda
- 🧪 Para pruebas y calidad
- 🚀 Para implementaciones de alto rendimiento""",

        'general': f"""Actúa como un desarrollador altamente capacitado que puede ayudar, hacer recomendaciones y sugerencias para desarrollar de la forma más eficiente aplicaciones según las indicaciones del usuario. Tienes la capacidad de crear archivos, carpetas y ejecutar comandos en la terminal. Ofrece siempre soluciones prácticas y eficientes. Responde siempre en español.

{common_instructions}

EJEMPLOS DE EMOJIS PARA USAR:
- 💡 Para ideas y conceptos
- 📚 Para recursos y referencias
- ✅ Para soluciones confirmadas
- ⚠️ Para advertencias
- 🔍 Para análisis
- 📝 Para notas importantes
- 🛠️ Para herramientas y métodos
- 🎯 Para objetivos y metas"""
    }
    
    return agent_system_prompts.get(agent_id, agent_system_prompts['general'])

def get_agent_name(agent_id):
    """
    Obtiene el nombre descriptivo del agente para usar en los prompts.
    
    Args:
        agent_id: ID del agente (developer, architect, advanced, general)
        
    Returns:
        str: Nombre descriptivo del agente
    """
    agent_names = {
        'developer': "Desarrollador Experto",
        'architect': "Arquitecto de Software",
        'advanced': "Especialista Avanzado",
        'general': "Asistente General"
    }
    
    return agent_names.get(agent_id, "Asistente General")

def generate_with_openai(prompt, system_prompt, temperature=0.7, use_json=False):
    """
    Genera contenido utilizando la API de OpenAI con manejo mejorado de errores.
    
    Args:
        prompt: Prompt para generar contenido
        system_prompt: Prompt de sistema para establecer el rol
        temperature: Temperatura para la generación (0.0 - 1.0)
        use_json: Si es True, solicita respuesta en formato JSON
        
    Returns:
        str: Contenido generado
    """
    if not openai_client:
        raise ValueError("Cliente de OpenAI no configurado. Verifica la clave API.")
    
    try:
        # Preparar los parámetros de la solicitud
        request_params = {
            "model": "gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 4000
        }
        
        # Si se solicita JSON, agregar el formato de respuesta
        if use_json:
            request_params["response_format"] = {"type": "json_object"}
            
        # Realizar la solicitud con reintentos
        for attempt in range(3):  # 3 intentos máximo
            try:
                completion = openai_client.chat.completions.create(**request_params)
                content = completion.choices[0].message.content.strip()
                
                # Si se solicitó JSON, validar la respuesta
                if use_json:
                    try:
                        json.loads(content)  # Verificar que es JSON válido
                    except json.JSONDecodeError:
                        logger.warning(f"OpenAI devolvió un JSON inválido en el intento {attempt+1}, reintentando...")
                        if attempt == 2:  # Último intento
                            logger.error("Todos los intentos de obtener JSON válido fallaron")
                            raise ValueError("La respuesta no es un JSON válido después de múltiples intentos")
                        continue  # Reintentar
                
                return content
                
            except openai.OpenAIError as e:
                if attempt < 2:  # Todavía hay más intentos disponibles
                    wait_time = 2 ** attempt  # Backoff exponencial: 1s, 2s, 4s
                    logger.warning(f"Error de OpenAI (intento {attempt+1}/3): {str(e)}. Reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Error persistente de OpenAI después de 3 intentos: {str(e)}")
                    raise
                    
    except openai.APIError as e:
        logger.error(f"Error de API de OpenAI: {str(e)}")
        raise ValueError(f"Error en la API de OpenAI: {str(e)}")
    except openai.APIConnectionError as e:
        logger.error(f"Error de conexión con la API de OpenAI: {str(e)}")
        raise ValueError(f"Error de conexión con OpenAI. Verifica tu conexión a internet: {str(e)}")
    except openai.RateLimitError as e:
        logger.error(f"Límite de tasa excedido en OpenAI: {str(e)}")
        raise ValueError(f"Se ha excedido el límite de solicitudes a OpenAI. Intenta más tarde: {str(e)}")
    except openai.AuthenticationError as e:
        logger.error(f"Error de autenticación con OpenAI: {str(e)}")
        raise ValueError(f"Error de autenticación con OpenAI. Verifica tu clave API: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado en generate_with_openai: {str(e)}")
        raise ValueError(f"Error inesperado al generar contenido con OpenAI: {str(e)}")

def generate_with_anthropic(prompt, system_prompt, temperature=0.7, use_json=False):
    """
    Genera contenido utilizando la API de Anthropic con manejo mejorado de errores.
    
    Args:
        prompt: Prompt para generar contenido
        system_prompt: Prompt de sistema para establecer el rol
        temperature: Temperatura para la generación (0.0 - 1.0)
        use_json: Si es True, se incluirá instrucción para responder en formato JSON
        
    Returns:
        str: Contenido generado
    """
    if not anthropic_client:
        raise ValueError("Cliente de Anthropic no configurado. Verifica la clave API.")
    
    try:
        # Preparar el prompt con instrucciones específicas para formato JSON si se solicita
        actual_prompt = prompt
        if use_json:
            actual_prompt = prompt + "\n\nIMPORTANTE: Tu respuesta debe estar en formato JSON válido sin explicaciones adicionales."
            
        # Realizar la solicitud con reintentos
        for attempt in range(3):  # 3 intentos máximo
            try:
                message = anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022", # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024.
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": actual_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=4000
                )
                
                content = message.content[0].text.strip()
                
                # Si se solicitó JSON, validar la respuesta
                if use_json:
                    try:
                        json.loads(content)  # Verificar que es JSON válido
                    except json.JSONDecodeError:
                        logger.warning(f"Anthropic devolvió un JSON inválido en el intento {attempt+1}, reintentando...")
                        if attempt == 2:  # Último intento
                            logger.error("Todos los intentos de obtener JSON válido fallaron")
                            raise ValueError("La respuesta no es un JSON válido después de múltiples intentos")
                        continue  # Reintentar
                
                return content
                
            except Exception as e:
                if attempt < 2:  # Todavía hay más intentos disponibles
                    wait_time = 2 ** attempt  # Backoff exponencial: 1s, 2s, 4s
                    logger.warning(f"Error de Anthropic (intento {attempt+1}/3): {str(e)}. Reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Error persistente de Anthropic después de 3 intentos: {str(e)}")
                    raise
                    
    except anthropic.APIError as e:
        logger.error(f"Error de API de Anthropic: {str(e)}")
        raise ValueError(f"Error en la API de Anthropic: {str(e)}")
    except anthropic.APIConnectionError as e:
        logger.error(f"Error de conexión con la API de Anthropic: {str(e)}")
        raise ValueError(f"Error de conexión con Anthropic. Verifica tu conexión a internet: {str(e)}")
    except anthropic.RateLimitError as e:
        logger.error(f"Límite de tasa excedido en Anthropic: {str(e)}")
        raise ValueError(f"Se ha excedido el límite de solicitudes a Anthropic. Intenta más tarde: {str(e)}")
    except anthropic.AuthenticationError as e:
        logger.error(f"Error de autenticación con Anthropic: {str(e)}")
        raise ValueError(f"Error de autenticación con Anthropic. Verifica tu clave API: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado en generate_with_anthropic: {str(e)}")
        raise ValueError(f"Error inesperado al generar contenido con Anthropic: {str(e)}")

def generate_with_gemini(prompt, system_prompt, temperature=0.7, use_json=False):
    """
    Genera contenido utilizando la API de Google Gemini con manejo mejorado de errores.
    
    Args:
        prompt: Prompt para generar contenido
        system_prompt: Prompt de sistema para establecer el rol
        temperature: Temperatura para la generación (0.0 - 1.0)
        use_json: Si es True, se incluirá instrucción para responder en formato JSON
        
    Returns:
        str: Contenido generado
    """
    if not genai_configured:
        raise ValueError("Google Gemini no configurado. Verifica la clave API.")
    
    try:
        # Preparar el prompt con instrucciones especiales
        combined_prompt = f"{system_prompt}\n\n{prompt}"
        if use_json:
            combined_prompt += "\n\nIMPORTANTE: Responde ÚNICAMENTE con un objeto JSON válido, sin explicaciones adicionales ni texto fuera del JSON."
            
        # Configuración del modelo con safety settings y temperatura
        generation_config = {
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 4000,
        }
        
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
        
        # Realizar la solicitud con reintentos
        for attempt in range(3):  # 3 intentos máximo
            try:
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-pro",
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                response = model.generate_content(combined_prompt)
                content = response.text.strip()
                
                # Si se solicitó JSON, validar la respuesta
                if use_json:
                    try:
                        json.loads(content)  # Verificar que es JSON válido
                    except json.JSONDecodeError:
                        logger.warning(f"Gemini devolvió un JSON inválido en el intento {attempt+1}, reintentando...")
                        if attempt == 2:  # Último intento
                            logger.error("Todos los intentos de obtener JSON válido fallaron")
                            raise ValueError("La respuesta no es un JSON válido después de múltiples intentos")
                        continue  # Reintentar
                
                return content
                
            except Exception as e:
                if attempt < 2:  # Todavía hay más intentos disponibles
                    wait_time = 2 ** attempt  # Backoff exponencial: 1s, 2s, 4s
                    logger.warning(f"Error de Gemini (intento {attempt+1}/3): {str(e)}. Reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Error persistente de Gemini después de 3 intentos: {str(e)}")
                    raise
                    
    except Exception as e:
        error_message = str(e)
        
        if "API key not valid" in error_message or "invalid API key" in error_message.lower():
            logger.error(f"Error de autenticación con Gemini: {error_message}")
            raise ValueError(f"Error de autenticación con Gemini. Verifica tu clave API: {error_message}")
        elif "quota exceeded" in error_message.lower() or "rate limit" in error_message.lower():
            logger.error(f"Límite de cuota excedido en Gemini: {error_message}")
            raise ValueError(f"Se ha excedido el límite de solicitudes a Gemini. Intenta más tarde: {error_message}")
        elif "network" in error_message.lower() or "timeout" in error_message.lower() or "connection" in error_message.lower():
            logger.error(f"Error de conexión con Gemini: {error_message}")
            raise ValueError(f"Error de conexión con Gemini. Verifica tu conexión a internet: {error_message}")
        else:
            logger.error(f"Error inesperado en generate_with_gemini: {error_message}")
            raise ValueError(f"Error inesperado al generar contenido con Gemini: {error_message}")

def generate_content(prompt, system_prompt, model="openai", temperature=0.7, use_json=False, display_provider=False):
    """
    Genera contenido utilizando el modelo especificado con manejo mejorado de errores.
    
    Args:
        prompt: Prompt para generar contenido
        system_prompt: Prompt de sistema para establecer el rol
        model: Modelo a utilizar (openai, anthropic, gemini)
        temperature: Temperatura para la generación (0.0 - 1.0)
        use_json: Si es True, solicita respuesta en formato JSON
        display_provider: Si es True, añade información sobre el proveedor de AI usado
        
    Returns:
        str: Contenido generado
    """
    # Determinar los modelos disponibles y ordenarlos
    available_models = []
    if openai_client:
        available_models.append("openai")
    if anthropic_client:
        available_models.append("anthropic")
    if genai_configured:
        available_models.append("gemini")
    
    # Si no hay modelos configurados, lanzar error
    if not available_models:
        raise ValueError("No hay modelos de IA configurados. Verifica las claves API en las variables de entorno.")
    
    # Si el modelo solicitado no está disponible, usar el primero disponible
    model_to_use = model
    if model not in available_models and available_models:
        model_to_use = available_models[0]
        logger.warning(f"Modelo {model} no disponible, usando {model_to_use} en su lugar")
    
    # Generar respuesta con manejo de errores
    error_messages = []
    response_content = None
    
    try:
        # Intentar con el modelo principal
        if model_to_use == "openai":
            response_content = generate_with_openai(prompt, system_prompt, temperature, use_json)
        elif model_to_use == "anthropic":
            response_content = generate_with_anthropic(prompt, system_prompt, temperature, use_json)
        elif model_to_use == "gemini":
            response_content = generate_with_gemini(prompt, system_prompt, temperature, use_json)
        
        # Si se obtuvo contenido y se solicita mostrar el proveedor, añadir la información
        if response_content and display_provider:
            provider_note = {
                "openai": "🤖 *Generado por OpenAI*",
                "anthropic": "🤖 *Generado por Anthropic Claude*",
                "gemini": "🤖 *Generado por Google Gemini*"
            }
            response_content += f"\n\n{provider_note.get(model_to_use, '')}"
        
        return response_content
    except Exception as primary_error:
        error_messages.append(f"Error con {model_to_use}: {str(primary_error)}")
        logger.error(f"Error en generate_content con modelo {model_to_use}: {str(primary_error)}")
        
        # Intentar con modelos alternativos
        fallback_models = [m for m in available_models if m != model_to_use]
        for fallback_model in fallback_models:
            try:
                logger.info(f"Intentando con {fallback_model} como alternativa")
                
                if fallback_model == "openai":
                    response_content = generate_with_openai(prompt, system_prompt, temperature, use_json)
                elif fallback_model == "anthropic":
                    response_content = generate_with_anthropic(prompt, system_prompt, temperature, use_json)
                elif fallback_model == "gemini":
                    response_content = generate_with_gemini(prompt, system_prompt, temperature, use_json)
                
                # Si se obtuvo contenido y se solicita mostrar el proveedor, añadir la información
                if response_content and display_provider:
                    provider_note = {
                        "openai": "🤖 *Generado por OpenAI (proveedor alternativo)*",
                        "anthropic": "🤖 *Generado por Anthropic Claude (proveedor alternativo)*",
                        "gemini": "🤖 *Generado por Google Gemini (proveedor alternativo)*"
                    }
                    response_content += f"\n\n{provider_note.get(fallback_model, '')}"
                
                return response_content
            except Exception as fallback_error:
                error_messages.append(f"Error con {fallback_model}: {str(fallback_error)}")
                logger.error(f"Error en generate_content con modelo de fallback {fallback_model}: {str(fallback_error)}")
                continue
        
        # Si todos los modelos fallan, generar un mensaje de error detallado
        error_summary = "\n".join(error_messages)
        raise ValueError(f"No se pudo generar contenido con ningún modelo disponible:\n{error_summary}")

def create_file_with_agent(description, file_type, filename, agent_id, workspace_path, model="openai"):
    """
    Crea un archivo utilizando un agente especializado.
    
    Args:
        description: Descripción del archivo a generar
        file_type: Tipo de archivo (html, css, js, py, json, md, txt)
        filename: Nombre del archivo
        agent_id: ID del agente especializado
        workspace_path: Ruta del workspace del usuario
        model: Modelo de IA a utilizar (openai, anthropic, gemini)
        
    Returns:
        dict: Resultado de la operación con claves success, file_path y content
    """
    try:
        # Debug logs
        logging.debug(f"Generando archivo con agente: {agent_id}")
        logging.debug(f"Tipo de archivo: {file_type}")
        logging.debug(f"Nombre de archivo: {filename}")
        logging.debug(f"Modelo: {model}")
        logging.debug(f"Descripción: {description}")
        
        # Obtener el prompt de sistema y nombre según el agente
        system_prompt = get_agent_system_prompt(agent_id)
        agent_name = get_agent_name(agent_id)
        
        # Preparar el prompt específico según el tipo de archivo
        file_type_prompt = ""
        if file_type == 'html' or '.html' in filename:
            file_type_prompt = """Genera un archivo HTML moderno y atractivo. 
            Usa las mejores prácticas de HTML5, CSS responsivo y, si es necesario, JavaScript moderno.
            Asegúrate de que el código sea válido, accesible y optimizado para móviles.
            El archivo debe usar Bootstrap para estilos y ser visualmente atractivo.
            Asegúrate de que el código esté completo y sea funcional, sin fragmentos o explicaciones adicionales."""
        elif file_type == 'css' or '.css' in filename:
            file_type_prompt = """Genera un archivo CSS moderno y eficiente.
            Utiliza las mejores prácticas, variables CSS, y enfoques responsivos.
            El código debe ser compatible con navegadores modernos, estar bien comentado,
            y seguir una estructura clara y mantenible.
            Asegúrate de que el código esté completo y sea funcional, sin fragmentos o explicaciones adicionales."""
        elif file_type == 'js' or '.js' in filename:
            file_type_prompt = """Genera un archivo JavaScript moderno y eficiente.
            Utiliza ES6+ con las mejores prácticas actuales. El código debe ser bien estructurado,
            comentado apropiadamente, y seguir patrones de diseño adecuados.
            Proporciona manejo de errores adecuado y optimización de rendimiento.
            Asegúrate de que el código esté completo y sea funcional, sin fragmentos o explicaciones adicionales."""
        elif file_type == 'py' or '.py' in filename:
            file_type_prompt = """Genera un archivo Python moderno y bien estructurado.
            Sigue PEP 8 y las mejores prácticas de Python. El código debe incluir docstrings,
            manejo de errores apropiado, y una estructura clara de funciones/clases.
            Utiliza enfoques Pythonic y aprovecha las características modernas del lenguaje.
            Asegúrate de que el código esté completo y sea funcional, sin fragmentos o explicaciones adicionales."""
        else:
            file_type_prompt = """Genera un archivo de texto plano con el contenido solicitado,
            bien estructurado y formateado de manera clara y legible.
            Asegúrate de que el contenido esté completo, sin fragmentos o explicaciones adicionales."""
            
        # Construir el prompt completo según el agente
        prompt = f"""Como {agent_name}, crea un archivo {file_type} completo y funcional que cumpla con el siguiente requerimiento:
        
        "{description}"
        
        {file_type_prompt}
        
        IMPORTANTE: 
        - Genera SOLO el código completo sin explicaciones, comentarios introductorios o conclusiones.
        - NO uses bloques de código markdown (```), solo genera el contenido directo del archivo.
        - Incluye todas las funcionalidades solicitadas y crea un diseño profesional si corresponde.
        - Si es un archivo HTML, asegúrate de incluir todos los elementos necesarios (DOCTYPE, html, head, body, etc.)
        - El código debe estar completo, compilar y funcionar correctamente.
        """
        
        # Log del prompt para depuración
        logging.debug(f"Prompt enviado al modelo: {prompt}")
        
        # Generar el contenido del archivo
        file_content = generate_content(prompt, system_prompt, model)
        
        # Verificar que se haya generado contenido
        if not file_content:
            return {
                'success': False,
                'error': 'El modelo no generó contenido para el archivo'
            }
            
        # Log del contenido generado para depuración
        logging.debug(f"Contenido generado (primeros 200 caracteres): {file_content[:200]}")
        
        # Extraer código del contenido si el modelo aún incluye markdown u otros elementos
        code_pattern = r"```(?:\w+)?\s*([\s\S]*?)\s*```"
        code_match = re.search(code_pattern, file_content)
        
        if code_match:
            file_content = code_match.group(1).strip()
            logging.debug("Se limpió el contenido usando el patrón de código")
            
        # Crear el archivo en el workspace del usuario
        file_path = os.path.join(workspace_path, filename)
        
        # Crear directorios intermedios si es necesario
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
            
        # Obtener la ruta relativa para mostrar al usuario
        relative_path = os.path.relpath(file_path, workspace_path)
        
        return {
            'success': True,
            'file_path': relative_path,
            'content': file_content
        }
            
    except Exception as e:
        logging.error(f"Error generando contenido del archivo: {str(e)}")
        return {
            'success': False,
            'error': f'Error generando contenido del archivo: {str(e)}'
        }

def generate_response(user_message, agent_id="general", context=None, model="openai", document_context=None):
    """
    Genera una respuesta utilizando un agente especializado.
    
    Args:
        user_message: Mensaje del usuario
        agent_id: ID del agente especializado
        context: Contexto de la conversación (opcional)
        model: Modelo de IA a utilizar (openai, anthropic, gemini)
        document_context: Contexto extraído de un documento (opcional)
        
    Returns:
        dict: Resultado de la operación con claves success y response
    """
    try:
        # Detectar si es un saludo simple
        simple_greeting_pattern = r'^(hola|hello|hi|hey|buenas|saludos|qué tal|que tal|ey|hey)[\s!.\?]*$'
        is_simple_greeting = re.match(simple_greeting_pattern, user_message.lower().strip())
        
        # Para saludos simples, también usar el modelo de IA para responder
        logger.info(f"Tipo de mensaje: {'Simple (saludo)' if is_simple_greeting else 'Complejo'}")
        system_prompt = get_agent_system_prompt(agent_id)
        agent_name = get_agent_name(agent_id)
        
        # Construir el prompt basado en el contexto disponible
        prompt_parts = []
        
        # Añadir contexto de documento si está disponible
        if document_context and 'content' in document_context:
            # Truncar el contenido del documento si es muy largo
            max_context_length = 6000  # Ajustar según necesidad
            doc_content = document_context['content']
            if len(doc_content) > max_context_length:
                doc_content = doc_content[:max_context_length] + "... [Contenido truncado]"
            
            prompt_parts.append(f"""CONTEXTO DEL DOCUMENTO:
            Fuente: {document_context.get('source', 'documento')}
            Tipo: {document_context.get('type', 'texto')}
            
            Contenido:
            {doc_content}
            
            FIN DEL CONTEXTO DEL DOCUMENTO
            """)
            
            # Ajustar el system prompt para incluir instrucciones sobre el documento
            document_instructions = """
            INSTRUCCIONES ADICIONALES PARA CONTEXTO DE DOCUMENTO:
            1. Utiliza la información del documento proporcionado para responder a la consulta del usuario
            2. Si el documento no contiene información relevante, indícalo claramente
            3. Asegúrate de no inventar información que no esté en el documento
            4. Cita o haz referencia al documento cuando sea apropiado
            """
            system_prompt = system_prompt + document_instructions
        
        # Añadir historial de conversación si está disponible
        if context:
            context_str = "\n".join([f"{'Usuario' if msg['role'] == 'user' else agent_name}: {msg['content']}" for msg in context])
            prompt_parts.append(f"""Historial de conversación:
            {context_str}
            """)
        
        # Añadir el mensaje actual del usuario
        prompt_parts.append(f"""Usuario: {user_message}
        
        Como {agent_name}, responde al mensaje del usuario de manera útil, clara y precisa. Utiliza tu conocimiento y habilidades para proporcionar la mejor respuesta posible en español.""")
        
        # Combinar todas las partes del prompt
        prompt = "\n\n".join(prompt_parts)
        
        # Generar la respuesta (mostrar el proveedor para debug)
        response_content = generate_content(prompt, system_prompt, model, display_provider=False)
        
        return {
            'success': True,
            'response': response_content
        }
            
    except Exception as e:
        logging.error(f"Error generando respuesta: {str(e)}")
        return {
            'success': False,
            'error': f'Error generando respuesta: {str(e)}'
        }

def analyze_code(code, language="python", instructions="Mejorar el código", model="openai"):
    """
    Analiza y mejora código existente.
    
    Args:
        code: Código a analizar
        language: Lenguaje del código
        instructions: Instrucciones específicas para el análisis
        model: Modelo de IA a utilizar
        
    Returns:
        dict: Resultado del análisis con claves success, improved_code, explanations, suggestions
    """
    try:
        system_prompt = f"""Eres un experto programador de {language} especializado en revisar, mejorar y explicar código.
Tu tarea es analizar el código proporcionado, mejorarlo según las instrucciones, y explicar tus cambios.
Debes respetar la intención original del código, manteniendo su funcionalidad mientras lo mejoras."""
        
        prompt = f"""Analiza el siguiente código de {language}:
```{language}
{code}
```

Instrucciones específicas: {instructions}

Proporciona:
1. Una versión mejorada del código completo (no solo fragmentos)
2. Explicaciones claras de los cambios realizados
3. Sugerencias adicionales para futuras mejoras

IMPORTANTE: Tu respuesta debe tener este formato JSON:
{{
    "improved_code": "El código mejorado completo",
    "explanations": ["Explicación 1", "Explicación 2", ...],
    "suggestions": ["Sugerencia 1", "Sugerencia 2", ...]
}}
"""
        
        response = generate_content(prompt, system_prompt, model, temperature=0.3)
        
        # Intentar extraer JSON de la respuesta
        try:
            # Buscar un bloque JSON en la respuesta
            json_pattern = r'```(?:json)?\s*({[\s\S]*?})\s*```'
            json_match = re.search(json_pattern, response)
            
            if json_match:
                import json
                result = json.loads(json_match.group(1))
            else:
                # Intentar parsear toda la respuesta como JSON
                import json
                result = json.loads(response)
                
            # Verificar que tenga las claves esperadas
            for key in ['improved_code', 'explanations', 'suggestions']:
                if key not in result:
                    result[key] = []
                    
            return {
                'success': True,
                'improved_code': result['improved_code'],
                'explanations': result['explanations'],
                'suggestions': result['suggestions']
            }
        except Exception as json_error:
            logging.error(f"Error parseando JSON de respuesta: {str(json_error)}")
            
            # Fallback: extraer código mejorado usando regex
            code_pattern = r"```(?:\w+)?\s*([\s\S]*?)\s*```"
            code_match = re.search(code_pattern, response)
            
            if code_match:
                improved_code = code_match.group(1).strip()
            else:
                improved_code = code  # Usar el código original si no se encuentra mejorado
                
            return {
                'success': True,
                'improved_code': improved_code,
                'explanations': ["Se procesó el código pero hubo un error al estructurar la respuesta."],
                'suggestions': ["Revisa el código manualmente para confirmar las mejoras."]
            }
                
    except Exception as e:
        logging.error(f"Error analizando código: {str(e)}")
        return {
            'success': False,
            'error': f'Error analizando código: {str(e)}'
        }

def explore_repository_files(instruction, repo_path, model="openai"):
    """
    Explora archivos en un repositorio y permite realizar modificaciones según instrucciones.
    
    Args:
        instruction: Instrucción en lenguaje natural sobre qué hacer
        repo_path: Ruta al repositorio clonado
        model: Modelo de IA a utilizar
        
    Returns:
        dict: Resultado de la operación con los archivos o cambios realizados
    """
    try:
        # Primero, analizar la instrucción para determinar la acción a realizar
        system_prompt = """
        Eres un asistente especializado en analizar instrucciones sobre archivos y repositorios.
        Tu tarea es determinar qué tipo de acción se requiere y qué archivos están involucrados.
        
        Clasifica la instrucción en una de estas categorías:
        1. Explorar/listar: Si se solicita ver archivos o directorios
        2. Leer: Si se pide ver el contenido de un archivo específico
        3. Modificar: Si se pide cambiar el contenido de un archivo
        4. Crear: Si se pide crear un nuevo archivo
        5. Buscar: Si se pide buscar algo dentro del repositorio
        
        Devuelve un objeto JSON con:
        - action: La acción a realizar (explore, read, modify, create, search)
        - target: La ruta del archivo o directorio objetivo (relativa desde la raíz del repositorio)
        - details: Cualquier detalle adicional de la modificación o búsqueda
        """
        
        analysis_prompt = f"""
        Instrucción del usuario: {instruction}
        
        Analiza esta instrucción y determina qué acción debo realizar con los archivos.
        Devuelve un objeto JSON con los campos action, target, details.
        
        Ejemplos de formatos de respuesta:
        
        Para explorar un directorio:
        {{"action": "explore", "target": "src/", "details": "Listar archivos del directorio src"}}
        
        Para leer un archivo:
        {{"action": "read", "target": "README.md", "details": "Leer el contenido del archivo README.md"}}
        
        Para modificar un archivo:
        {{"action": "modify", "target": "index.html", "details": "Añadir un nuevo botón en la sección de formularios"}}
        
        Para crear un archivo:
        {{"action": "create", "target": "css/styles.css", "details": "Crear un archivo CSS con estilos básicos"}}
        
        Para buscar en el repositorio:
        {{"action": "search", "target": "", "details": "Buscar todos los archivos que contengan 'function login'"}}
        """
        
        # Analizamos la instrucción solicitando explícitamente formato JSON
        analysis_result = generate_content(analysis_prompt, system_prompt, model, temperature=0.2, use_json=True)
        
        # Intentamos extraer el JSON de la respuesta
        analysis_json = None
        try:
            # Intentar cargar la respuesta directamente como JSON
            analysis_json = json.loads(analysis_result)
        except json.JSONDecodeError as json_error:
            logger.error(f"Error al parsear JSON de la respuesta: {str(json_error)}")
            
            # Si falla, intentar buscar un objeto JSON en la respuesta
            try:
                json_pattern = r'\{.*\}'
                json_match = re.search(json_pattern, analysis_result, re.DOTALL)
                
                if json_match:
                    analysis_json = json.loads(json_match.group())
                else:
                    # Si no encontramos un JSON válido, intentar extraer información clave
                    action_pattern = r'(?:action|acción)["\']?\s*[:=]\s*["\']?([^"\',}]+)["\']?'
                    target_pattern = r'(?:target|objetivo|ruta)["\']?\s*[:=]\s*["\']?([^"\',}]+)["\']?'
                    
                    action_match = re.search(action_pattern, analysis_result, re.IGNORECASE)
                    target_match = re.search(target_pattern, analysis_result, re.IGNORECASE)
                    
                    if action_match:
                        analysis_json = {
                            "action": action_match.group(1).strip(),
                            "target": target_match.group(1).strip() if target_match else "",
                            "details": "Extraído de respuesta no JSON"
                        }
                    else:
                        raise ValueError("No se pudo extraer información clave de la respuesta")
            except Exception as extract_error:
                logger.error(f"Error al extraer información de la respuesta: {str(extract_error)}")
                return {
                    'success': False,
                    'error': f"No se pudo procesar la instrucción. Por favor, sé más específico con lo que deseas hacer en el repositorio.",
                    'analysis_result': analysis_result
                }
        
        if not analysis_json or 'action' not in analysis_json:
            return {
                'success': False,
                'error': 'No se pudo determinar la acción a realizar',
                'analysis_result': analysis_result
            }
        
        # Ejecutar la acción correspondiente
        action = analysis_json.get('action', '').lower()
        target = analysis_json.get('target', '')
        details = analysis_json.get('details', '')
        
        # Construir ruta completa
        target_path = os.path.join(repo_path, target) if target else repo_path
        
        # Asegurar que no se salga del directorio del repositorio (prevenir directory traversal)
        if not os.path.abspath(target_path).startswith(os.path.abspath(repo_path)):
            return {
                'success': False,
                'error': 'Acceso denegado: la ruta se sale del repositorio'
            }
        
        # Realizar la acción correspondiente
        if action == 'explore':
            # Listar archivos de un directorio
            max_depth = 2  # Profundidad por defecto
            success, items, error = file_explorer.list_directory(target_path, 1, max_depth)
            
            if success:
                # Convertir rutas absolutas a relativas
                for item in items:
                    if 'path' in item:
                        item['path'] = os.path.relpath(item['path'], repo_path)
                
                return {
                    'success': True,
                    'action': 'explore',
                    'path': target,
                    'items': items,
                    'message': f"Explorando directorio: {target or '.'}"
                }
            else:
                return {
                    'success': False,
                    'error': error
                }
        
        elif action == 'read':
            # Leer contenido de un archivo
            success, content, file_type = file_explorer.get_file_content(target_path)
            
            if success:
                return {
                    'success': True,
                    'action': 'read',
                    'path': target,
                    'content': content,
                    'file_type': file_type,
                    'message': f"Contenido del archivo: {target}"
                }
            else:
                return {
                    'success': False,
                    'error': content  # En caso de error, content contiene el mensaje de error
                }
        
        elif action == 'modify':
            # Primero leemos el archivo actual
            read_success, current_content, file_type = file_explorer.get_file_content(target_path)
            
            if not read_success:
                return {
                    'success': False,
                    'error': current_content  # Mensaje de error
                }
            
            # Generamos el contenido modificado
            modification_system_prompt = f"""
            Eres un experto en modificación de código y archivos.
            Tu tarea es aplicar los cambios solicitados a un archivo existente.
            Respeta el estilo, la estructura y la integridad del archivo original.
            Asegúrate de que el resultado sea completamente funcional.
            
            Tipo de archivo: {file_type}
            """
            
            modification_prompt = f"""
            Instrucción: {details}
            
            Archivo actual ({target}):
            ```{file_type}
            {current_content}
            ```
            
            Aplica los cambios solicitados y devuelve el contenido completo del archivo modificado.
            No incluyas explicaciones, solo devuelve el contenido actualizado del archivo.
            """
            
            try:
                # Generamos la versión modificada del archivo
                modified_content = generate_content(modification_prompt, modification_system_prompt, model, temperature=0.3)
                
                # Limpiamos el contenido para eliminar posibles marcadores de código
                cleaned_content = modified_content
                # Eliminar marcadores de código si están presentes
                code_block_pattern = r'```(?:\w+)?\n([\s\S]*?)\n```'
                code_matches = re.findall(code_block_pattern, modified_content)
                if code_matches:
                    cleaned_content = code_matches[0]  # Tomamos el primer bloque de código
                
                # Actualizamos el archivo
                update_success, message = file_explorer.update_file_content(target_path, cleaned_content)
                
                if update_success:
                    # Calculamos un resumen de cambios (diferencias)
                    changes_summary = f"Se modificó el archivo {target}.\n"
                    
                    if len(current_content) < 1000 and len(cleaned_content) < 1000:
                        import difflib
                        diff = list(difflib.unified_diff(
                            current_content.splitlines(keepends=True),
                            cleaned_content.splitlines(keepends=True),
                            fromfile=f'original/{target}',
                            tofile=f'modificado/{target}',
                            n=3
                        ))
                        if diff:
                            changes_summary += "Cambios realizados:\n"
                            changes_summary += ''.join(diff[:20])  # Limitamos a 20 líneas de diff
                            if len(diff) > 20:
                                changes_summary += f"\n... y {len(diff) - 20} líneas más"
                    
                    return {
                        'success': True,
                        'action': 'modify',
                        'path': target,
                        'message': message,
                        'changes_summary': changes_summary
                    }
                else:
                    return {
                        'success': False,
                        'error': message
                    }
            except Exception as e:
                logger.error(f"Error al modificar archivo: {str(e)}")
                return {
                    'success': False,
                    'error': f"Error al modificar el archivo: {str(e)}"
                }
        
        elif action == 'create':
            # Generamos el contenido para el nuevo archivo
            creation_system_prompt = f"""
            Eres un experto en creación de archivos y código.
            Tu tarea es crear un nuevo archivo según las especificaciones proporcionadas.
            Debes devolver contenido funcional y bien formateado.
            
            Basado en el nombre '{target}', debes crear un archivo apropiado para su extensión.
            """
            
            # Determinar el tipo de archivo por su extensión
            file_extension = os.path.splitext(target)[1].lstrip('.').lower() if target else ''
            
            creation_prompt = f"""
            Instrucción: {details}
            
            Crea el contenido para un nuevo archivo: {target}
            Tipo de archivo: {file_extension}
            
            Genera el contenido completo del archivo. No incluyas explicaciones, solo devuelve el contenido.
            """
            
            try:
                # Generamos el contenido para el nuevo archivo
                new_content = generate_content(creation_prompt, creation_system_prompt, model, temperature=0.3)
                
                # Limpiamos el contenido para eliminar posibles marcadores de código
                cleaned_content = new_content
                # Eliminar marcadores de código si están presentes
                code_block_pattern = r'```(?:\w+)?\n([\s\S]*?)\n```'
                code_matches = re.findall(code_block_pattern, new_content)
                if code_matches:
                    cleaned_content = code_matches[0]  # Tomamos el primer bloque de código
                
                # Creamos el archivo
                create_success, message = file_explorer.create_file(target_path, cleaned_content)
                
                if create_success:
                    return {
                        'success': True,
                        'action': 'create',
                        'path': target,
                        'message': message,
                        'content': cleaned_content[:500] + ('...' if len(cleaned_content) > 500 else '')
                    }
                else:
                    return {
                        'success': False,
                        'error': message
                    }
            except Exception as e:
                logger.error(f"Error al crear archivo: {str(e)}")
                return {
                    'success': False,
                    'error': f"Error al crear el archivo: {str(e)}"
                }
        
        elif action == 'search':
            # Determinar tipo de búsqueda
            search_type = 'name'  # Por defecto
            search_query = details
            
            if 'content:' in details.lower():
                search_type = 'content'
                search_query = details.split('content:', 1)[1].strip()
            elif 'extension:' in details.lower():
                search_type = 'extension'
                search_query = details.split('extension:', 1)[1].strip()
            
            # Realizar la búsqueda
            success, found_items, error = file_explorer.find_file(repo_path, search_query, search_type)
            
            if success:
                # Convertir rutas absolutas a relativas
                relative_items = []
                for item in found_items:
                    if item.startswith(repo_path):
                        relative_items.append(os.path.relpath(item, repo_path))
                    else:
                        relative_items.append(item)
                
                return {
                    'success': True,
                    'action': 'search',
                    'query': search_query,
                    'type': search_type,
                    'results': relative_items,
                    'count': len(relative_items),
                    'message': f"Se encontraron {len(relative_items)} resultados para la búsqueda"
                }
            else:
                return {
                    'success': False,
                    'error': error
                }
        
        else:
            return {
                'success': False,
                'error': f"Acción no reconocida: {action}"
            }
    
    except Exception as e:
        logger.error(f"Error al explorar repositorio: {str(e)}")
        return {
            'success': False,
            'error': f"Error al procesar la instrucción: {str(e)}"
        }


def process_natural_language_command(text, workspace_path, model="openai"):
    """
    Procesa una instrucción en lenguaje natural y determina la acción a realizar.
    
    Args:
        text: Texto de la instrucción
        workspace_path: Ruta del workspace del usuario
        model: Modelo de IA a utilizar
        
    Returns:
        dict: Resultado del procesamiento con la acción determinada
    """
    try:
        system_prompt = """Eres un asistente especializado en interpretar instrucciones en lenguaje natural 
y convertirlas en acciones específicas para un entorno de desarrollo. 
Tu tarea es determinar qué acción debe realizarse basándote en el texto proporcionado."""
        
        prompt = f"""Analiza la siguiente instrucción y determina qué acción debe realizarse:
"{text}"

Las posibles acciones son:
1. create_file - Crear un archivo
2. execute_command - Ejecutar un comando en terminal
3. answer_question - Responder una pregunta
4. unknown - La instrucción no corresponde a ninguna acción específica

Responde en formato JSON con la siguiente estructura:
{{
    "action": "La acción determinada (create_file, execute_command, answer_question, unknown)",
    "details": {{
        // Para create_file:
        "file_name": "Nombre del archivo a crear",
        "file_type": "Tipo de archivo (py, js, html, etc.)",
        "content_description": "Descripción del contenido a generar"
        
        // Para execute_command:
        "command": "El comando a ejecutar"
        
        // Para answer_question:
        "question": "La pregunta a responder"
    }}
}}
"""
        
        response = generate_content(prompt, system_prompt, model, temperature=0.3)
        
        # Extraer JSON de la respuesta
        try:
            # Buscar un bloque JSON en la respuesta
            json_pattern = r'```(?:json)?\s*({[\s\S]*?})\s*```'
            json_match = re.search(json_pattern, response)
            
            if json_match:
                import json
                result = json.loads(json_match.group(1))
            else:
                # Intentar parsear toda la respuesta como JSON
                import json
                result = json.loads(response)
                
            action = result.get('action', 'unknown')
            details = result.get('details', {})
            
            # Procesar según la acción determinada
            if action == 'create_file':
                file_name = details.get('file_name', 'unnamed.txt')
                file_type = details.get('file_type', 'txt')
                content_description = details.get('content_description', text)
                
                # Asegurar que el nombre de archivo tenga la extensión correcta
                if not file_name.endswith('.' + file_type):
                    file_name += '.' + file_type
                
                # Usar la función de creación de archivo para generar el contenido
                result = create_file_with_agent(
                    description=content_description,
                    file_type=file_type,
                    filename=file_name,
                    agent_id='developer',  # Usar agente desarrollador por defecto
                    workspace_path=workspace_path,
                    model=model
                )
                
                if result['success']:
                    return {
                        'success': True,
                        'action': 'create_file',
                        'file_path': result['file_path'],
                        'content': result['content']
                    }
                else:
                    return {
                        'success': False,
                        'error': result['error']
                    }
            
            elif action == 'execute_command':
                command = details.get('command', '')
                
                if not command:
                    return {
                        'success': False,
                        'error': 'No se pudo determinar el comando a ejecutar'
                    }
                
                import subprocess
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=workspace_path
                )
                
                stdout, stderr = process.communicate(timeout=30)
                status = process.returncode
                
                return {
                    'success': True,
                    'action': 'execute_command',
                    'command': command,
                    'stdout': stdout.decode('utf-8', errors='replace'),
                    'stderr': stderr.decode('utf-8', errors='replace'),
                    'status': status
                }
            
            elif action == 'answer_question':
                question = details.get('question', text)
                
                # Generar respuesta a la pregunta
                response_result = generate_response(
                    user_message=question,
                    agent_id='general',  # Usar agente general para preguntas
                    model=model
                )
                
                if response_result['success']:
                    return {
                        'success': True,
                        'action': 'answer_question',
                        'question': question,
                        'answer': response_result['response']
                    }
                else:
                    return {
                        'success': False,
                        'error': response_result['error']
                    }
            
            else:  # unknown o cualquier otro caso
                return {
                    'success': False,
                    'error': 'No se pudo determinar una acción específica para esta instrucción'
                }
                
        except Exception as json_error:
            logging.error(f"Error parseando respuesta: {str(json_error)}")
            return {
                'success': False,
                'error': f'Error procesando la instrucción: {str(json_error)}'
            }
                
    except Exception as e:
        logging.error(f"Error procesando instrucción en lenguaje natural: {str(e)}")
        return {
            'success': False,
            'error': f'Error procesando instrucción: {str(e)}'
        }