"""
Módulo de generación de contenido con agentes especializados.
Este módulo proporciona funciones para generar archivos con diferentes agentes IA especializados.
"""
import os
import re
import logging
import openai
from flask import session
from app import get_user_workspace

def get_agent_system_prompt(agent_id):
    """
    Obtiene el prompt de sistema según el agente especializado seleccionado.
    
    Args:
        agent_id: ID del agente (developer, architect, advanced, general)
        
    Returns:
        str: Prompt de sistema para el agente
    """
    agent_system_prompts = {
        'developer': "Eres un Desarrollador experto en la creación de código de alta calidad. Tu especialidad es escribir código eficiente, bien documentado y que sigue las mejores prácticas actuales. Eres meticuloso con la estructura, optimizaciones y detalles de implementación.",
        'architect': "Eres un Arquitecto de Software experto en diseño de sistemas y componentes. Tu especialidad es crear estructuras escalables, mantenibles y bien organizadas. Te enfocas en patrones de diseño, modularidad y principios SOLID.",
        'advanced': "Eres un Desarrollador Avanzado especializado en implementaciones sofisticadas. Tu especialidad es crear soluciones complejas con características avanzadas, optimizaciones de rendimiento y técnicas modernas. Dominas los detalles más profundos de las tecnologías.",
        'general': "Eres un asistente experto en desarrollo de software especializado en crear archivos de alta calidad."
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
        'developer': "desarrollador experto",
        'architect': "arquitecto de software",
        'advanced': "desarrollador avanzado especializado",
        'general': "experto desarrollador"
    }
    
    return agent_names.get(agent_id, "experto desarrollador")

def create_file_with_agent(description, file_type, filename, agent_id, workspace_path):
    """
    Crea un archivo utilizando un agente especializado.
    
    Args:
        description: Descripción del archivo a generar
        file_type: Tipo de archivo (html, css, js, py, json, md, txt)
        filename: Nombre del archivo
        agent_id: ID del agente especializado
        workspace_path: Ruta del workspace del usuario
        
    Returns:
        dict: Resultado de la operación con claves success, file_path y content
    """
    try:
        # Debug logs
        logging.debug(f"Generando archivo con agente: {agent_id}")
        logging.debug(f"Tipo de archivo: {file_type}")
        logging.debug(f"Nombre de archivo: {filename}")
        logging.debug(f"Descripción: {description}")
        
        openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
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
        
        completion = openai_client.chat.completions.create(
            model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000  # Aumentado para permitir archivos más complejos
        )
        
        file_content = completion.choices[0].message.content.strip()
        
        # Verificar que se haya generado contenido
        if not file_content:
            return {
                'success': False,
                'message': 'El modelo no generó contenido para el archivo'
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
        
        with open(file_path, 'w') as f:
            f.write(file_content)
            
        # Obtener la ruta relativa para mostrar al usuario
        relative_path = os.path.relpath(file_path, workspace_path)
        
        return {
            'success': True,
            'file_path': relative_path,
            'content': file_content[:500] + '...' if len(file_content) > 500 else file_content
        }
            
    except Exception as e:
        logging.error(f"Error generando contenido del archivo: {str(e)}")
        return {
            'success': False,
            'message': f'Error generando contenido del archivo: {str(e)}'
        }

def generate_complex_file_with_agent(description, file_type="html", filename="", agent_id="general"):
    """
    Función principal que maneja la generación de archivos complejos usando agentes especializados.
    
    Args:
        description: Descripción del archivo a generar
        file_type: Tipo de archivo (html, css, js, py, json, md, txt)
        filename: Nombre del archivo a crear (opcional)
        agent_id: ID del agente especializado a utilizar (general, developer, architect, advanced)
    """
    try:
        if not description:
            return {
                'success': False,
                'message': 'No se proporcionó una descripción para el archivo'
            }
            
        # Si no se proporciona un nombre de archivo, creamos uno basado en la descripción
        if not filename:
            # Generar un nombre de archivo basado en las primeras palabras de la descripción
            words = re.sub(r'[^\w\s]', '', description.lower()).split()
            filename = '_'.join(words[:3])[:30]  # Usar las primeras 3 palabras, máximo 30 caracteres
            
            # Añadir extensión según el tipo de archivo
            if file_type == 'html':
                filename += '.html'
            elif file_type == 'css':
                filename += '.css'
            elif file_type == 'js':
                filename += '.js'
            elif file_type == 'py':
                filename += '.py'
            else:
                filename += '.txt'
                
        # Asegurar que el archivo tenga una extensión
        if '.' not in filename:
            filename += f'.{file_type}'
            
        # Get the user workspace
        user_id = session.get('user_id', 'default')
        workspace_path = get_user_workspace(user_id)
        
        # Generar el contenido del archivo usando el agente seleccionado
        return create_file_with_agent(description, file_type, filename, agent_id, workspace_path)
            
    except Exception as e:
        logging.error(f"Error en generate_complex_file: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }