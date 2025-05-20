"""
Context Manager for Claude Code Orchestrator

This module implements the Context Manager component that manages
the context for tasks, including retrieving relevant information
from previous tasks and providing it to the current task.
"""

import logging
from typing import Dict, List, Any, Optional, Set
import json
import time
import os

from .engine import TaskPackage, ResultPackage

# Configure logging
logger = logging.getLogger(__name__)

class ContextManager:
    """
    Manages context for tasks in the orchestration system.
    
    This class is responsible for retrieving, storing, and providing
    relevant context for tasks based on their dependencies and requirements.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the context manager.
        
        Args:
            config: Configuration dictionary for the context manager
        """
        self.config: Dict[str, Any] = config if config is not None else {}
        self.context_store: Dict[str, Dict[str, Any]] = {}
        self.task_results: Dict[str, Any] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        
        # Initialize context storage directory
        self.storage_dir = self.config.get("storage_dir", "context_storage")
        os.makedirs(self.storage_dir, exist_ok=True)
        
        logger.info("Context Manager initialized")
    
    async def get_context(self, task_id: str, task: TaskPackage) -> Dict[str, Any]:
        """
        Get context for a specific task.
        
        This method retrieves relevant context for a task based on its
        dependencies and requirements.
        
        Args:
            task_id: The ID of the task to get context for
            task: The task package containing task details
            
        Returns:
            dict: A dictionary containing the context for the task
        """
        context: Dict[str, Any] = {}
        
        # Add basic task information to context
        context["task_id"] = task_id
        context["task_type"] = task.task_type
        context["timestamp"] = time.time()
        
        # Add dependency context
        dependency_context = await self._get_dependency_context(task)
        context["dependencies"] = dependency_context
        
        # Add task-specific context based on task type
        if task.task_type == "code":
            context["code_context"] = await self._get_code_context(task)
        elif task.task_type == "design":
            context["design_context"] = await self._get_design_context(task)
        elif task.task_type == "debug":
            context["debug_context"] = await self._get_debug_context(task)
        
        # Add any additional context from the task's context field
        context.update(task.context)
        
        # Store the context for future reference
        self.context_store[task_id] = context
        
        # Save context to disk for persistence
        self._save_context(task_id, context)
        
        logger.info(f"Retrieved context for task {task_id}")
        return context
    
    async def _get_dependency_context(self, task: TaskPackage) -> Dict[str, Any]:
        """
        Get context from task dependencies.
        
        Args:
            task: The task package containing dependency information
            
        Returns:
            dict: A dictionary containing context from dependencies
        """
        dependency_context: Dict[str, Any] = {}
        
        for dep_id in task.dependencies:
            # Check if we have results for this dependency
            if dep_id in self.task_results:
                result = self.task_results[dep_id]
                dependency_context[dep_id] = {
                    "status": result.status,
                    "result": result.result,
                    "metadata": result.metadata
                }
            
            # Check if we have stored context for this dependency
            elif dep_id in self.context_store:
                dependency_context[dep_id] = self.context_store[dep_id]
            
            # Try to load context from disk
            else:
                loaded_context = self._load_context(dep_id)
                if loaded_context:
                    dependency_context[dep_id] = loaded_context
                    self.context_store[dep_id] = loaded_context
        
        return dependency_context
    
    async def _get_code_context(self, task: TaskPackage) -> Dict[str, Any]:
        """
        Get context specific to code tasks.
        
        Args:
            task: The task package containing task details
            
        Returns:
            dict: A dictionary containing code-specific context
        """
        # This would typically involve retrieving code files, repository information,
        # code analysis results, etc.
        # For now, we'll return a simple placeholder
        return {
            "language": task.context.get("language", "python"),
            "files": task.context.get("files", []),
            "repository": task.context.get("repository", {})
        }
    
    async def _get_design_context(self, task: TaskPackage) -> Dict[str, Any]:
        """
        Get context specific to design tasks.
        
        Args:
            task: The task package containing task details
            
        Returns:
            dict: A dictionary containing design-specific context
        """
        # This would typically involve retrieving design documents, architecture diagrams,
        # system requirements, etc.
        # For now, we'll return a simple placeholder
        return {
            "architecture": task.context.get("architecture", {}),
            "requirements": task.context.get("requirements", []),
            "constraints": task.context.get("constraints", [])
        }
    
    async def _get_debug_context(self, task: TaskPackage) -> Dict[str, Any]:
        """
        Get context specific to debug tasks.
        
        Args:
            task: The task package containing task details
            
        Returns:
            dict: A dictionary containing debug-specific context
        """
        # This would typically involve retrieving error logs, stack traces,
        # test results, etc.
        # For now, we'll return a simple placeholder
        return {
            "error_logs": task.context.get("error_logs", []),
            "stack_trace": task.context.get("stack_trace", ""),
            "test_results": task.context.get("test_results", {})
        }
    
    def store_task_result(self, task_id: str, result: ResultPackage) -> None:
        """
        Store the result of a completed task.
        
        Args:
            task_id: The ID of the completed task
            result: The result package from the task execution
        """
        self.task_results[task_id] = result
        
        # Update context with the result
        if task_id in self.context_store:
            self.context_store[task_id]["result"] = {
                "status": result.status,
                "data": result.result,
                "error": result.error,
                "execution_time": result.execution_time,
                "metadata": result.metadata
            }
            
            # Save updated context to disk
            self._save_context(task_id, self.context_store[task_id])
        
        logger.info(f"Stored result for task {task_id}")
    
    def update_dependency_graph(self, task_id: str, dependencies: List[str]) -> None:
        """
        Update the dependency graph with a new task and its dependencies.
        
        Args:
            task_id: The ID of the task
            dependencies: List of dependency task IDs
        """
        self.dependency_graph[task_id] = set(dependencies)
        logger.debug(f"Updated dependency graph for task {task_id}")
    
    def get_dependent_tasks(self, task_id: str) -> List[str]:
        """
        Get tasks that depend on a specific task.
        
        Args:
            task_id: The ID of the task to find dependents for
            
        Returns:
            list: A list of task IDs that depend on the specified task
        """
        dependents = []
        for tid, deps in self.dependency_graph.items():
            if task_id in deps:
                dependents.append(tid)
        return dependents
    
    def _save_context(self, task_id: str, context: Dict[str, Any]) -> None:
        """
        Save context to disk for persistence.
        
        Args:
            task_id: The ID of the task
            context: The context dictionary to save
        """
        # Replace any non-serializable objects with string representations
        serializable_context = self._make_serializable(context)
        
        # Create a file path for the context
        file_path = os.path.join(self.storage_dir, f"{task_id}.json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(serializable_context, f, indent=2)
            logger.debug(f"Saved context for task {task_id} to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save context for task {task_id}: {e}")
    
    def _load_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Load context from disk.
        
        Args:
            task_id: The ID of the task to load context for
            
        Returns:
            dict or None: The loaded context dictionary, or None if not found
        """
        file_path = os.path.join(self.storage_dir, f"{task_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r') as f:
                context = json.load(f)
            logger.debug(f"Loaded context for task {task_id} from {file_path}")
            return context
        except Exception as e:
            logger.error(f"Failed to load context for task {task_id}: {e}")
            return None
    
    def _make_serializable(self, obj: Any) -> Any:
        """
        Convert a potentially non-serializable object to a serializable one.
        
        Args:
            obj: The object to make serializable
            
        Returns:
            A serializable version of the object
        """
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            return obj