"""
Agent Pool Manager for Claude Code Orchestrator

This module implements the Agent Pool Manager component that manages
the pool of AI agent workers and their assignment to tasks.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
import uuid
import time

from .engine import TaskPackage, ResultPackage

# Configure logging
logger = logging.getLogger(__name__)

class AgentWorker:
    """
    Represents an AI agent worker that can execute tasks.
    
    This class encapsulates the state and capabilities of an individual
    AI agent worker in the pool.
    """
    
    def __init__(self, worker_id: str, worker_type: str, capabilities: List[str]):
        """
        Initialize an agent worker.
        
        Args:
            worker_id: Unique identifier for the worker
            worker_type: Type of worker (e.g., 'code', 'architect', 'debug')
            capabilities: List of task types this worker can handle
        """
        self.worker_id = worker_id
        self.worker_type = worker_type
        self.capabilities = capabilities
        self.busy = False
        self.current_task: Optional[str] = None
        self.last_active = time.time()
        self.results: Dict[str, ResultPackage] = {}
    
    def can_handle(self, task_type: str) -> bool:
        """
        Check if this worker can handle a specific task type.
        
        Args:
            task_type: The type of task to check
            
        Returns:
            bool: True if the worker can handle the task, False otherwise
        """
        return task_type in self.capabilities
    
    def assign_task(self, task_id: str) -> None:
        """
        Assign a task to this worker.
        
        Args:
            task_id: The ID of the task being assigned
        """
        self.busy = True
        self.current_task = task_id
        self.last_active = time.time()
    
    def release(self) -> None:
        """Release this worker from its current task."""
        self.busy = False
        self.current_task = None
        self.last_active = time.time()
    
    def set_result(self, task_id: str, result: ResultPackage) -> None:
        """
        Store the result of a completed task.
        
        Args:
            task_id: The ID of the completed task
            result: The result package from the task execution
        """
        self.results[task_id] = result
    
    def get_result(self, task_id: str) -> Optional[ResultPackage]:
        """
        Get the result of a completed task.
        
        Args:
            task_id: The ID of the task to get the result for
            
        Returns:
            ResultPackage or None: The result package if available, None otherwise
        """
        return self.results.get(task_id)
    
    def clear_result(self, task_id: str) -> None:
        """
        Clear the result of a completed task.
        
        Args:
            task_id: The ID of the task to clear the result for
        """
        if task_id in self.results:
            del self.results[task_id]


class PoolManager:
    """
    Manages a pool of AI agent workers.
    
    This class is responsible for creating, tracking, and assigning workers
    to tasks based on their capabilities and availability.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the pool manager.
        
        Args:
            config: Configuration dictionary for the pool manager
        """
        self.config: Dict[str, Any] = config if config is not None else {}
        self.workers: Dict[str, AgentWorker] = {}
        self.worker_types: Dict[str, List[str]] = {
            "code": ["code", "refactor", "implement"],
            "architect": ["design", "architecture"],
            "debug": ["debug", "fix", "test"],
            "general": ["general", "research", "analyze"]
        }
        
        # Initialize the worker pool
        self._initialize_worker_pool()
        
        logger.info("Pool Manager initialized with %d workers", len(self.workers))
    
    def _initialize_worker_pool(self) -> None:
        """Initialize the pool of workers based on configuration."""
        # Get worker pool configuration
        pool_config = self.config.get("worker_pool", {})
        
        # Create workers for each worker type
        for worker_type, capabilities in self.worker_types.items():
            # Get the number of workers for this type (default: 2)
            count = pool_config.get(f"{worker_type}_count", 2)
            
            # Create the specified number of workers
            for i in range(count):
                worker_id = f"{worker_type}-{uuid.uuid4().hex[:8]}"
                self.workers[worker_id] = AgentWorker(worker_id, worker_type, capabilities)
                logger.debug(f"Created worker {worker_id} of type {worker_type}")
    
    async def get_available_worker(self, task_type: str) -> Optional[str]:
        """
        Get an available worker that can handle a specific task type.
        
        Args:
            task_type: The type of task that needs to be handled
            
        Returns:
            str or None: The ID of an available worker, or None if no worker is available
        """
        # Find all workers that can handle this task type and are not busy
        available_workers = [
            worker_id for worker_id, worker in self.workers.items()
            if worker.can_handle(task_type) and not worker.busy
        ]
        
        if not available_workers:
            logger.warning(f"No available workers for task type: {task_type}")
            return None
        
        # Sort by last active time (oldest first) to ensure fair distribution
        available_workers.sort(
            key=lambda worker_id: self.workers[worker_id].last_active
        )
        
        return available_workers[0] if available_workers else None
    
    async def assign_task(self, worker_id: str, task: TaskPackage) -> str:
        """
        Assign a task to a specific worker.
        
        Args:
            worker_id: The ID of the worker to assign the task to
            task: The task package to assign
            
        Returns:
            str: The worker ID that the task was assigned to
            
        Raises:
            ValueError: If the worker is not available or cannot handle the task
        """
        worker = self.workers.get(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")
        
        if worker.busy:
            raise ValueError(f"Worker {worker_id} is busy")
        
        if not worker.can_handle(task.task_type):
            raise ValueError(
                f"Worker {worker_id} cannot handle task type {task.task_type}"
            )
        
        # Assign the task to the worker
        worker.assign_task(task.task_id)
        
        # Simulate task execution in a separate task
        asyncio.create_task(self._execute_task(worker_id, task))
        
        logger.info(f"Assigned task {task.task_id} to worker {worker_id}")
        return worker_id
    
    async def _execute_task(self, worker_id: str, task: TaskPackage) -> None:
        """
        Simulate task execution by a worker.
        
        In a real implementation, this would communicate with the actual worker
        process or service to execute the task.
        
        Args:
            worker_id: The ID of the worker executing the task
            task: The task package to execute
        """
        worker = self.workers.get(worker_id)
        if not worker:
            logger.error(f"Worker {worker_id} not found for task execution")
            return
        
        try:
            # Simulate task execution time
            execution_time = min(task.timeout * 0.8, 5.0)  # For simulation, cap at 5 seconds
            await asyncio.sleep(execution_time)
            
            # Create a success result
            result = ResultPackage(
                task_id=task.task_id,
                status="success",
                result=f"Simulated result for task {task.task_id}",
                execution_time=execution_time,
                metadata={"worker_id": worker_id}
            )
            
            # Store the result
            worker.set_result(task.task_id, result)
            
            logger.info(f"Worker {worker_id} completed task {task.task_id}")
            
        except Exception as e:
            # Create a failure result
            result = ResultPackage(
                task_id=task.task_id,
                status="failure",
                result=None,
                error=str(e),
                execution_time=time.time() - worker.last_active,
                metadata={"worker_id": worker_id}
            )
            
            # Store the result
            worker.set_result(task.task_id, result)
            
            logger.error(f"Worker {worker_id} failed task {task.task_id}: {e}")
    
    async def release_worker(self, worker_id: str) -> None:
        """
        Release a worker from its current task.
        
        Args:
            worker_id: The ID of the worker to release
            
        Raises:
            ValueError: If the worker is not found
        """
        worker = self.workers.get(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")
        
        worker.release()
        logger.info(f"Released worker {worker_id}")
    
    async def get_task_result(self, worker_id: str, task_id: str) -> Optional[ResultPackage]:
        """
        Get the result of a task from a worker.
        
        Args:
            worker_id: The ID of the worker that executed the task
            task_id: The ID of the task to get the result for
            
        Returns:
            ResultPackage or None: The result package if available, None otherwise
            
        Raises:
            ValueError: If the worker is not found
        """
        worker = self.workers.get(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")
        
        result = worker.get_result(task_id)
        if result:
            # Clear the result from the worker to free up memory
            worker.clear_result(task_id)
        
        return result
    
    async def get_worker_status(self, worker_id: str) -> Dict[str, Any]:
        """
        Get the status of a specific worker.
        
        Args:
            worker_id: The ID of the worker to get the status for
            
        Returns:
            dict: A dictionary containing the worker's status
            
        Raises:
            ValueError: If the worker is not found
        """
        worker = self.workers.get(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")
        
        return {
            "worker_id": worker.worker_id,
            "worker_type": worker.worker_type,
            "capabilities": worker.capabilities,
            "busy": worker.busy,
            "current_task": worker.current_task,
            "last_active": worker.last_active
        }
    
    async def get_all_worker_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all workers.
        
        Returns:
            dict: A dictionary mapping worker IDs to their status dictionaries
        """
        return {
            worker_id: await self.get_worker_status(worker_id)
            for worker_id in self.workers
        }