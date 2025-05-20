"""
Orchestration Engine for Claude Code Orchestrator

This module implements the core orchestration engine that coordinates
the execution of tasks across multiple AI agents.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import json
import asyncio
import time
from dataclasses import dataclass, field

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class TaskPackage:
    """Data structure for tasks sent to worker agents."""
    task_id: str
    task_type: str
    prompt: str
    context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: int = 1
    timeout: int = 300  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ResultPackage:
    """Data structure for results returned from worker agents."""
    task_id: str
    status: str  # 'success', 'failure', 'timeout', 'in_progress'
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrchestrationEngine:
    """
    Core orchestration engine for coordinating AI agent tasks.
    
    This class manages the workflow of distributing tasks to worker agents,
    tracking their progress, handling dependencies, and processing results.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the orchestration engine.
        
        Args:
            config: Configuration dictionary for the orchestration engine
        """
        self.config: Dict[str, Any] = config if config is not None else {}
        self.tasks: Dict[str, TaskPackage] = {}  # task_id -> TaskPackage
        self.results: Dict[str, ResultPackage] = {}  # task_id -> ResultPackage
        self.pending_tasks: List[str] = []  # List of task_ids that are ready to be executed
        self.running_tasks: Dict[str, Tuple[float, str]] = {}  # task_id -> (start_time, worker_id)
        self.completed_tasks: List[str] = []  # List of completed task_ids
        self.failed_tasks: List[str] = []  # List of failed task_ids
        
        # Initialize components (these will be injected by the main module)
        self.pool_manager = None
        self.context_manager = None
        self.results_processor = None
        
        logger.info("Orchestration Engine initialized")
    
    def register_components(self, pool_manager=None, context_manager=None, results_processor=None):
        """
        Register the required components with the orchestration engine.
        
        Args:
            pool_manager: Agent Pool Manager instance
            context_manager: Context Manager instance
            results_processor: Results Processor instance
        """
        self.pool_manager = pool_manager
        self.context_manager = context_manager
        self.results_processor = results_processor
        logger.info("Components registered with Orchestration Engine")
    
    def add_task(self, task: TaskPackage) -> str:
        """
        Add a new task to the orchestration engine.
        
        Args:
            task: TaskPackage object containing task details
            
        Returns:
            task_id: The ID of the added task
        """
        self.tasks[task.task_id] = task
        
        # Check if task is ready to execute (all dependencies satisfied)
        if self._are_dependencies_satisfied(task.task_id):
            self.pending_tasks.append(task.task_id)
            logger.info(f"Task {task.task_id} added to pending queue")
        else:
            logger.info(f"Task {task.task_id} added but waiting for dependencies")
            
        return task.task_id
    
    def _are_dependencies_satisfied(self, task_id: str) -> bool:
        """
        Check if all dependencies for a task are satisfied.
        
        Args:
            task_id: The ID of the task to check
            
        Returns:
            bool: True if all dependencies are satisfied, False otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
                
        return True
    
    async def process_pending_tasks(self):
        """
        Process all pending tasks that are ready to be executed.
        
        This method is the main processing loop that assigns tasks to workers.
        """
        # Sort pending tasks by priority
        self.pending_tasks.sort(key=lambda task_id: self.tasks[task_id].priority, reverse=True)
        
        for task_id in self.pending_tasks[:]:
            # Get an available worker
            if not self.pool_manager:
                logger.error("Pool manager not registered")
                continue
                
            worker = await self.pool_manager.get_available_worker(self.tasks[task_id].task_type)
            if not worker:
                logger.warning(f"No available worker for task {task_id}")
                continue
                
            # Get context for the task
            if not self.context_manager:
                logger.error("Context manager not registered")
                continue
                
            context = await self.context_manager.get_context(task_id, self.tasks[task_id])
            
            # Update task with context
            task = self.tasks[task_id]
            task.context.update(context)
            
            # Assign task to worker
            if not self.pool_manager:
                logger.error("Pool manager not registered")
                continue
                
            worker_id = await self.pool_manager.assign_task(worker, task)
            
            # Update tracking
            self.pending_tasks.remove(task_id)
            self.running_tasks[task_id] = (time.time(), worker_id)
            
            logger.info(f"Task {task_id} assigned to worker {worker_id}")
    
    async def check_running_tasks(self):
        """
        Check the status of all running tasks and handle completed or timed out tasks.
        """
        current_time = time.time()
        
        for task_id, (start_time, worker_id) in list(self.running_tasks.items()):
            task = self.tasks[task_id]
            
            # Check if task has timed out
            if current_time - start_time > task.timeout:
                logger.warning(f"Task {task_id} timed out")
                
                # Create timeout result
                result = ResultPackage(
                    task_id=task_id,
                    status="timeout",
                    result=None,
                    error="Task execution timed out",
                    execution_time=current_time - start_time
                )
                
                # Process the result
                await self._process_task_result(task_id, result)
                
                # Release the worker
                if self.pool_manager:
                    await self.pool_manager.release_worker(worker_id)
                else:
                    logger.error("Pool manager not registered")
                
                # Remove from running tasks
                del self.running_tasks[task_id]
                
                # Add to failed tasks
                self.failed_tasks.append(task_id)
                continue
                
            # Check if task has completed
            if not self.pool_manager:
                logger.error("Pool manager not registered")
                continue
                
            result = await self.pool_manager.get_task_result(worker_id, task_id)
            if result:
                # Process the result
                await self._process_task_result(task_id, result)
                
                # Release the worker
                if self.pool_manager:
                    await self.pool_manager.release_worker(worker_id)
                else:
                    logger.error("Pool manager not registered")
                
                # Remove from running tasks
                del self.running_tasks[task_id]
                
                # Add to completed or failed tasks
                if result.status == "success":
                    self.completed_tasks.append(task_id)
                else:
                    self.failed_tasks.append(task_id)
                    
                # Check if any pending tasks now have their dependencies satisfied
                self._update_pending_tasks()
    
    async def _process_task_result(self, task_id: str, result: ResultPackage):
        """
        Process the result of a completed task.
        
        Args:
            task_id: The ID of the completed task
            result: ResultPackage object containing the task result
        """
        # Store the result
        self.results[task_id] = result
        
        # Process the result with the results processor
        if self.results_processor:
            await self.results_processor.process_result(task_id, result)
            
        logger.info(f"Task {task_id} completed with status: {result.status}")
    
    def _update_pending_tasks(self):
        """
        Update the pending tasks list based on completed dependencies.
        """
        for task_id, task in self.tasks.items():
            if (task_id not in self.pending_tasks and 
                task_id not in self.running_tasks and 
                task_id not in self.completed_tasks and 
                task_id not in self.failed_tasks):
                
                if self._are_dependencies_satisfied(task_id):
                    self.pending_tasks.append(task_id)
                    logger.info(f"Task {task_id} now ready for execution")
    
    async def run(self):
        """
        Main execution loop for the orchestration engine.
        """
        logger.info("Starting orchestration engine execution loop")
        
        while True:
            # Process pending tasks
            await self.process_pending_tasks()
            
            # Check running tasks
            await self.check_running_tasks()
            
            # If no more tasks to process, break the loop
            if not self.pending_tasks and not self.running_tasks:
                break
                
            # Sleep to avoid busy waiting
            await asyncio.sleep(0.1)
            
        logger.info("Orchestration engine execution loop completed")
        
        # Return summary of execution
        return {
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "results": self.results
        }