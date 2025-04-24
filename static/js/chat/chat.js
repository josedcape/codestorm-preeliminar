// CODESTORM - Sistema de chat con agentes especializados y funcionalidades avanzadas

// Función para copiar el contenido de un mensaje al portapapeles
function copyMessageToClipboard(messageElement) {
  if (!messageElement) return;

  // Obtener el contenido del mensaje
  const messageContent = messageElement.querySelector('.message-content');
  if (!messageContent) return;

  // Extraer el texto plano del contenido HTML para copiar
  const textToCopy = messageContent.textContent.trim();

  // Usar la API del portapapeles moderna si está disponible
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(textToCopy)
      .then(() => {
        showCopyFeedback(messageElement);
      })
      .catch(err => {
        console.error('Error al copiar texto: ', err);
        // Fallback al método alternativo
        fallbackCopyToClipboard(textToCopy, messageElement);
      });
  } else {
    // Método alternativo para contextos no seguros o navegadores antiguos
    fallbackCopyToClipboard(textToCopy, messageElement);
  }
}

// Método alternativo para copiar al portapapeles
function fallbackCopyToClipboard(text, messageElement) {
  // Crear un elemento textarea temporal
  const textArea = document.createElement("textarea");
  textArea.value = text;

  // Hacer que el textarea no sea visible
  textArea.style.position = "fixed";
  textArea.style.top = "0";
  textArea.style.left = "0";
  textArea.style.width = "2em";
  textArea.style.height = "2em";
  textArea.style.padding = "0";
  textArea.style.border = "none";
  textArea.style.outline = "none";
  textArea.style.boxShadow = "none";
  textArea.style.background = "transparent";

  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  let successful = false;
  try {
    successful = document.execCommand('copy');
  } catch (err) {
    console.error('Error en fallback de copiar:', err);
  }

  document.body.removeChild(textArea);

  if (successful) {
    showCopyFeedback(messageElement);
  }
}

// Mostrar feedback visual al copiar
function showCopyFeedback(messageElement) {
  // Encontrar el botón de copiar
  const copyButton = messageElement.querySelector('.copy-message');
  if (!copyButton) return;

  // Cambiar el ícono temporalmente
  const originalHTML = copyButton.innerHTML;
  copyButton.innerHTML = '<i class="bi bi-check"></i>';
  copyButton.title = '¡Copiado!';
  copyButton.classList.add('btn-success');
  copyButton.classList.remove('btn-outline-light');

  // Mostrar un tooltip o mensaje emergente
  const tooltip = document.createElement('div');
  tooltip.className = 'copy-tooltip';
  tooltip.textContent = '¡Copiado al portapapeles!';
  messageElement.appendChild(tooltip);

  // Eliminar el tooltip después de un tiempo
  setTimeout(() => {
    if (tooltip && tooltip.parentNode) {
      tooltip.parentNode.removeChild(tooltip);
    }
  }, 2000);

  // Restaurar el botón después de un tiempo
  setTimeout(() => {
    copyButton.innerHTML = originalHTML;
    copyButton.title = 'Copiar mensaje';
    copyButton.classList.remove('btn-success');
    copyButton.classList.add('btn-outline-light');
  }, 1500);
}

// Mejorar el HTML para previsualización añadiendo meta tags y estilos necesarios
function enhanceHtmlForPreview(htmlContent) {
  // Si el HTML no tiene estructura completa, agregar las etiquetas básicas
  if (!htmlContent.includes('<!DOCTYPE html>')) {
    htmlContent = `<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Previsualización CODESTORM</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        margin: 0;
        padding: 20px;
      }
    </style>
</head>
<body>
${htmlContent}
</body>
</html>`;
  }

  // Asegurar que tenga viewport para dispositivos móviles
  if (!htmlContent.includes('<meta name="viewport"') && htmlContent.includes('<head>')) {
    htmlContent = htmlContent.replace(
      '<head>',
      '<head>\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">'
    );
  }

  return htmlContent;
}

