"""
Módulo para manejar la descarga y gestión de repositorios de GitHub.
Proporciona funcionalidades para clonar repositorios completos y analizarlos.
"""

import os
import shutil
import logging
import re
from typing import Dict, List, Optional, Union
from git import Repo, GitCommandError

# Configurar el logger
logger = logging.getLogger(__name__)

class GitHubRepoManager:
    """Clase para manejar operaciones con repositorios de GitHub."""
    
    @staticmethod
    def validate_repo_url(url: str) -> bool:
        """
        Valida si la URL proporcionada es una URL de repositorio GitHub válida.
        
        Args:
            url: URL del repositorio
            
        Returns:
            bool: True si la URL es válida, False en caso contrario
        """
        # Patrones válidos para URLs de GitHub
        patterns = [
            r'https?://github\.com/[^/]+/[^/]+(?:\.git)?/?$',
            r'git@github\.com:[^/]+/[^/]+(?:\.git)?/?$'
        ]
        
        return any(re.match(pattern, url) for pattern in patterns)
    
    @staticmethod
    def extract_repo_name(url: str) -> str:
        """
        Extrae el nombre del repositorio desde la URL.
        
        Args:
            url: URL del repositorio
            
        Returns:
            str: Nombre del repositorio
        """
        # Extraer el nombre del repositorio desde la URL
        if 'github.com' in url:
            if url.endswith('.git'):
                url = url[:-4]
            if url.endswith('/'):
                url = url[:-1]
                
            repo_name = url.split('/')[-1]
            return repo_name
        
        return "repo_" + str(hash(url) % 10000)  # Fallback
    
    @staticmethod
    def clone_repository(url: str, destination_dir: str, branch: Optional[str] = None) -> Dict:
        """
        Clona un repositorio GitHub en el directorio especificado.
        
        Args:
            url: URL del repositorio GitHub
            destination_dir: Directorio donde se clonará el repositorio
            branch: Rama específica a clonar (opcional)
            
        Returns:
            dict: Resultado de la operación con claves success, path y message
        """
        try:
            # Validar la URL
            if not GitHubRepoManager.validate_repo_url(url):
                return {
                    'success': False,
                    'error': f"URL de repositorio no válida: {url}"
                }
            
            # Extraer nombre del repositorio para crear el directorio destino
            repo_name = GitHubRepoManager.extract_repo_name(url)
            repo_path = os.path.join(destination_dir, repo_name)
            
            # Comprobar si el directorio ya existe
            if os.path.exists(repo_path):
                return {
                    'success': False,
                    'error': f"Ya existe un repositorio en '{repo_path}'. Usa otro nombre o elimina el existente."
                }
            
            # Crear el directorio padre si no existe
            os.makedirs(destination_dir, exist_ok=True)
            
            # Clonar el repositorio
            logger.info(f"Clonando repositorio desde {url} en {repo_path}")
            
            clone_args = {
                'url': url,
                'to_path': repo_path,
                'depth': 1,  # Clonar solo la última revisión para ahorrar espacio
            }
            
            # Añadir la rama específica si se proporciona
            if branch:
                clone_args['branch'] = branch
            
            # Ejecutar la clonación
            repo = Repo.clone_from(**clone_args)
            
            return {
                'success': True,
                'path': repo_path,
                'message': f"Repositorio clonado exitosamente en '{repo_path}'",
                'repo_name': repo_name,
                'default_branch': repo.active_branch.name
            }
            
        except GitCommandError as e:
            logger.error(f"Error de Git al clonar repositorio: {str(e)}")
            return {
                'success': False,
                'error': f"Error al clonar repositorio: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error al clonar repositorio: {str(e)}")
            return {
                'success': False,
                'error': f"Error al clonar repositorio: {str(e)}"
            }
    
    @staticmethod
    def delete_repository(repo_path: str) -> Dict:
        """
        Elimina un repositorio clonado del sistema de archivos.
        
        Args:
            repo_path: Ruta al repositorio clonado
            
        Returns:
            dict: Resultado de la operación con claves success y message
        """
        try:
            if not os.path.exists(repo_path):
                return {
                    'success': False,
                    'error': f"El repositorio no existe en '{repo_path}'"
                }
            
            # Verificar que es un directorio de Git
            if not os.path.exists(os.path.join(repo_path, '.git')):
                return {
                    'success': False,
                    'error': f"El directorio '{repo_path}' no es un repositorio Git"
                }
            
            # Eliminar el repositorio
            shutil.rmtree(repo_path)
            
            return {
                'success': True,
                'message': f"Repositorio eliminado exitosamente de '{repo_path}'"
            }
            
        except Exception as e:
            logger.error(f"Error al eliminar repositorio: {str(e)}")
            return {
                'success': False,
                'error': f"Error al eliminar repositorio: {str(e)}"
            }
    
    @staticmethod
    def analyze_repository(repo_path: str) -> Dict:
        """
        Analiza un repositorio para obtener información sobre su estructura.
        
        Args:
            repo_path: Ruta al repositorio clonado
            
        Returns:
            dict: Información sobre el repositorio (estructura, lenguajes, etc.)
        """
        try:
            if not os.path.exists(repo_path):
                return {
                    'success': False,
                    'error': f"El repositorio no existe en '{repo_path}'"
                }
            
            # Verificar que es un directorio de Git
            if not os.path.exists(os.path.join(repo_path, '.git')):
                return {
                    'success': False,
                    'error': f"El directorio '{repo_path}' no es un repositorio Git"
                }
            
            # Inicializar repo
            repo = Repo(repo_path)
            
            # Obtener información básica
            result = {
                'success': True,
                'name': os.path.basename(repo_path),
                'path': repo_path,
                'active_branch': repo.active_branch.name,
                'last_commit': {
                    'hash': repo.head.commit.hexsha,
                    'author': f"{repo.head.commit.author.name} <{repo.head.commit.author.email}>",
                    'date': repo.head.commit.committed_datetime.isoformat(),
                    'message': repo.head.commit.message.strip()
                },
                'stats': {
                    'files': 0,
                    'directories': 0,
                    'size': 0
                },
                'file_types': {},
                'structure': {}
            }
            
            # Analizar estructura de archivos
            for root, dirs, files in os.walk(repo_path):
                # Excluir directorio .git
                if '.git' in dirs:
                    dirs.remove('.git')
                
                rel_path = os.path.relpath(root, repo_path)
                if rel_path == '.':
                    rel_path = ''
                
                # Actualizar estadísticas
                result['stats']['directories'] += len(dirs)
                result['stats']['files'] += len(files)
                
                # Construir estructura de directorios
                current_level = result['structure']
                if rel_path:
                    path_parts = rel_path.split(os.sep)
                    for part in path_parts:
                        if part not in current_level:
                            current_level[part] = {}
                        current_level = current_level[part]
                
                # Analizar archivos
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    result['stats']['size'] += file_size
                    
                    # Contar tipos de archivo
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext:
                        if file_ext not in result['file_types']:
                            result['file_types'][file_ext] = {
                                'count': 0,
                                'size': 0
                            }
                        result['file_types'][file_ext]['count'] += 1
                        result['file_types'][file_ext]['size'] += file_size
                    
                    # Añadir archivo a la estructura
                    if isinstance(current_level, dict):
                        current_level[file] = file_size
            
            # Convertir tamaño a formato legible
            result['stats']['size_formatted'] = GitHubRepoManager.format_file_size(result['stats']['size'])
            
            return result
            
        except Exception as e:
            logger.error(f"Error al analizar repositorio: {str(e)}")
            return {
                'success': False,
                'error': f"Error al analizar repositorio: {str(e)}"
            }
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Formatea el tamaño en bytes a un formato legible.
        
        Args:
            size_bytes: Tamaño en bytes
            
        Returns:
            str: Tamaño formateado
        """
        size_float = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_float < 1024 or unit == 'TB':
                return f"{size_float:.2f} {unit}"
            size_float /= 1024
        
        # Caso improbable, pero asegura que siempre retorne un string
        return f"{size_float:.2f} TB"


def clone_github_repository(url: str, workspace_dir: str, branch: Optional[str] = None) -> Dict:
    """
    Función principal para clonar un repositorio de GitHub.
    
    Args:
        url: URL del repositorio
        workspace_dir: Directorio de trabajo donde se clonará
        branch: Rama específica (opcional)
        
    Returns:
        dict: Resultado de la operación
    """
    return GitHubRepoManager.clone_repository(url, workspace_dir, branch)


def delete_github_repository(repo_path: str) -> Dict:
    """
    Elimina un repositorio clonado.
    
    Args:
        repo_path: Ruta al repositorio
        
    Returns:
        dict: Resultado de la operación
    """
    return GitHubRepoManager.delete_repository(repo_path)


def analyze_github_repository(repo_path: str) -> Dict:
    """
    Analiza un repositorio clonado.
    
    Args:
        repo_path: Ruta al repositorio
        
    Returns:
        dict: Información del repositorio
    """
    return GitHubRepoManager.analyze_repository(repo_path)