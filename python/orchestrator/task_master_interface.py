"""
Task Master Interface for Claude Code Orchestrator

This module provides an interface between the orchestrator components
and the Task Master CLI tool. It handles the conversion between the
Task Master data structures and the orchestrator's TaskPackage/ResultPackage
structures.
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple, Union
import sys
import os

# Add the parent directory to the path to import the Task Master CLI tool
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.task_master_cli_tool import TaskMasterCliTool
from .engine import TaskPackage, ResultPackage

# Configure logging
logger = logging.getLogger(__name__)

class TaskMasterInterface:
    """
    Interface between the orchestrator components and the Task Master CLI tool.
    
    This class provides methods for the orchestrator components to interact
    with the Task Master system via the Task Master CLI tool.
    """
    
    def __init__(self, agent, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Task Master interface.
        
        Args:
            agent: The agent instance to use for the Task Master CLI tool
            config: Configuration dictionary for the Task Master interface
        """
        self.config: Dict[str, Any] = config if config is not None else {}
        self.task_master_cli = TaskMasterCliTool(agent=agent)
        
        # Get configuration values
        self.default_task_file = self.config.get("default_task_file", "./tasks/tasks.json")
        
        logger.info("Task Master Interface initialized")
    
    async def get_next_task(self) -> Optional[TaskPackage]:
        """
        Get the next task to work on from Task Master.
        
        Returns:
            TaskPackage or None: The next task to work on, or None if no task is available
        """
        result = await self.task_master_cli.get_next_task()
        
        if not result.get("success", False):
            logger.error(f"Failed to get next task: {result.get('result', '')}")
            return None
            
        # Parse the result
        try:
            task_data = json.loads(result["result"].split("Result:\n", 1)[1])
            
            # Check if a task was found
            if not task_data or "id" not in task_data:
                logger.info("No next task available")
                return None
                
            # Convert to TaskPackage
            task_package = self._convert_to_task_package(task_data)
            return task_package
            
        except Exception as e:
            logger.error(f"Error parsing next task result: {e}")
            return None
    
    async def get_task(self, task_id: str) -> Optional[TaskPackage]:
        """
        Get details for a specific task from Task Master.
        
        Args:
            task_id: The ID of the task to get details for
            
        Returns:
            TaskPackage or None: The task details, or None if the task is not found
        """
        result = await self.task_master_cli.get_task(task_id)
        
        if not result.get("success", False):
            logger.error(f"Failed to get task {task_id}: {result.get('result', '')}")
            return None
            
        # Parse the result
        try:
            task_data = json.loads(result["result"].split("Result:\n", 1)[1])
            
            # Check if a task was found
            if not task_data or "id" not in task_data:
                logger.warning(f"Task {task_id} not found")
                return None
                
            # Convert to TaskPackage
            task_package = self._convert_to_task_package(task_data)
            return task_package
            
        except Exception as e:
            logger.error(f"Error parsing task {task_id} result: {e}")
            return None
    
    async def get_tasks(self, status: Optional[str] = None) -> List[TaskPackage]:
        """
        Get a list of tasks from Task Master.
        
        Args:
            status: Filter tasks by status (e.g., "pending", "done")
            
        Returns:
            list: A list of TaskPackage objects
        """
        result = await self.task_master_cli.get_tasks(status=status)
        
        if not result.get("success", False):
            logger.error(f"Failed to get tasks: {result.get('result', '')}")
            return []
            
        # Parse the result
        try:
            result_text = result["result"].split("Result:\n", 1)[1]
            tasks_data = json.loads(result_text)
            
            # Convert to TaskPackage objects
            task_packages = []
            for task_data in tasks_data:
                task_package = self._convert_to_task_package(task_data)
                task_packages.append(task_package)
                
            return task_packages
            
        except Exception as e:
            logger.error(f"Error parsing tasks result: {e}")
            return []
    
    async def set_task_status(self, task_id: str, status: str) -> bool:
        """
        Set the status of a task in Task Master.
        
        Args:
            task_id: The ID of the task to set the status for
            status: The status to set (e.g., "pending", "done")
            
        Returns:
            bool: True if the status was set successfully, False otherwise
        """
        result = await self.task_master_cli.set_task_status(task_id, status)
        
        if not result.get("success", False):
            logger.error(f"Failed to set status for task {task_id}: {result.get('result', '')}")
            return False
            
        logger.info(f"Set status for task {task_id} to {status}")
        return True
    
    async def update_task(self, task_id: str, prompt: str, research: bool = False) -> bool:
        """
        Update a task in Task Master.
        
        Args:
            task_id: The ID of the task to update
            prompt: The update prompt
            research: Whether to use research mode
            
        Returns:
            bool: True if the task was updated successfully, False otherwise
        """
        result = await self.task_master_cli.update_task(task_id, prompt, research)
        
        if not result.get("success", False):
            logger.error(f"Failed to update task {task_id}: {result.get('result', '')}")
            return False
            
        logger.info(f"Updated task {task_id}")
        return True
    
    async def update_subtask(self, subtask_id: str, prompt: str, research: bool = False) -> bool:
        """
        Update a subtask in Task Master.
        
        Args:
            subtask_id: The ID of the subtask to update
            prompt: The update prompt
            research: Whether to use research mode
            
        Returns:
            bool: True if the subtask was updated successfully, False otherwise
        """
        result = await self.task_master_cli.update_subtask(subtask_id, prompt, research)
        
        if not result.get("success", False):
            logger.error(f"Failed to update subtask {subtask_id}: {result.get('result', '')}")
            return False
            
        logger.info(f"Updated subtask {subtask_id}")
        return True
    
    async def process_task_result(self, task_id: str, result_package: ResultPackage) -> bool:
        """
        Process a task result and update the task in Task Master.
        
        Args:
            task_id: The ID of the task
            result_package: The result package from the task execution
            
        Returns:
            bool: True if the result was processed successfully, False otherwise
        """
        # Update the task status based on the result
        status = "done" if result_package.status == "success" else "failed"
        success = await self.set_task_status(task_id, status)
        
        if not success:
            return False
            
        # Add result details to the task
        prompt = self._generate_result_prompt(result_package)
        success = await self.update_task(task_id, prompt)
        
        return success
    
    def _convert_to_task_package(self, task_data: Dict[str, Any]) -> TaskPackage:
        """
        Convert a Task Master task data dictionary to a TaskPackage.
        
        Args:
            task_data: The task data from Task Master
            
        Returns:
            TaskPackage: The converted task package
        """
        # Extract task details
        task_id = str(task_data.get("id", ""))
        title = task_data.get("title", "")
        description = task_data.get("description", "")
        details = task_data.get("details", "")
        
        # Combine title, description, and details into the prompt
        prompt = f"{title}\n\n{description}\n\n{details}"
        
        # Extract dependencies
        dependencies = []
        for dep in task_data.get("dependencies", []):
            if isinstance(dep, str):
                dependencies.append(dep)
            elif isinstance(dep, dict) and "id" in dep:
                dependencies.append(str(dep["id"]))
        
        # Extract priority
        priority_map = {"high": 3, "medium": 2, "low": 1}
        priority_str = task_data.get("priority", "medium").lower()
        priority = priority_map.get(priority_str, 2)
        
        # Create context
        context = {
            "title": title,
            "description": description,
            "details": details,
            "test_strategy": task_data.get("testStrategy", ""),
            "subtasks": task_data.get("subtasks", []),
            "original_task_data": task_data
        }
        
        # Create TaskPackage
        task_package = TaskPackage(
            task_id=task_id,
            task_type="code",  # Default to code task type
            prompt=prompt,
            context=context,
            dependencies=dependencies,
            priority=priority
        )
        
        return task_package
    
    def _generate_result_prompt(self, result_package: ResultPackage) -> str:
        """
        Generate a prompt for updating a task with the result.
        
        Args:
            result_package: The result package from the task execution
            
        Returns:
            str: The generated prompt
        """
        prompt = f"Task execution completed with status: {result_package.status}\n\n"
        
        if result_package.status == "success":
            prompt += "The task was completed successfully.\n\n"
            if result_package.result:
                prompt += f"Result:\n{result_package.result}\n\n"
        else:
            prompt += "The task failed to complete.\n\n"
            if result_package.error:
                prompt += f"Error:\n{result_package.error}\n\n"
        
        prompt += f"Execution time: {result_package.execution_time:.2f} seconds\n"
        
        if result_package.metadata:
            prompt += "\nAdditional metadata:\n"
            for key, value in result_package.metadata.items():
                prompt += f"{key}: {value}\n"
        
        return prompt