// Función para abrir previsualización en una nueva ventana o pestaña
function openPreviewInNewWindow(htmlContent) {
  const enhancedHtml = enhanceHtmlForPreview(htmlContent);
  const newWindow = window.open('', '_blank');
  if (newWindow) {
    newWindow.document.write(enhancedHtml);
    newWindow.document.close();
  } else {
    alert('El navegador bloqueó la apertura de una nueva ventana. Por favor, permita ventanas emergentes para este sitio.');
  }
}


// Función principal para inicializar el chat
function initializeChat() {
  const chatContainer = document.getElementById('chat-container');
  const chatMessages = document.getElementById('chat-messages');
  const chatInput = document.getElementById('chat-input');
  const sendButton = document.getElementById('send-button');
  const agentSelector = document.getElementById('agent-selector');

  console.log("Inicializando chat con nueva configuración");

  // Cargar los agentes en el selector
  loadAgentSelector();

  // Verificar si hay un mensaje en la URL (enviado desde el corrector de código)
  checkMessageFromUrl(chatInput);

  // Crear un formulario virtual o usar el existente
  let chatForm = document.getElementById('chat-form');
  if (!chatForm) {
    console.log("Creando formulario virtual para el chat");
    chatForm = document.createElement('form');
    chatForm.id = 'chat-form';
    // No es necesario agregar el formulario al DOM
  }

  // Evento para enviar mensaje al hacer clic en el botón
  sendButton.addEventListener('click', function(e) {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (message) {
      console.log("Enviando mensaje desde botón:", message);
      sendMessage(message);
      chatInput.value = '';
      // Restablecer altura después de enviar
      chatInput.style.height = 'auto';
    }
  });

  // También manejar el evento submit del formulario (si existe en el DOM)
  chatForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (message) {
      console.log("Enviando mensaje desde formulario:", message);
      sendMessage(message);
      chatInput.value = '';
      // Restablecer altura después de enviar
      chatInput.style.height = 'auto';
    }
  });

  // Permitir enviar con Enter (excepto con Shift+Enter para nueva línea)
  chatInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendButton.click();
    }
  });

  // Autoajustar altura del textarea al escribir
  chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
  });

  // Si se recibió un mensaje de la URL, ajustar la altura inicial
  if (chatInput.value) {
    chatInput.style.height = 'auto';
    chatInput.style.height = (chatInput.scrollHeight) + 'px';
  }

  // Evento para cambiar de agente
  agentSelector.addEventListener('change', function() {
    const selectedAgentId = agentSelector.value;
    setActiveAgent(selectedAgentId);
  });

  // Inicializar selectores para dispositivos móviles
  initMobileSelectors();

  // Inicializar detección de comandos de creación de páginas
  initCreationCommandDetection();

  // Initialize document features
  initializeDocumentFeatures();

  // Set up message timeout handler
  setupMessageTimeoutHandler();
}

// Inicializar selectores para dispositivos móviles
function initMobileSelectors() {
  const mobileModelSelect = document.getElementById('mobile-model-select');
  const mobileAgentSelector = document.getElementById('mobile-agent-selector');
  const desktopModelSelect = document.getElementById('model-select');

  if (mobileModelSelect && desktopModelSelect) {
    // Sincronizar selección inicial
    mobileModelSelect.value = desktopModelSelect.value;

    // Sincronizar cambios de modelo
    mobileModelSelect.addEventListener('change', function() {
      desktopModelSelect.value = this.value;
      console.log("Modelo cambiado a: " + this.value);
    });

    desktopModelSelect.addEventListener('change', function() {
      if (mobileModelSelect) {
        mobileModelSelect.value = this.value;
      }
    });
  }

  if (mobileAgentSelector) {
    mobileAgentSelector.addEventListener('change', function() {
      const selectedAgentId = this.value;
      setActiveAgent(selectedAgentId);
      console.log("Agente móvil cambiado a: " + selectedAgentId);
    });
  }
}

