# Solamente el código de la función corregida para el problema de indentación
def generate_complex_file_internal(description, file_type="html", filename="", agent_id="general"):
    """
    Versión interna de generate_complex_file para uso dentro de handle_chat.
    Genera archivos complejos basados en descripciones generales.
    
    Args:
        description: Descripción del archivo a generar
        file_type: Tipo de archivo (html, css, js, py, json, md, txt)
        filename: Nombre del archivo a crear (opcional)
        agent_id: ID del agente especializado a utilizar (general, developer, architect, advanced)
    """
    # Importar el módulo de agentes generadores
    import agents_generators
    
    # Utilizar la nueva implementación con soporte para agentes
    return agents_generators.generate_complex_file_with_agent(description, file_type, filename, agent_id)