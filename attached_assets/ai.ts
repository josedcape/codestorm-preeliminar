import { Request, Response } from "express";
import axios from "axios";
import dotenv from 'dotenv';

dotenv.config();

// Función para generar una respuesta de OpenAI
async function generateOpenAIResponse(
  prompt: string,
  code?: string,
  agentType?: string,
  apiKey?: string,
) {
  const openaiKey = apiKey || process.env.OPENAI_API_KEY;
  if (!openaiKey) {
    throw new Error(
      "❌ API key de OpenAI no configurada. Por favor, configura tu clave API en la configuración.",
    );
  }

  // Seleccionar el sistema de instrucciones según el tipo de agente
  let systemPrompt =
    "Eres un asistente de programación experto. Responde en español.";

  if (agentType === "dev") {
    systemPrompt = `Eres un Agente de Desarrollo experto, altamente capacitado en la edición y optimización de código en tiempo real.
Tus capacidades incluyen:
- Corrección y refactorización de código utilizando linters y herramientas como Pylint, ESLint y Prettier
- Optimización de rendimiento con técnicas como caching, optimización de consultas SQL, lazy loading y code splitting
- Integración de frameworks modernos como FastAPI, Flask, Express.js, React con Hooks y React Router
- Automatización de tareas con herramientas CI/CD como GitHub Actions y CircleCI
- Generación de código limpio, legible, modular y mantenible

Responde siempre en español y ofrece soluciones prácticas con ejemplos de código específicos.`;
  } else if (agentType === "architect") {
    systemPrompt = `Eres un Agente de Arquitectura experto, responsable de diseñar arquitecturas escalables y optimizadas.
Tus capacidades incluyen:
- Definición de estructuras de proyecto organizadas con herramientas como Docker y Kubernetes
- Selección de tecnologías y frameworks adecuados (Django, FastAPI, React, Redux, React Native)
- Asesoría en elección de bases de datos (PostgreSQL, MongoDB, Firebase, AWS DynamoDB)
- Implementación de microservicios y arquitecturas basadas en eventos con RabbitMQ o Kafka
- Planificación de UI/UX y patrones de diseño como Atomic Design, Styled Components y Material UI

Responde siempre en español y ofrece soluciones estructuradas con diagramas y ejemplos cuando sea posible.`;
  } else if (agentType === "advanced") {
    systemPrompt = `Eres un Agente Avanzado de Software especializado en integraciones complejas y creación de funciones avanzadas.
Tus capacidades incluyen:
- Gestión de APIs (RESTful, GraphQL) y microservicios con Docker y Kubernetes
- Optimización de backend con Nginx, Redis y manejo de tareas asíncronas con Celery
- Automatización avanzada con Node.js, Grunt y Gulp
- Implementación de autenticación segura con OAuth 2.0, JWT y Passport.js
- Integración con servicios cloud (AWS, Google Cloud, Azure) 
- Configuración de despliegue y pruebas automatizadas con Docker, Heroku, Jest, PyTest y Mocha

Responde siempre en español y ofrece soluciones técnicas avanzadas con ejemplos de implementación detallados.`;
  }

  const messages = [
    { role: "system", content: systemPrompt },
    { role: "user", content: prompt },
  ];

  // Si hay código, añadirlo como contexto
  if (code) {
    messages.push({
      role: "user",
      content: `Contexto de código:\n\`\`\`\n${code}\n\`\`\``,
    });
  }

  try {
    console.log("Enviando solicitud a OpenAI...");

    // Verificar que la clave API sea válida
    if (!openaiKey || openaiKey === 'your-openai-api-key' || !openaiKey.startsWith('sk-') || openaiKey.length < 40) {
      throw new Error('La clave API de OpenAI no es válida. Debe comenzar con "sk-" y tener al menos 40 caracteres.');
    }

    const response = await axios.post(
      "https://api.openai.com/v1/chat/completions",
      {
        model: "gpt-4",  // Corregido el nombre del modelo
        messages,
        temperature: 0.7,
        max_tokens: 1000,
      },
      {
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${openaiKey}`,
        },
      },
    );

    // Verificar que la respuesta tenga el formato esperado
    if (
      response.data.choices &&
      response.data.choices.length > 0 &&
      response.data.choices[0].message &&
      response.data.choices[0].message.content
    ) {
      console.log("Respuesta de OpenAI recibida correctamente");
      return response.data.choices[0].message.content;
    } else {
      console.error(
        "Respuesta de OpenAI en formato inesperado:",
        response.data,
      );
      throw new Error("Formato de respuesta de OpenAI inesperado");
    }
  } catch (error) {
    console.error("Error al llamar a la API de OpenAI:", error);
    if (axios.isAxiosError(error) && error.response) {
      console.error("Detalles de la respuesta de error:", error.response.data);
      if (error.response.status === 401) {
        throw new Error('Error de autenticación. Verifica tu API key de OpenAI.');
      }
    }
    throw error;
  }
}

// Función para generar una respuesta de Gemini
async function generateGeminiResponse(prompt: string, code?: string) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error("Gemini API key no configurada");
  }

  const fullPrompt = code
    ? `${prompt}\n\nContexto de código:\n\`\`\`\n${code}\n\`\`\``
    : prompt;

  try {
    // Endpoint actualizado para Gemini 2.5 Pro
    const response = await axios.post(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent`,
      {
        contents: [
          {
            parts: [
              {
                text: `Eres un asistente de programación experto. Responde siempre en español.\n\n${fullPrompt}`,
              },
            ],
          },
        ],
        generationConfig: {
          temperature: 0.7,
          maxOutputTokens: 1000,
        },
      },
      {
        headers: {
          "Content-Type": "application/json",
          "x-goog-api-key": apiKey,
        },
        params: {
          key: apiKey,  // También incluido como parámetro de URL para mayor compatibilidad
        },
      },
    );

    // Verificar que la respuesta tenga el formato esperado
    if (
      response.data.candidates &&
      response.data.candidates.length > 0 &&
      response.data.candidates[0].content &&
      response.data.candidates[0].content.parts &&
      response.data.candidates[0].content.parts.length > 0
    ) {
      return response.data.candidates[0].content.parts[0].text;
    } else {
      console.error(
        "Respuesta de Gemini en formato inesperado:",
        response.data,
      );
      return "Lo siento, no pude procesar la respuesta de Gemini. Por favor intenta con otro modelo.";
    }
  } catch (error) {
    console.error("Error al llamar a la API de Gemini:", error);
    if (axios.isAxiosError(error) && error.response) {
      console.error("Detalles de la respuesta de error:", error.response.data);
    }
    throw error;
  }
}

// Función para generar una respuesta de Anthropic/Claude
async function generateClaudeResponse(
  prompt: string,
  code?: string,
  model: string = "claude-3.5-sonnet-v2",
) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error("Anthropic API key no configurada");
  }

  const fullPrompt = code
    ? `${prompt}\n\nContexto de código:\n\`\`\`\n${code}\n\`\`\``
    : prompt;

  try {
    const response = await axios.post(
      "https://api.anthropic.com/v1/messages",
      {
        model: model,
        max_tokens: 1000,
        temperature: 0.7,
        system:
          "Actúa como un desarrollador altamente capacitado que puede ayudar, hacer recomendaciones y sugerencias para desarrollar de la forma más eficiente aplicaciones según las indicaciones del usuario. Tienes la capacidad de crear archivos, carpetas y ejecutar comandos en la terminal. Ofrece siempre soluciones prácticas y eficientes. Responde siempre en español.",
        messages: [
          {
            role: "user",
            content: fullPrompt,
          },
        ],
      },
      {
        headers: {
          "Content-Type": "application/json",
          "anthropic-api-key": apiKey,  // Corregido: de "x-api-key" a "anthropic-api-key"
          "anthropic-version": "2023-06-01",
        },
      },
    );

    // Claude devuelve la respuesta en un formato diferente
    if (response.data.content && response.data.content.length > 0) {
      return response.data.content[0].text;
    } else {
      console.error("Respuesta de Claude sin contenido:", response.data);
      throw new Error("Formato de respuesta de Claude inesperado");
    }
  } catch (error) {
    console.error("Error al llamar a la API de Claude:", error);
    if (axios.isAxiosError(error) && error.response) {
      console.error("Detalles de la respuesta de error:", error.response.data);
    }
    throw error;
  }
}

// Ruta para manejar la generación de respuestas
const availableModels = {
  'gpt-4o': { provider: 'openai', name: 'GPT-4' },
  'gpt-4': { provider: 'openai', name: 'GPT-4' },
  'gpt-3.5-turbo': { provider: 'openai', name: 'GPT-3.5 Turbo' },
  'claude-3-opus': { provider: 'anthropic', name: 'Claude 3 Opus' },
  'claude-3-sonnet': { provider: 'anthropic', name: 'Claude 3 Sonnet' },
  'gemini-pro': { provider: 'google', name: 'Gemini Pro' }
};

const availableModelsKeys = Object.keys(availableModels);

export async function handleAIGenerate(req: Request, res: Response) {
  try {
    const { model, prompt, code, agentType } = req.body;

    // Verificar API keys
    const openaiKey = req.headers['x-openai-key'] || process.env.OPENAI_API_KEY;
    if (!openaiKey) {
      return res.status(400).json({ 
        error: "API key de OpenAI no configurada. Por favor, configura la clave en la sección de API Keys.",
        type: "api_key_missing"
      });
    }

    if (!prompt) {
      return res.status(400).json({ error: "Se requiere un prompt" });
    }

    console.log(
      `Generando respuesta con modelo ${model} y agente ${agentType || "default"}. Prompt: ${prompt.substring(0, 50)}...`,
    );

    // Obtener claves API de los headers o variables de entorno
    const anthropicKey = req.headers['x-anthropic-key'] || process.env.ANTHROPIC_API_KEY;
    const geminiKey = req.headers['x-gemini-key'] || process.env.GEMINI_API_KEY;

    // Mostrar información sobre las claves para depuración
    console.log("API Keys disponibles:");
    console.log("OpenAI:", openaiKey ? "Configurada" : "No configurada");
    console.log("Anthropic:", anthropicKey ? "Configurada" : "No configurada");
    console.log("Gemini:", geminiKey ? "Configurada" : "No configurada");

    let response: string;
    let warning = null;

    try {
      // Definir y comprobar disponibilidad de modelos
      const availableModelsKeys = Object.keys(availableModels);
      console.log("Modelos disponibles:", availableModelsKeys);
      console.log("Modelo solicitado:", model);

      // Verificar el modelo solicitado y usar alternativa si es necesario
      let modelToUse = model;
      if (!model || !availableModels[model]) {
        modelToUse = 'gpt-4'; // Modelo por defecto
        console.log(`Modelo ${model} no válido, usando modelo por defecto: ${modelToUse}`);
        warning = `El modelo solicitado no está disponible. Usando ${modelToUse} como alternativa.`;
      }

      switch (modelToUse) {
        case "gpt-4o":
        case "gpt-4.1":
        case "o3-mini":
        case "gpt-4":
        case "gpt-3.5-turbo":
          if (!openaiKey) {
            return res
              .status(400)
              .json({ error: "API key de OpenAI no configurada. Por favor, configura la clave en la sección de API Keys." });
          }
          response = await generateOpenAIResponse(prompt, code, agentType, openaiKey.toString());
          break;
        case "gemini-pro":
          if (!geminiKey) {
            return res
              .status(400)
              .json({ error: "API key de Gemini no configurada. Por favor, configura la clave en la sección de API Keys." });
          }
          response = await generateGeminiResponse(prompt, code);
          break;
        case "claude-3.7-sonnet":
        case "claude-3.5-sonnet-v2":
        case "claude-3-opus":
        case "claude-3-sonnet":
        case "claude-3":
        case "claude-2.1":
          if (!anthropicKey) {
            return res
              .status(400)
              .json({ error: "API key de Anthropic no configurada. Por favor, configura la clave en la sección de API Keys." });
          }
          // Usar el modelo adecuado para Claude
          response = await generateClaudeResponse(prompt, code, modelToUse);
          break;
        case "qwen-2.5-omni-7b":
          // Para modelos locales, podríamos implementar una solución diferente
          // Por ahora, usamos OpenAI como fallback si está configurado
          if (process.env.OPENAI_API_KEY) {
            response = await generateOpenAIResponse(prompt, code);
          } else {
            return res
              .status(400)
              .json({
                error: "No hay un modelo disponible para usar como fallback",
              });
          }
          break;
        default:
          // Intentar usar OpenAI como fallback
          if (process.env.OPENAI_API_KEY) {
            response = await generateOpenAIResponse(prompt, code);
          } else {
            return res
              .status(400)
              .json({ error: "Modelo no válido y no hay fallback disponible" });
          }
      }

      console.log(`Respuesta generada exitosamente con modelo ${modelToUse}`);
      return res.json({ response, warning });
    } catch (modelError: any) {
      console.error(`Error específico del modelo ${model}:`, modelError);

      // Intentar con el siguiente modelo disponible
      for (const modelo_alternativo of availableModelsKeys) {
        if (modelo_alternativo !== model) {
          try {
            console.log(`Intentando con ${modelo_alternativo} como alternativa...`);
            warning = `El modelo ${model} falló. Usando ${modelo_alternativo} como alternativa.`;

            switch (modelo_alternativo) {
              case "gpt-4o":
              case "gpt-4.1":
              case "o3-mini":
                response = await generateOpenAIResponse(prompt, code, agentType);
                break;
              case "gemini-pro":
                response = await generateGeminiResponse(prompt, code);
                break;
              case "claude-3.7-sonnet":
              case "claude-3.5-sonnet-v2":
              case "claude-3-opus":
              case "claude-3-sonnet":
                response = await generateClaudeResponse(prompt, code, modelo_alternativo);
                break;
            }

            return res.json({ response, warning });
          } catch (fallbackError) {
            console.error(`El fallback a ${modelo_alternativo} también falló:`, fallbackError);
          }
        }
      }

      // Si llegamos aquí, ningún modelo funcionó
      throw new Error(`Todos los modelos disponibles fallaron. Error original: ${modelError.message}`);
    }
  } catch (error: any) {
    console.error("Error al generar respuesta de IA:", error);
    let errorMessage = "⚠️ Error interno del servidor";

    if (error.response && error.response.data) {
      console.error("Detalles de la respuesta de error:", error.response.data);
      errorMessage = `⚠️ **Error**: ${error.message}\n\n**Detalles**: ${JSON.stringify(error.response.data)}`;
    } else if (error.message) {
      errorMessage = `⚠️ **Error**: ${error.message}`;
    }

    res.status(500).json({ error: errorMessage });
  }
}

// Ruta para ejecutar comandos de terminal
export async function handleTerminalExecute(req: Request, res: Response) {
  const { command, workingDirectory } = req.body;

  if (!command) {
    return res.status(400).json({ error: "Se requiere un comando" });
  }

  // Sanitización básica de comandos para prevenir ejecución de comandos maliciosos
  const forbiddenCommands = ['rm -rf /', 'rm -rf *', 'rm -rf .', 'chmod -R 777'];
  if (forbiddenCommands.some(forbidden => command.includes(forbidden))) {
    return res.status(403).json({ 
      error: "Comando no permitido por razones de seguridad",
      output: "⚠️ Este comando podría causar daños al sistema y ha sido bloqueado por seguridad."
    });
  }

  console.log(`Ejecutando comando: ${command}`);

  try {
    // Implementación con spawn para mejor manejo de outputs grandes y en tiempo real
    const { spawn } = require("child_process");
    const options: any = {};

    // Usar directorio de trabajo personalizado si se proporciona
    if (workingDirectory) {
      options.cwd = workingDirectory;
    }

    // Dividir el comando en partes para spawn
    const parts = command.split(' ');
    const cmd = parts[0];
    const args = parts.slice(1);

    const process = spawn(cmd, args, options);

    let output = '';
    let errorOutput = '';

    // Capturar salida en tiempo real
    process.stdout.on('data', (data: Buffer) => {
      const chunk = data.toString();
      output += chunk;
    });

    process.stderr.on('data', (data: Buffer) => {
      const chunk = data.toString();
      errorOutput += chunk;
    });

    // Manejar finalización del proceso
    process.on('close', (code: number) => {
      if (code !== 0) {
        console.log(`Comando terminado con código: ${code}`);
        return res.json({ 
          output: errorOutput || output,
          error: code !== 0,
          exitCode: code
        });
      }

      res.json({ 
        output: output,
        error: false,
        exitCode: code
      });
    });

    // Manejar errores de ejecución
    process.on('error', (err: Error) => {
      console.error(`Error al ejecutar comando: ${err.message}`);
      res.status(500).json({ 
        error: true, 
        output: `Error al ejecutar el comando: ${err.message}`
      });
    });

  } catch (error: any) {
    console.error("Error al ejecutar comando:", error);
    res.status(500).json({ 
      error: true,
      output: error.message || "Error interno del servidor" 
    });
  }
}

// Función para manejar la corrección de código
export async function handleCodeCorrection(req: Request, res: Response) {
  try {
    const { content, instructions, language, fileId, projectId } = req.body;

    if (!content || !instructions) {
      return res
        .status(400)
        .json({
          error: "Se requieren el contenido del código y las instrucciones",
        });
    }

    console.log(
      `Solicitando corrección de código. Lenguaje: ${language}, Instrucciones: ${instructions.substring(0, 50)}...`,
    );

    // Construir un prompt específico para la corrección de código
    const prompt = `
Actúa como un experto en desarrollo de software, especializado en ${language}.
Por favor, revisa y corrige el siguiente código según estas instrucciones: "${instructions}"

Código a corregir:
\`\`\`${language}
${content}
\`\`\`

Proporciona el código corregido junto con una explicación de los cambios realizados.
Devuelve la respuesta en el siguiente formato:
1. El código corregido
2. Una lista de los cambios específicos realizados con números de línea
3. Una explicación general de las mejoras
`;

    // Usar el modelo de GPT-4o para obtener la mejor corrección (actualizado desde GPT-4)
    const response = await generateOpenAIResponse(prompt);

    // Procesar la respuesta para extraer el código corregido y explicaciones
    const correctedCode = extractCorrectedCode(response, language);
    const changes = extractChanges(response);
    const explanation = extractExplanation(response);

    console.log("Corrección de código generada exitosamente");

    res.json({
      correctedCode: correctedCode || content, // Si no se pudo extraer, devolver el código original
      changes,
      explanation,
    });
  } catch (error: any) {
    console.error("Error al corregir código:", error);
    let errorMessage = "Error interno al corregir el código";

    if (error.response && error.response.data) {
      errorMessage = `Error: ${error.message}. Detalles: ${JSON.stringify(error.response.data)}`;
    } else if (error.message) {
      errorMessage = `Error: ${error.message}`;
    }

    res.status(500).json({ error: errorMessage });
  }
}

// Función auxiliar para extraer el código corregido de la respuesta
function extractCorrectedCode(
  response: string,
  language: string,
): string | null {
  // Intentar encontrar el código entre bloques de código markdown
  const codeBlockRegex = new RegExp(
    `\`\`\`(?:${language})?\\n([\\s\\S]*?)\\n\`\`\``,
    "i",
  );
  const match = response.match(codeBlockRegex);

  if (match && match[1]) {
    return match[1].trim();
  }

  // Si no hay bloques de código, intentar extraer de otras formas
  // Por ejemplo, buscar secciones que empiecen con "Código corregido:"
  const sectionRegex =
    /(?:Código corregido:|Código mejorado:|Aquí está el código corregido:)(?:\s*\n+)?([\s\S]+?)(?:\n\s*\n|$)/i;
  const sectionMatch = response.match(sectionRegex);

  if (sectionMatch && sectionMatch[1]) {
    return sectionMatch[1].trim();
  }

  return null;
}

// Función auxiliar para extraer los cambios realizados
function extractChanges(
  response: string,
): { description: string; lineNumbers?: number[] }[] {
  const changes: { description: string; lineNumbers?: number[] }[] = [];

  // Buscar patrones como "Línea 10: Cambié X por Y"
  const changeRegex =
    /(?:línea|líneas)\s+(\d+(?:\s*[-,]\s*\d+)*)\s*:\s*([^\n]+)/gi;
  let match;

  while ((match = changeRegex.exec(response)) !== null) {
    const lineNumbersText = match[1];
    const description = match[2].trim();

    // Procesar números de línea (puede ser "10", "10-15", "10, 11, 12", etc.)
    const lineNumbers = lineNumbersText
      .split(/\s*[-,]\s*/)
      .map((n) => parseInt(n.trim(), 10));

    changes.push({
      description,
      lineNumbers,
    });
  }

  // Si no encontramos cambios con el patrón de línea, buscar listas
  if (changes.length === 0) {
    const listItemRegex = /(?:^|\n)(?:[*-]|\d+\.)\s*([^\n]+)/g;

    while ((match = listItemRegex.exec(response)) !== null) {
      const description = match[1].trim();
      if (
        description &&
        !description.toLowerCase().includes("código corregido") &&
        !description.toLowerCase().includes("explicación")
      ) {
        changes.push({ description });
      }
    }
  }

  return changes;
}

// Función auxiliar para extraer la explicación general
function extractExplanation(response: string): string | undefined {
  // Buscar secciones que parezcan explicaciones
  const explanationRegex =
    /(?:explicación general|explicación|mejoras realizadas|resumen de cambios):\s*\n+(.+(?:\n+(?!\n*(?:código|corrección|\d+\.|[*-]|\`\`\`)).+)*)/i;
  const match = response.match(explanationRegex);

  if (match && match[1]) {
    return match[1].trim();
  }

  return undefined;
}
// Función para sugerir archivos y estructura de proyecto
export async function handleProjectSuggestion(req: Request, res: Response) {
  try {
    const { projectType, description, techStack } = req.body;

    if (!projectType) {
      return res.status(400).json({ error: "Se requiere el tipo de proyecto" });
    }

    console.log(`Generando sugerencia para proyecto: ${projectType}`);
    console.log(`Descripción: ${description || 'No proporcionada'}`);
    console.log(`Stack tecnológico: ${techStack?.join(', ') || 'No especificado'}`);

    // Utilizar el modelo de IA para generar la estructura del proyecto
    const prompt = `
Actúa como un arquitecto de software y planificador de proyectos. 
Necesito crear un proyecto de tipo "${projectType}" con las siguientes características:
${description ? `Descripción: ${description}` : ''}
${techStack?.length ? `Stack tecnológico: ${techStack.join(', ')}` : ''}

Proporciona una estructura de archivos recomendada para este proyecto.
Para cada archivo sugerido, incluye:
1. Nombre del archivo
2. Ruta completa
3. Lenguaje de programación
4. Descripción breve de su propósito
5. Contenido base recomendado (código inicial)

Devuelve la respuesta como un objeto JSON con el siguiente formato:
{
  "projectStructure": {
    "name": "Nombre del proyecto",
    "description": "Descripción general",
    "checklist": [
      { "id": "unique-id", "title": "Paso 1", "description": "Descripción del paso", "completed": false },
      ...
    ],
    "files": [
      {
        "id": "unique-id",
        "name": "nombre-archivo.ext",
        "path": "/ruta/completa/nombre-archivo.ext",
        "language": "lenguaje",
        "description": "Propósito del archivo",
        "content": "Contenido base del archivo",
        "isDirectory": false
      },
      ...
    ]
  }
}
`;

    const response = await generateOpenAIResponse(prompt);

    // Intentar parsear la respuesta como JSON
    try {
      // Buscar el primer objeto JSON válido en la respuesta
      const jsonMatch = response.match(/\{[\s\S]*\}/);
      if (!jsonMatch) {
        throw new Error("No se encontró una estructura JSON válida en la respuesta");
      }

      const projectData = JSON.parse(jsonMatch[0]);

      // Validar la estructura
      if (!projectData.projectStructure || !Array.isArray(projectData.projectStructure.files)) {
        throw new Error("La estructura JSON no tiene el formato esperado");
      }

      res.json(projectData);
    } catch (jsonError) {
      console.error("Error al parsear la respuesta JSON:", jsonError);
      res.status(500).json({ 
        error: "No se pudo generar una estructura de proyecto válida",
        rawResponse: response
      });
    }
  } catch (error: any) {
    console.error("Error al generar sugerencia de proyecto:", error);
    res.status(500).json({ 
      error: error.message || "Error interno del servidor" 
    });
  }
}

// Función para crear archivos en el proyecto
export async function handleFileCreation(req: Request, res: Response) {
  try {
    const { files } = req.body;

    if (!files || !Array.isArray(files) || files.length === 0) {
      return res.status(400).json({ error: "Se requiere al menos un archivo" });
    }

    const fs = require('fs');
    const path = require('path');
    const results = [];

    for (const file of files) {
      try {
        // Validar datos del archivo
        if (!file.path || !file.content) {
          results.push({
            path: file.path || 'desconocido',
            success: false,
            error: "Ruta o contenido no proporcionado"
          });
          continue;
        }

        // Asegurar que el directorio exista
        const dirname = path.dirname(file.path);
        if (!fs.existsSync(dirname)) {
          fs.mkdirSync(dirname, { recursive: true });
        }

        // Escribir el archivo
        fs.writeFileSync(file.path, file.content);

        results.push({
          path: file.path,
          success: true
        });

        console.log(`Archivo creado: ${file.path}`);
      } catch (fileError: any) {
        console.error(`Error al crear archivo ${file.path}:`, fileError);
        results.push({
          path: file.path || 'desconocido',
          success: false,
          error: fileError.message
        });
      }
    }

    res.json({ results });
  } catch (error: any) {
    console.error("Error al crear archivos:", error);
    res.status(500).json({ 
      error: error.message || "Error interno del servidor" 
    });
  }
}

import { exec } from 'child_process';

async function executeCommand(command: string): Promise<string> {
  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error) {
        reject(error);
        return;
      }
      if (stderr) {
        console.error('Command stderr:', stderr);
      }
      resolve(stdout.trim() || stderr.trim() || 'Comando ejecutado');
    });
  });
}