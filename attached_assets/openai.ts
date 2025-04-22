import OpenAI from "openai";
import { CodeGenerationRequest, CodeGenerationResponse, CodeCorrectionRequest, CodeCorrectionResponse } from "@shared/schema";
import { executeAgent, orchestrateAgents, getAvailableAgents } from "./agents";

const AVAILABLE_MODELS = {
  // OpenAI models
  "gpt-4o": "GPT-4O - Modelo multimodal y multilingüe para texto, imágenes y audio (Mayo 2024)",
  "gpt-o3-mini": "GPT-O3 Mini - Optimizado para tareas de programación (Febrero 2025)",

  // Google models
  "gemini-2.5": "Gemini 2.5 - Modelo avanzado para texto, audio, imágenes, video y código (Marzo 2025)",
  "gemini-2.0-flash": "Gemini 2.0 Flash - Modelo equilibrado entre velocidad y precisión",

  // Anthropic models
  "claude-3.7": "Claude 3.7 - Modelo híbrido para codificación y resolución de problemas complejos (Febrero 2025)",
  "claude-3.5-sonnet-v2": "Claude 3.5 Sonnet V2 - Equilibrio entre rendimiento y velocidad",

  // Alibaba models
  "qwen2.5-omni-7B": "Qwen2.5-Omni-7B - Modelo multimodal para texto, imagen, audio y video (Marzo 2025)"
};

let MODEL = "gpt-4o"; // default model

// Función para cambiar el modelo activo
export function setActiveModel(modelId: string) {
  if (AVAILABLE_MODELS[modelId]) {
    MODEL = modelId;
    console.log(`Modelo activo cambiado a: ${modelId}`);
    return true;
  }
  console.warn(`Modelo solicitado no disponible: ${modelId}. Usando modelo actual: ${MODEL}`);
  return false;
}

// Función para obtener el modelo activo
export function getActiveModel() {
  return MODEL;
}

// Función para validar si un modelo existe
export function isValidModel(modelId: string) {
  return !!AVAILABLE_MODELS[modelId];
}

// Función para obtener todos los modelos disponibles
export function getAvailableModels() {
  return AVAILABLE_MODELS;
}

import * as dotenv from 'dotenv';
dotenv.config({ path: '.env' });

function getOpenAIConfig() {
  const apiKey = process.env.OPENAI_API_KEY?.trim();

  if (!apiKey) {
    throw new Error("OpenAI API key no está configurada. Por favor configura OPENAI_API_KEY en el archivo .env");
  }

  return new OpenAI({
    apiKey: apiKey,
    maxRetries: 3,
    timeout: 30000
  });
}

const openai = getOpenAIConfig();

// Re-exportar para uso en otros módulos
export { openai };

// Interfaz extendida para incluir el plan de acción
interface CodeGenerationWithPlanResponse extends Omit<CodeGenerationResponse, 'files'> {
  plan?: string[];
  architecture?: string;
  components?: string[];
  requirements?: string[];
  language?: string;
  code?: string;
}

/**
 * Crea un plan de desarrollo basado en una descripción
 */