// Cargar los agentes en el selector
function loadAgentSelector() {
  const agentSelector = document.getElementById('agent-selector');
  if (!agentSelector) return; // Prevenir errores si el elemento no existe

  // Limpiar el selector actual
  agentSelector.innerHTML = '';

  // Verificar que SPECIALIZED_AGENTS está disponible
  if (typeof window.SPECIALIZED_AGENTS === 'undefined') {
    console.error("Error: SPECIALIZED_AGENTS no está definido");
    // Usar agentes predefinidos básicos si no están disponibles
    window.SPECIALIZED_AGENTS = {
      developer: {
        id: 'developer',
        name: 'Agente de Desarrollo',
        icon: 'bi-code-slash',
        description: 'Experto en optimización y edición de código en tiempo real',
        capabilities: ['Corrección de código', 'Optimización', 'Desarrollo']
      },
      architect: {
        id: 'architect',
        name: 'Agente de Arquitectura',
        icon: 'bi-diagram-3',
        description: 'Diseñador de arquitecturas escalables',
        capabilities: ['Diseño de sistemas', 'Planificación', 'Estructura']
      }
    };
  }

  // Crear opciones HTML directamente para mejor rendimiento
  let optionsHTML = '';

  // Opción por defecto (Developer)
  optionsHTML += `<option value="developer" selected>Agente de Desarrollo</option>`;

  // Añadir el resto de agentes
  for (const agentId in window.SPECIALIZED_AGENTS) {
    if (agentId !== 'developer') {
      const agent = window.SPECIALIZED_AGENTS[agentId];
      optionsHTML += `<option value="${agentId}">${agent.name}</option>`;
    }
  }

  // Insertar todas las opciones de una vez (mejor rendimiento)
  agentSelector.innerHTML = optionsHTML;
}

// Establecer el agente activo
function setActiveAgent(agentId) {
  // Asegurarse de que SPECIALIZED_AGENTS está definido
  if (typeof window.SPECIALIZED_AGENTS === 'undefined') {
    console.error("Error: SPECIALIZED_AGENTS no está definido");
    return;
  }

  // Obtener el agente seleccionado o usar el agente desarrollador por defecto
  window.app = window.app || {};
  window.app.activeAgent = window.SPECIALIZED_AGENTS[agentId] || window.SPECIALIZED_AGENTS.developer;

  // Actualizar el valor de los selectores (desktop y móvil)
  const agentSelector = document.getElementById('agent-selector');
  const mobileAgentSelector = document.getElementById('mobile-agent-selector');

  if (agentSelector) {
    agentSelector.value = agentId;
  }

  if (mobileAgentSelector) {
    mobileAgentSelector.value = agentId;
  }

  // Actualizar la descripción del agente
  updateAgentDescription(window.app.activeAgent);

  // Actualizar el icono del avatar
  updateAgentAvatar(window.app.activeAgent);

  // Añadir mensaje informativo al chat
  addSystemMessage(`Has cambiado al <strong>${window.app.activeAgent.name}</strong>. Este agente se especializa en: ${window.app.activeAgent.description}.`);
}

// Actualizar el avatar del agente
function updateAgentAvatar(agent) {
  const agentAvatar = document.querySelector('.agent-avatar i');
  if (agentAvatar) {
    agentAvatar.className = `bi ${agent.icon}`;
  }
}

// Actualizar la descripción del agente
function updateAgentDescription(agent) {
  const agentDescription = document.getElementById('agent-description');
  const agentCapabilities = document.getElementById('agent-capabilities');
  const agentTitle = document.querySelector('.agent-details h5');

  if (agentDescription && agentCapabilities) {
    agentDescription.textContent = agent.description;
    if (agentTitle) {
      agentTitle.textContent = agent.name;
    }

    // Mostrar capacidades
    agentCapabilities.innerHTML = '';
    agent.capabilities.forEach(capability => {
      const li = document.createElement('li');
      li.textContent = capability;
      agentCapabilities.appendChild(li);
    });
  }
}

