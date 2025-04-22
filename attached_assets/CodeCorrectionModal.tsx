import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { apiRequest } from "@/lib/queryClient";
import { CodeCorrectionResponse } from "@shared/schema";
import { useToast } from "@/hooks/use-toast";

interface CodeCorrectionModalProps {
  file: {
    id: number;
    name: string;
    content: string;
    type: string;
  };
  onClose: () => void;
  onApplyChanges: (correctedCode: string) => Promise<void>;
  projectId?: number;
}

const CodeCorrectionModal: React.FC<CodeCorrectionModalProps> = ({
  file,
  onClose,
  onApplyChanges,
  projectId
}) => {
  const [instructions, setInstructions] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [correctionResult, setCorrectionResult] = useState<CodeCorrectionResponse | null>(null);
  const [diffView, setDiffView] = useState(false);
  const [editedCode, setEditedCode] = useState(file.content || '');
  const { toast } = useToast();

  useEffect(() => {
    resetState();
  }, [file.id]);

  const resetState = () => {
    setCorrectionResult(null);
    setInstructions("");
    setDiffView(false);
    setEditedCode(file.content || '');
  };

  // Asegurarse de que se actualice el contenido cuando cambia el archivo
  useEffect(() => {
    setEditedCode(file.content || '');
  }, [file.content]);

  const requestCorrection = async () => {
    if (!instructions.trim()) {
      showErrorToast("Por favor, describe las correcciones que necesitas");
      return;
    }

    if (!editedCode.trim()) {
      showErrorToast("El contenido del archivo está vacío");
      return;
    }

    try {
      setIsLoading(true);
      validateFileId();

      const response = await apiRequest("POST", "/api/correct", {
        fileId: file.id,
        content: editedCode,
        instructions,
        language: getLanguageFromType(file.type),
        projectId
      });

      const result: CodeCorrectionResponse = await response.json();
      setCorrectionResult(result);
    } catch (error) {
      console.error("Error al corregir el código:", error);
      showErrorToast("No se pudo corregir el código. Intente con instrucciones más claras.");
    } finally {
      setIsLoading(false);
    }
  };

  const validateFileId = () => {
    if (!file.id) {
      throw new Error("ID de archivo inválido o no especificado");
    }
  };

  const showErrorToast = (message: string) => {
    toast({
      title: "Error",
      description: message,
      variant: "destructive"
    });
  };

  const handleApplyChanges = async () => {
    if (!correctionResult) return;

    try {
      await onApplyChanges(correctionResult.correctedCode);
      toast({
        title: "Correcciones aplicadas",
        description: "El código ha sido actualizado con éxito",
      });
      onClose();
    } catch (error) {
      console.error("Error al aplicar correcciones:", error);
      showErrorToast("No se pudieron aplicar las correcciones");
    }
  };

  const getLanguageFromType = (type: string): string => {
    const typeToLanguage: Record<string, string> = {
      'javascript': 'javascript',
      'html': 'html',
      'css': 'css',
      'typescript': 'typescript',
      'json': 'json',
    };

    return typeToLanguage[type] || 'text';
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
          <h2 className="text-xl font-semibold">Corrección de Código: {file.name}</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md"
            aria-label="Cerrar"
          >
            <i className="ri-close-line text-xl"></i>
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4 flex flex-col gap-4">
          {!correctionResult ? (
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Instrucciones para la corrección:</label>
                <Textarea
                  placeholder="Describe qué correcciones necesitas en el código. Por ejemplo: 'Corrige el manejo de errores y optimiza el rendimiento'"
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  className="min-h-[100px]"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Código actual:</label>
                <div className="bg-slate-100 dark:bg-slate-900 p-3 rounded-md overflow-auto max-h-[300px] text-sm whitespace-pre-wrap">
                  <pre>
                    <code className="language-{getLanguageFromType(file.type)}">
                      {editedCode}
                    </code>
                  </pre>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Resultado de la corrección</h3>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setDiffView(!diffView)}
                  >
                    <i className={`ri-${diffView ? 'code-line' : 'git-pull-request-line'} mr-2`}></i>
                    {diffView ? 'Ver código' : 'Ver cambios'}
                  </Button>
                </div>
              </div>

              {diffView ? (
                <div>
                  <h4 className="text-sm font-medium mb-2">Cambios realizados:</h4>
                  <div className="bg-slate-100 dark:bg-slate-900 p-3 rounded-md overflow-auto max-h-[400px]">
                    {correctionResult.changes && correctionResult.changes.length > 0 ? (
                      correctionResult.changes.map((change, idx) => (
                        <div key={idx} className="mb-3 border-l-2 border-blue-500 pl-2">
                          <p className="font-medium text-sm">{change.description}</p>
                          {change.lineNumbers && (
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                              Líneas: {change.lineNumbers.join(', ')}
                            </p>
                          )}
                        </div>
                      ))
                    ) : (
                      <p className="text-sm italic text-slate-600 dark:text-slate-400">
                        No se especificaron cambios detallados.
                      </p>
                    )}

                    {correctionResult.explanation ? (
                      <div className="mt-4 pt-4 border-t border-slate-300 dark:border-slate-700">
                        <h4 className="text-sm font-medium mb-2">Explicación general:</h4>
                        <p className="text-sm whitespace-pre-wrap">{correctionResult.explanation}</p>
                      </div>
                    ) : (
                      <div className="mt-4 pt-4 border-t border-slate-300 dark:border-slate-700">
                        <p className="text-sm italic text-slate-600 dark:text-slate-400">
                          No se proporcionó una explicación detallada.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div>
                  <h4 className="text-sm font-medium mb-2">Código corregido:</h4>
                  {correctionResult.correctedCode ? (
                    <pre className="bg-slate-100 dark:bg-slate-900 p-3 rounded-md overflow-auto max-h-[400px] text-sm whitespace-pre-wrap">
                      <code className="language-{getLanguageFromType(file.type)}">
                        {correctionResult.correctedCode}
                      </code>
                    </pre>
                  ) : (
                    <div className="bg-slate-100 dark:bg-slate-900 p-3 rounded-md">
                      <p className="text-sm italic text-slate-600 dark:text-slate-400">
                        No se pudo generar el código corregido.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-2">
          {!correctionResult ? (
            <>
              <Button variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button onClick={requestCorrection} disabled={isLoading || !instructions.trim()}>
                {isLoading ? (
                  <>
                    <i className="ri-loader-4-line animate-spin mr-2"></i>
                    Corrigiendo...
                  </>
                ) : "Corregir código"}
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setCorrectionResult(null)}>
                Volver a editar
              </Button>
              <Button onClick={handleApplyChanges}>
                Aplicar cambios
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default CodeCorrectionModal;