export async function createDevelopmentPlan(description: string, language: string = "javascript"): Promise<CodeGenerationWithPlanResponse> {
  try {
    if (!process.env.OPENAI_API_KEY) {
      throw new Error("OpenAI API key is not configured. Please set the OPENAI_API_KEY environment variable.");
    }

    // Mensaje para el sistema que guía la creación del plan
    const systemMessage = `Eres un experto arquitecto de software encargado de crear planes de desarrollo detallados.
    - Tu tarea es analizar la solicitud del usuario y crear un plan paso a paso para desarrollar la solución.
    - Incluye arquitectura, componentes principales, y requisitos técnicos.
    - No generes código en esta fase, solo el plan de desarrollo.
    - Utiliza un enfoque estructurado y claro.
    - Responde con JSON en este formato exacto: 
    {
      "language": "lenguaje principal a usar",
      "architecture": "descripción breve de la arquitectura",
      "plan": ["paso 1", "paso 2", "..."],
      "components": ["componente 1", "componente 2", "..."],
      "requirements": ["requisito 1", "requisito 2", "..."],
      "code": ""
    }`;

    // Preparar el mensaje con la solicitud y preferencia de lenguaje
    let userMessage = `Crea un plan de desarrollo detallado para: ${description}`;
    if (language && language !== "javascript") {
      userMessage += `\n\nPreferencia de lenguaje: ${language}`;
    }

    const response = await openai.chat.completions.create({
      model: MODEL,
      messages: [
        { role: "system", content: systemMessage },
        { role: "user", content: userMessage }
      ],
      response_format: { type: "json_object" },
      temperature: 0.5,
    });

    const content = response.choices[0].message.content;
    if (!content) {
      throw new Error("No se recibió respuesta del modelo de IA para el plan");
    }

    const parsedResponse = JSON.parse(content);

    // Asegurarse de que la respuesta tiene la estructura esperada
    if (!parsedResponse.plan || !parsedResponse.language) {
      throw new Error("La respuesta del plan no tiene el formato esperado");
    }

    return {
      code: parsedResponse.code || "",
      language: parsedResponse.language,
      plan: parsedResponse.plan || [],
      architecture: parsedResponse.architecture || "",
      components: parsedResponse.components || [],
      requirements: parsedResponse.requirements || [],
      suggestions: []
    };
  } catch (error) {
    console.error("Error creating development plan:", error);
    throw new Error(`Error al crear plan de desarrollo: ${error instanceof Error ? error.message : "Error desconocido"}`);
  }
}

/**
 * Corrige y mejora código existente basado en instrucciones específicas
 */
export async function correctCode(request: CodeCorrectionRequest): Promise<CodeCorrectionResponse> {
  const { content, instructions, language = "javascript" } = request;

  try {
    // Validar entradas
    if (!content || content.trim() === '') {
      throw new Error("El contenido del código no puede estar vacío");
    }

    if (!instructions || instructions.trim() === '') {
      throw new Error("Las instrucciones para la corrección no pueden estar vacías");
    }

    if (!process.env.OPENAI_API_KEY) {
      throw new Error("OpenAI API key is not configured. Please set the OPENAI_API_KEY environment variable.");
    }

    // Detectar el tipo de lenguaje basado en el contenido o usar el proporcionado
    const detectedLanguage = language || (
      content.includes('<html') ? 'html' : 
      content.includes('function') || content.includes('const ') || content.includes('let ') ? 'javascript' : 
      content.includes('{') && content.includes(':') && !content.includes('function') ? 'css' : 
      'javascript'
    );

    // Crear un mensaje del sistema que guía la corrección de código
    const systemMessage = `Eres un experto programador especializado en revisar y mejorar código.
    - Tu tarea es corregir, optimizar y mejorar el código proporcionado según las instrucciones específicas.
    - Mantén el mismo lenguaje y estructura general, a menos que las instrucciones indiquen lo contrario.
    - Proporciona explicaciones claras sobre los cambios realizados.
    - Indica los números de línea donde se realizaron los cambios importantes.
    - Responde con JSON en este formato exacto: 
    {
      "correctedCode": "código completo corregido",
      "changes": [
        {
          "description": "descripción del cambio realizado",
          "lineNumbers": [1, 2, 3]
        }
      ],
      "explanation": "explicación general de las mejoras"
    }`;

    // Preparar el mensaje con el código y las instrucciones
    const userMessage = `
    # Código a corregir (${detectedLanguage}):
    \`\`\`${detectedLanguage}
    ${content}
    \`\`\`

    # Instrucciones para la corrección:
    ${instructions}

    Por favor, corrige y mejora este código siguiendo las instrucciones proporcionadas.`;

    const response = await openai.chat.completions.create({
      model: MODEL,
      messages: [
        { role: "system", content: systemMessage },
        { role: "user", content: userMessage }
      ],
      response_format: { type: "json_object" },
      temperature: 0.5,
    });

    const responseContent = response.choices[0].message.content;
    if (!responseContent) {
      throw new Error("No se recibió respuesta del modelo de IA");
    }

    const parsedResponse = JSON.parse(responseContent);

    // Verificar que la respuesta tiene la estructura esperada
    if (!parsedResponse.correctedCode) {
      throw new Error("La respuesta no contiene el código corregido");
    }

    return {
      correctedCode: parsedResponse.correctedCode,
      changes: parsedResponse.changes || [],
      explanation: parsedResponse.explanation || ""
    };
  } catch (error) {
    console.error("Error correcting code:", error);
    throw new Error(`Error al corregir código: ${error instanceof Error ? error.message : "Error desconocido"}`);
  }
}