// Inicializar detección de comandos de creación
function initCreationCommandDetection() {
  // Patrones para detectar comandos de creación (mejorados)
  window.app.creationPatterns = {
    page: /crea(r)?\s+(una)?\s+p[áa]gina|genera(r)?\s+(una)?\s+p[áa]gina|p[áa]gina\s+de\s+ventas/i,
    component: /crea(r)?\s+(un)?\s+componente|genera(r)?\s+(un)?\s+componente/i,
    form: /crea(r)?\s+(un)?\s+formulario|genera(r)?\s+(un)?\s+formulario/i
  };

  // Almacenar información de conversación contextual
  window.app.conversationState = {
    hasColorPreference: false,
    colorPreference: '',
    hasStyleInfo: false,
    styleInfo: '',
    hasContentInfo: false,
    contentInfo: '',
    creationMode: false,
    creationStep: 0,
    lastInstructionType: '',
    pendingActions: [],
    creationInProgress: false,
    messageHistory: []
  };
}

// Enviar mensaje al backend - Versión mejorada con sistema multi-agente y Socket.IO
function sendMessage(message) {
  // Validar que haya un mensaje
  if (!message || message.trim() === '') {
    return;
  }

  // Añadir clase al botón de envío para mostrar animación
  const sendButton = document.getElementById('send-button');
  if (sendButton) {
    sendButton.classList.add('btn-ripple');
    sendButton.disabled = true;

    // Mostrar spinner en el botón
    if (typeof AnimationUtils !== 'undefined') {
      AnimationUtils.showSpinner(sendButton, 'sm');
    } else {
      // Fallback si AnimationUtils no está disponible
      const originalText = sendButton.innerHTML;
      sendButton.innerHTML = '<div class="spinner spinner-sm"></div> Enviando...';

      // Restaurar después de 1.5 segundos
      setTimeout(() => {
        sendButton.innerHTML = originalText;
        sendButton.disabled = false;
        sendButton.classList.remove('btn-ripple');
      }, 1500);
    }
  }

  // Intentar usar Socket.IO si está disponible
  if (socket && socket.connected) {
    console.log("Enviando mensaje a través de Socket.IO");

    // Añadir mensaje del usuario al chat
    addUserMessage(message);

    // Mostrar indicador de carga
    addLoadingMessage();

    // Obtener información del agente y modelo seleccionados
    const agentSelector = document.getElementById('agent-selector');
    const modelSelect = document.getElementById('model-select');
    const documentSelector = document.getElementById('document-selector');

    // Preparar datos para enviar
    const data = {
      message: message,
      agent: agentSelector ? agentSelector.value : 'developer',
      model: modelSelect ? modelSelect.value : 'openai',
      document: documentSelector ? documentSelector.value : ''
    };

    console.log("Enviando mensaje:", data);

    // Enviar mensaje a través de Socket.IO
    socket.emit('user_message', data, (error) => {
      if (error) {
        console.error("Error sending message via Socket.IO:", error);
        removeLoadingMessage();
        addSystemMessage(`Error al enviar el mensaje: ${error}`);
        // Restablecer el botón de envío en caso de error
        if (sendButton) {
          sendButton.disabled = false;
          sendButton.classList.remove('btn-ripple');
          if (typeof AnimationUtils !== 'undefined') {
            AnimationUtils.hideSpinner(sendButton);
          } else {
            // Fallback si AnimationUtils no está disponible
            if (sendButton.querySelector('.spinner')) {
              sendButton.innerHTML = '<i class="bi bi-send"></i>';
            }
          }
        }
      }
    });

    // Limpiar el campo de entrada
    document.getElementById('chat-input').value = '';

    return; // Terminamos aquí si usamos Socket.IO
  }

  // Si Socket.IO no está disponible, usar el método antiguo (fallback)
  console.warn("Socket.IO no está conectado, usando el método de fallback");
  // Añadir mensaje del usuario al chat con animación
  const userMessageElement = addUserMessage(message);
  if (userMessageElement) {
    userMessageElement.classList.add('slide-in-up');
  }

  // Verificar si es un comando para modificar archivos o ejecutar comandos en lenguaje natural
  if (window.naturalCommandProcessor) {
    const parsedRequest = window.naturalCommandProcessor.processRequest(message);
    if (parsedRequest.success) {
      // Es un comando para manipular archivos o ejecutar comandos
      // Mostrar indicador de carga con animación
      addLoadingMessage();

      // Procesar la solicitud mediante el API de lenguaje natural en el backend
      fetch('/api/natural_language', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: message
        }),
      })
        .then(response => response.json())
        .then(data => {
          // Remover indicador de carga
          removeLoadingMessage();

          // Obtener el agente activo
          const activeAgent = window.app.activeAgent || window.SPECIALIZED_AGENTS.developer;

          if (data.success) {
            // La acción fue exitosa, mostrar el resultado
            let resultMessage = data.message || 'Acción completada correctamente';

            // Si hay contenido de archivo o salida de comando, agregarla
            if (data.content) {
              resultMessage += '\n\n```' + (data.file_type || '') + '\n' + data.content + '\n```';
            }

            if (data.stdout) {
              resultMessage += '\n\n```bash\n# Salida del comando:\n' + data.stdout + '\n```';
            }

            if (data.stderr && data.stderr.trim()) {
              resultMessage += '\n\n```bash\n# Errores:\n' + data.stderr + '\n```';
            }

            // Agregar respuesta del agente
            addAgentMessage(resultMessage, activeAgent);
          } else {
            // Hubo un error en la acción
            addAgentMessage('No pude completar esa acción: ' + data.message, activeAgent);
          }
        })
        .catch(error => {
          console.error('Error al procesar lenguaje natural:', error);
          removeLoadingMessage();
          addSystemMessage('Error de conexión. Por favor, inténtalo de nuevo.');
        });

      return; // Terminamos aquí porque ya procesamos el comando
    }
  }

  // Obtener el agente activo
  const activeAgent = window.app.activeAgent || window.SPECIALIZED_AGENTS.developer;
  const agentId = activeAgent.id || 'developer';

  // Mostrar indicador de carga con estilo futurista
  addLoadingMessage();

  // Determinar si estamos en modo colaborativo
  const collaborativeMode = true; // Activar por defecto

  // Enviar al backend con el modelo seleccionado
  const modelSelect = document.getElementById('model-select');
  const selectedModel = modelSelect ? modelSelect.value : 'openai';

  // Obtener el contexto de la conversación reciente (últimos 5 mensajes)
  let conversationContext = [];
  const chatMessages = document.querySelectorAll('.chat-message');
  let contextCount = 0;

  // Reunir los últimos mensajes como contexto, hasta un máximo de 5
  for (let i = chatMessages.length - 2; i >= 0 && contextCount < 5; i--) { // -2 para ignorar el mensaje actual
    const msg = chatMessages[i];
    const role = msg.classList.contains('user-message') ? 'user' :
      msg.classList.contains('system-message') ? 'system' : 'assistant';
    const content = msg.querySelector('.message-content').textContent;

    // Añadir al inicio para mantener el orden cronológico
    conversationContext.unshift({
      role: role,
      content: content
    });

    contextCount++;
  }

  console.log("Enviando mensaje al backend:", {
    message: message,
    agent_id: agentId,
    context: conversationContext,
    model: selectedModel,
    collaborative_mode: collaborativeMode
  });

  // Enviar al backend con información completa y mejor manejo de errores
  console.log("Enviando datos al servidor:", {
    message,
    agent_id: agentId,
    context: conversationContext,
    model: selectedModel,
    collaborative_mode: collaborativeMode
  });

  // Actualizar el estado de la conversación
  const lowerMsg = message.toLowerCase();
  if (lowerMsg.includes('página') || lowerMsg.includes('pagina') || lowerMsg.includes('web')) {
    window.app.conversationState.creationMode = true;
    window.app.conversationState.lastInstructionType = 'page';

    // Detectar preferencias de estilo y color
    if (lowerMsg.includes('color') || lowerMsg.includes('estilo') || lowerMsg.includes('diseño')) {
      window.app.conversationState.hasStyleInfo = true;

      if (lowerMsg.includes('pastel')) {
        window.app.conversationState.hasColorPreference = true;
        window.app.conversationState.colorPreference = 'pastel';
      } else if (lowerMsg.includes('moderna') || lowerMsg.includes('moderno')) {
        window.app.conversationState.hasStyleInfo = true;
        window.app.conversationState.styleInfo = 'moderna';
      }
    }
  }

  console.log("Estado de la conversación:", window.app.conversationState);

  // Guardar historial de mensajes
  window.app.conversationState.messageHistory.push({
    role: 'user',
    content: message,
    timestamp: new Date().toISOString()
  });

  // Log completo con toda la información para diagnóstico
  // Verificar si hay un documento seleccionado para usar como contexto
  const documentSelector = document.getElementById('document-selector');
  const selectedDocument = documentSelector ? documentSelector.value : '';

  // Datos de la solicitud
  const requestData = {
    message,
    agent_id: agentId,
    context: conversationContext,
    model: selectedModel,
    collaborative_mode: collaborativeMode,
    conversation_state: window.app.conversationState
  };

  // Si hay un documento seleccionado, usar la API con contexto de documento
  const apiEndpoint = selectedDocument ? '/api/chat/with-context' : '/api/chat';

  // Comprobar si el documento ya ha sido procesado previamente (buscando en el historial de chat)
  let documentAlreadyProcessed = false;
  let documentContent = '';

  // Buscar en el historial de mensajes si el documento ya fue procesado
  if (selectedDocument && window.app.conversationState.messageHistory.length > 0) {
    for (const msg of window.app.conversationState.messageHistory) {
      if (msg.role === 'assistant' &&
        msg.content &&
        msg.content.includes(`He extraído el contenido del documento '${selectedDocument}'`)) {
        documentAlreadyProcessed = true;
        documentContent = msg.content;
        console.log(`Documento ${selectedDocument} ya procesado anteriormente, usando contexto existente`);
        break;
      }
    }
  }

  // Preparar datos para la API según si es un nuevo documento o uno ya procesado
  const apiData = selectedDocument
    ? {
      message: message,
      document_filename: selectedDocument,
      agent_id: agentId,
      document_already_processed: documentAlreadyProcessed,
      context: conversationContext  // Incluir contexto de conversación para documentos procesados
    }
    : requestData;

  // Mensaje de estado
  if (selectedDocument) {
    if (documentAlreadyProcessed) {
      console.log("Enviando fetch a /api/chat/with-context con documento ya procesado:", selectedDocument);
      addSystemMessage(`⌛ Conectando con el servidor (usando documento "${selectedDocument}" ya procesado como contexto)...`);
    } else {
      console.log("Enviando fetch a /api/chat/with-context con documento nuevo:", selectedDocument);
      addSystemMessage(`⌛ Conectando con el servidor (usando documento "${selectedDocument}" como contexto)...`);
    }
  } else {
    console.log("Enviando fetch a /api/chat con datos:", requestData);
    addSystemMessage("⌛ Conectando con el servidor...");
  }

  // Realizar la solicitud
  fetch(apiEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(apiData),
  })
    .then(response => {
      console.log("Respuesta recibida:", response.status, response.statusText);
      addSystemMessage("✅ Conexión establecida, procesando respuesta...");
      return response.json();
    })
    .then(data => {
      // Remover indicador de carga
      removeLoadingMessage();

      // Restablecer el botón de envío (arreglar problema del spinner que se queda cargando)
      const sendButton = document.getElementById('send-button');
      if (sendButton) {
        sendButton.disabled = false;
        sendButton.classList.remove('btn-ripple');
        if (typeof AnimationUtils !== 'undefined') {
          AnimationUtils.hideSpinner(sendButton);
        } else {
          // Fallback si AnimationUtils no está disponible
          if (sendButton.querySelector('.spinner')) {
            sendButton.innerHTML = '<i class="bi bi-send"></i>';
          }
        }
      }

      // Log de la respuesta para diagnóstico
      console.log("Datos recibidos de /api/chat:", data);

      if (data.error) {
        addSystemMessage(`Error: ${data.error}`);
        return;
      }

      // Verificar si es respuesta directa de un documento (nueva funcionalidad)
      if (data.use_direct_content && data.document_content) {
        console.log("Documento detectado como no extenso. Mostrando contenido directamente:", {
          filename: data.document.filename,
          word_count: data.document.word_count
        });

        // Agregar mensaje del sistema indicando que se está mostrando el contenido directamente
        addSystemMessage(`ℹ️ Documento no extenso (${data.document.word_count} palabras) - Mostrando contenido directamente.`);

        // Agregar animación de carga para el procesamiento del documento
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
          const processingElement = document.createElement('div');
          processingElement.className = 'chat-message system-message fade-in';
          processingElement.innerHTML = `
          <div class="message-content">
            <div class="d-flex align-items-center">
              <div class="spinner spinner-sm me-2"></div>
              <span>Procesando contenido del documento...</span>
            </div>
          </div>
        `;
          chatMessages.appendChild(processingElement);
          scrollToBottom(chatMessages);

          // Remover después de un breve retraso y habilitar el chat de nuevo
          setTimeout(() => {
            // Eliminar el mensaje de procesamiento
            processingElement.remove();

            // Guardar respuesta en el historial
            window.app.conversationState.messageHistory.push({
              role: 'assistant',
              content: data.response,
              timestamp: new Date().toISOString()
            });

            // Mostrar la respuesta del agente con el contenido del documento
            addAgentMessage(data.response, activeAgent);

            // Mensaje adicional para invitar a hacer preguntas sobre el documento
            addSystemMessage("✅ El documento ha sido procesado. Ahora puedes hacer preguntas específicas sobre su contenido.");

            // Scroll hasta el final
            scrollToBottom(chatMessages);

            // Poner el foco en el campo de entrada
            const chatInput = document.getElementById('message-input');
            if (chatInput) {
              chatInput.focus();
            }
          }, 1500);
        }
      } else {
        // Comportamiento normal para respuestas regulares

        // Actualizar estado de la conversación si se creó un archivo o se realizó alguna acción especial
        if (data.response && data.response.includes('He creado el archivo que solicitaste')) {
          window.app.conversationState.creationMode = false;
          window.app.conversationState.creationInProgress = false;
          window.app.conversationState.creationStep = 0;
          window.app.conversationState.hasColorPreference = false;
          window.app.conversationState.hasStyleInfo = false;
          window.app.conversationState.hasContentInfo = false;
          console.log("¡Archivo creado! Restableciendo estado de conversación", window.app.conversationState);
        }

        // Guardar respuesta en el historial
        window.app.conversationState.messageHistory.push({
          role: 'assistant',
          content: data.response,
          timestamp: new Date().toISOString()
        });

        // Mostrar la respuesta del agente
        addAgentMessage(data.response, activeAgent);
      }

      // Procesar recomendaciones de agentes si las hay
      if (data.response.includes('**Nota:** Para esta consulta, también podrías consultar a:')) {
        const recommendationSection = data.response.split('**Nota:** Para esta consulta, también podrías consultar a:')[1];
        // Extraer recomendaciones de agentes
        const agentRecommendations = recommendationSection.match(/- El (.*?), para obtener/g);

        if (agentRecommendations && agentRecommendations.length > 0) {
          // Añadir opciones para cambiar de agente
          const agentOptions = agentRecommendations.map(rec => {
            const agentName = rec.match(/- El (.*?),/)[1];
            let agentId = '';

            // Mapear nombres a IDs
            if (agentName.includes('Desarrollo')) agentId = 'developer';
            else if (agentName.includes('Arquitectura')) agentId = 'architect';
            else if (agentName.includes('Avanzado')) agentId = 'advanced';

            return { id: agentId, name: agentName };
          });

          // Mostrar opciones de cambio como botones
          let agentButtonsHTML = '<div class="agent-recommendations mt-2">';
          agentButtonsHTML += '<p class="text-muted small">¿Quieres cambiar de agente para esta consulta?</p>';

          agentOptions.forEach(agent => {
            agentButtonsHTML += `<button class="btn btn-sm btn-outline-primary me-2 mt-1 switch-agent-btn" data-agent-id="${agent.id}">
            Cambiar a ${agent.name}
          </button>`;
          });

          agentButtonsHTML += '</div>';

          // Añadir botones al último mensaje del agente
          const lastAgentMessage = document.querySelector('.chat-message.agent-message:last-child .message-content');
          if (lastAgentMessage) {
            lastAgentMessage.insertAdjacentHTML('beforeend', agentButtonsHTML);

            // Añadir event listeners a los botones
            document.querySelectorAll('.switch-agent-btn').forEach(btn => {
              btn.addEventListener('click', function() {
                const newAgentId = this.getAttribute('data-agent-id');
                if (newAgentId) {
                  setActiveAgent(newAgentId);
                  addSystemMessage(`Has cambiado al ${window.SPECIALIZED_AGENTS[newAgentId].name}. Puedes repetir tu consulta para obtener su perspectiva.`);
                }
              });
            });
          }
        }
      }

      // Detectar y procesar código HTML dentro de la respuesta
      processHtmlCodeForPreview(data.response);
    })
    .catch(error => {
      console.error('Error en la comunicación con el servidor:', error);
      removeLoadingMessage();

      // Restablecer el botón de envío en caso de error
      const sendButton = document.getElementById('send-button');
      if (sendButton) {
        sendButton.disabled = false;
        sendButton.classList.remove('btn-ripple');
        if (typeof AnimationUtils !== 'undefined') {
          AnimationUtils.hideSpinner(sendButton);
        } else {
          // Fallback si AnimationUtils no está disponible
          if (sendButton.querySelector('.spinner')) {
            sendButton.innerHTML = '<i class="bi bi-send"></i>';
          }
        }
      }

      // Mensaje de error más detallado para facilitar la depuración
      const errorMessage = `Error de conexión: ${error.message || '([^\s]+)\n([\s\S]*?)```/g, function(match, language, code) {
        return `
            <div class="code-header">
                <span class="code-language">${language || 'code'}</span>
                <div class="code-buttons">
                    <button class="code-button copy-code-btn" title="Copiar código">
                        <i class="bi bi-clipboard"></i> Copiar
                    </button>
                </div>
            </div>
            <pre><code class="${language || ''}">${code}</code></pre>
        `;
    });

    // Replace inline code
    text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // Replace line breaks
    text = text.replace(/\n/g, '<br>');

    return text;
}