export async function generateCode(request: CodeGenerationRequest): Promise<CodeGenerationResponse> {
  const { prompt, language = "javascript", agents } = request;

  try {
    if (!process.env.OPENAI_API_KEY) {
      console.error("OpenAI API key no configurada. Usando respuesta de ejemplo.");
      // Proporcionar una respuesta de ejemplo cuando no hay clave API
      return {
        files: [
          {
            name: "ejemplo.js",
            content: "// Este es un código de ejemplo\n// Para usar la generación de código real, configura OPENAI_API_KEY\n\nconsole.log('Hola mundo');\n\n// Configura la variable de entorno OPENAI_API_KEY en la herramienta Secrets de Replit",
            language: "javascript",
            type: "javascript"
          }
        ],
        suggestions: [
          "Configura la variable de entorno OPENAI_API_KEY para habilitar la generación de código con IA",
          "Puedes obtener una clave API en https://platform.openai.com/api-keys"
        ]
      };
    }

    // Si se solicitan agentes específicos, usar el orquestador de agentes
    if (agents && agents.length > 0) {
      console.log(`Orquestando agentes: ${agents.join(", ")}`);
      const agentResults = await orchestrateAgents(request, agents);

      // Para simplicidad, devolvemos el primer resultado y guardamos información del agente
      if (agentResults.length > 0) {
        const mainResult = agentResults[0];

        // Si hay más de un resultado, agregar sugerencias sobre otros archivos generados
        if (agentResults.length > 1) {
          const suggestions = agentResults.slice(1).map((result, index) => {
            const filePreview = result.files && result.files.length > 0 ? 
              result.files[0].content.substring(0, 50) : 
              "No content available";
            return `Archivo adicional generado por agente ${result.agentName || `#${index+2}`}: ${filePreview}...`;
          });

          return {
            ...mainResult,
            suggestions: [...(mainResult.suggestions || []), ...suggestions]
          };
        }

        return mainResult;
      }
    }

    // Método estándar: Primero, crear un plan de desarrollo
    const developmentPlan = await createDevelopmentPlan(prompt, language);

    // Determinar el lenguaje a utilizar
    const targetLanguage = language || developmentPlan.language || "javascript";

    // Lista de lenguajes soportados para ejecución
    const supportedLanguages = ["javascript", "js", "html", "css"];

    // Crear un mensaje del sistema que guía al AI para generar código
    const systemMessage = `Eres un experto programador que genera código de alta calidad basado en descripciones y planes de desarrollo.
    - Genera MÚLTIPLES ARCHIVOS necesarios para resolver la solicitud, siguiendo el plan proporcionado.
    - Usa buenas prácticas y patrones modernos.
    - Comenta el código cuando sea necesario para explicar partes complejas.
    - IMPORTANTE: En este entorno, SOLAMENTE se pueden ejecutar los siguientes lenguajes: JavaScript, HTML y CSS.
    - PARA APLICACIONES WEB: Debes generar por lo menos tres archivos: index.html, styles.css y script.js.
    - PARA CHATBOTS: Genera como mínimo los archivos HTML, CSS y JavaScript necesarios para implementar un chatbot funcional.
    ${supportedLanguages.includes(targetLanguage.toLowerCase()) 
      ? `- Debes generar código en ${targetLanguage} y sus tecnologías complementarias (HTML/CSS si corresponde).` 
      : `- Aunque la preferencia es ${targetLanguage}, DEBES generar código en JavaScript, HTML y CSS para asegurar la ejecución correcta.`}
    - Responde con JSON en este formato: 
    { 
      "files": [
        {
          "name": "index.html",
          "content": "string con el código HTML",
          "language": "html",
          "type": "html"
        },
        {
          "name": "styles.css",
          "content": "string con el código CSS",
          "language": "css",
          "type": "css"
        },
        {
          "name": "script.js",
          "content": "string con el código JavaScript",
          "language": "javascript",
          "type": "javascript"
        }
      ],
      "suggestions": [
        "Sugerencia 1: Considera usar una librería de componentes UI para mejorar la apariencia.",
        "Sugerencia 2: Asegúrate de que tu CSS esté bien organizado y utilice un preprocesador como Sass o Less."
      ],
      "plan": ["paso 1", "paso 2"],
      "architecture": "descripción de la arquitectura",
      "components": ["componente 1", "componente 2"],
      "requirements": ["requisito 1", "requisito 2"]
    }`;

    // Preparar el mensaje con la solicitud y el plan de desarrollo
    let userMessage = `
Descripción: ${prompt}

Plan de desarrollo:
${developmentPlan.plan?.map((step, index) => `${index + 1}. ${step}`).join('\n') || 'No disponible'}

Arquitectura: ${developmentPlan.architecture || 'No definida'}

Componentes principales:
${developmentPlan.components?.map(comp => `- ${comp}`).join('\n') || 'No definidos'}

Requisitos técnicos:
${developmentPlan.requirements?.map(req => `- ${req}`).join('\n') || 'No definidos'}

IMPORTANTE: DEBES generar código en ${supportedLanguages.includes(targetLanguage.toLowerCase()) 
    ? targetLanguage 
    : "JavaScript (aunque la preferencia es " + targetLanguage + ", este entorno solo ejecuta JavaScript, HTML o CSS)"}.

Ahora, genera el código basado en este plan de desarrollo.`;

    const response = await openai.chat.completions.create({
      model: MODEL,
      messages: [
        { role: "system", content: systemMessage },
        { role: "user", content: userMessage }
      ],
      response_format: { type: "json_object" },
      temperature: 0.7,
    });

    const content = response.choices[0].message.content;
    if (!content) {
      throw new Error("No se recibió respuesta del modelo de IA");
    }

    const parsedResponse = JSON.parse(content);

    // Ensure the response has the expected structure
    if (!parsedResponse.files || !Array.isArray(parsedResponse.files) || parsedResponse.files.length === 0) {
      throw new Error("La respuesta del modelo de IA no tiene el formato esperado. Debe incluir un array de 'files'");
    }

    // Verificar que cada archivo tenga la estructura correcta
    parsedResponse.files.forEach((file: any, index: number) => {
      if (!file.name || !file.content || !file.language || !file.type) {
        throw new Error(`El archivo #${index + 1} no tiene todos los campos requeridos (name, content, language, type)`);
      }
    });

    // Combinar la respuesta del código con el plan de desarrollo
    return {
      files: parsedResponse.files,
      suggestions: parsedResponse.suggestions || [],
      plan: developmentPlan.plan,
      architecture: developmentPlan.architecture,
      components: developmentPlan.components,
      requirements: developmentPlan.requirements
    };
  } catch (error) {
    console.error("Error generating code:", error);
    throw new Error(`Error al generar código: ${error instanceof Error ? error.message : "Error desconocido"}`);
  }
}