// Process code blocks in message
function processCodeBlocks(messageElement) {
    // Initialize highlighting on all code blocks
    const codeBlocks = messageElement.querySelectorAll('pre code');
    codeBlocks.forEach(block => {
        hljs.highlightElement(block);
    });

    // Add copy functionality to code blocks
    const copyButtons = messageElement.querySelectorAll('.copy-code-btn');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const codeBlock = this.closest('.message-content').querySelector('pre code');
            copyToClipboard(codeBlock.textContent);

            // Change button text temporarily
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="bi bi-check"></i> Copiado';

            setTimeout(() => {
                this.innerHTML = originalText;
            }, 2000);
        });
    });
}

// Copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(
        () => console.log('Texto copiado al portapapeles'),
        err => console.error('Error al copiar texto: ', err)
    );
}

// Show loading indicator
function showLoadingIndicator() {
    const messagesContainer = document.getElementById('chat-messages');

    // Remove existing loading indicator if any
    const existingIndicator = document.getElementById('loading-indicator');
    if (existingIndicator) {
        existingIndicator.remove();
    }

    // Create loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loading-indicator';
    loadingDiv.className = 'loading-animation';
    loadingDiv.innerHTML = `
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
    `;

    messagesContainer.appendChild(loadingDiv);
    scrollToBottom(messagesContainer);
}

// Hide loading indicator
function hideLoadingIndicator() {
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.remove();
    }
}

// Handle socket connection errors
function handleSocketError() {
    console.warn('Problemas con la conexión Socket.IO');
    addSystemMessage("⚠️ Problemas de conexión. Utilizando método alternativo.");
}

// Process HTML code for preview
function processHtmlCodeForPreview(message) {
    // Extract HTML content from code blocks
    const htmlRegex = /```html([\s\S]*?)```/g;
    const htmlMatches = message.match(htmlRegex);

    if (htmlMatches && htmlMatches.length > 0) {
        // Extract the HTML from the first match
        const htmlCode = htmlMatches[0].replace(/```html/, '').replace(/