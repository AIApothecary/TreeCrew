"""
Results Processor for Claude Code Orchestrator

This module implements the Results Processor component that processes
the results of completed tasks, including storing them, analyzing them,
and providing feedback to the orchestration engine.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import json
import os
import time
from dataclasses import asdict

from .engine import ResultPackage

# Configure logging
logger = logging.getLogger(__name__)

class ResultsProcessor:
    """
    Processes results from completed tasks.
    
    This class is responsible for processing, analyzing, and storing
    the results of completed tasks, as well as providing feedback
    to the orchestration engine.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the results processor.
        
        Args:
            config: Configuration dictionary for the results processor
        """
        self.config: Dict[str, Any] = config if config is not None else {}
        self.results: Dict[str, ResultPackage] = {}
        self.result_history: Dict[str, List[ResultPackage]] = {}
        
        # Initialize results storage directory
        self.storage_dir = self.config.get("storage_dir", "results_storage")
        os.makedirs(self.storage_dir, exist_ok=True)
        
        logger.info("Results Processor initialized")
    
    async def process_result(self, task_id: str, result: ResultPackage) -> Dict[str, Any]:
        """
        Process the result of a completed task.
        
        This method analyzes the result, stores it, and provides feedback
        to the orchestration engine.
        
        Args:
            task_id: The ID of the completed task
            result: The result package from the task execution
            
        Returns:
            dict: A dictionary containing feedback for the orchestration engine
        """
        # Store the result
        self.results[task_id] = result
        
        # Add to result history
        if task_id not in self.result_history:
            self.result_history[task_id] = []
        self.result_history[task_id].append(result)
        
        # Save result to disk
        self._save_result(task_id, result)
        
        # Analyze the result
        analysis = await self._analyze_result(task_id, result)
        
        # Generate feedback
        feedback = self._generate_feedback(task_id, result, analysis)
        
        logger.info(f"Processed result for task {task_id}")
        return feedback
    
    async def _analyze_result(self, task_id: str, result: ResultPackage) -> Dict[str, Any]:
        """
        Analyze the result of a completed task.
        
        Args:
            task_id: The ID of the completed task
            result: The result package from the task execution
            
        Returns:
            dict: A dictionary containing the analysis results
        """
        analysis: Dict[str, Any] = {}
        
        # Basic analysis
        analysis["status"] = result.status
        analysis["execution_time"] = result.execution_time
        analysis["has_error"] = result.error is not None
        
        # Status-specific analysis
        if result.status == "success":
            analysis["success"] = True
            analysis["quality"] = self._assess_result_quality(result)
        elif result.status == "failure":
            analysis["success"] = False
            analysis["error_type"] = self._categorize_error(result.error)
            analysis["retry_recommended"] = self._should_retry(result)
        elif result.status == "timeout":
            analysis["success"] = False
            analysis["timeout_reason"] = "Task execution exceeded allowed time"
            analysis["retry_recommended"] = True
        
        return analysis
    
    def _assess_result_quality(self, result: ResultPackage) -> str:
        """
        Assess the quality of a successful result.
        
        Args:
            result: The result package to assess
            
        Returns:
            str: A quality assessment ("high", "medium", or "low")
        """
        # This would typically involve more sophisticated analysis
        # For now, we'll use a simple heuristic
        if not result.result:
            return "low"
        
        # Check if result is a string and has substantial content
        if isinstance(result.result, str) and len(result.result) < 10:
            return "low"
            
        return "high"
    
    def _categorize_error(self, error: Optional[str]) -> str:
        """
        Categorize the type of error in a failed result.
        
        Args:
            error: The error message from the result
            
        Returns:
            str: The error category
        """
        if not error:
            return "unknown"
            
        # Check for common error types
        if "timeout" in error.lower():
            return "timeout"
        elif "permission" in error.lower():
            return "permission"
        elif "not found" in error.lower():
            return "not_found"
        elif "syntax" in error.lower():
            return "syntax"
        elif "value" in error.lower():
            return "value"
        elif "type" in error.lower():
            return "type"
        elif "memory" in error.lower():
            return "memory"
        elif "connection" in error.lower():
            return "connection"
        
        return "other"
    
    def _should_retry(self, result: ResultPackage) -> bool:
        """
        Determine if a failed task should be retried.
        
        Args:
            result: The result package from the failed task
            
        Returns:
            bool: True if the task should be retried, False otherwise
        """
        if not result.error:
            return False
            
        # Check for retriable error types
        error_type = self._categorize_error(result.error)
        retriable_errors = ["timeout", "connection", "memory"]
        
        return error_type in retriable_errors
    
    def _generate_feedback(self, task_id: str, result: ResultPackage, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate feedback for the orchestration engine based on the result and analysis.
        
        Args:
            task_id: The ID of the completed task
            result: The result package from the task execution
            analysis: The analysis of the result
            
        Returns:
            dict: A dictionary containing feedback for the orchestration engine
        """
        feedback: Dict[str, Any] = {}
        
        # Basic feedback
        feedback["task_id"] = task_id
        feedback["status"] = result.status
        feedback["analysis"] = analysis
        
        # Recommendations
        recommendations = []
        
        if result.status == "success":
            if analysis["quality"] == "low":
                recommendations.append("Review result quality")
        elif result.status == "failure":
            if analysis.get("retry_recommended", False):
                recommendations.append("Retry task")
            else:
                recommendations.append("Investigate error")
        elif result.status == "timeout":
            recommendations.append("Increase timeout or optimize task")
        
        feedback["recommendations"] = recommendations
        
        return feedback
    
    def _save_result(self, task_id: str, result: ResultPackage) -> None:
        """
        Save a result to disk for persistence.
        
        Args:
            task_id: The ID of the task
            result: The result package to save
        """
        # Convert result to a serializable dictionary
        result_dict = asdict(result)
        
        # Create a file path for the result
        file_path = os.path.join(self.storage_dir, f"{task_id}_{int(time.time())}.json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(result_dict, f, indent=2)
            logger.debug(f"Saved result for task {task_id} to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save result for task {task_id}: {e}")
    
    def get_result(self, task_id: str) -> Optional[ResultPackage]:
        """
        Get the most recent result for a specific task.
        
        Args:
            task_id: The ID of the task to get the result for
            
        Returns:
            ResultPackage or None: The result package if available, None otherwise
        """
        return self.results.get(task_id)
    
    def get_result_history(self, task_id: str) -> List[ResultPackage]:
        """
        Get the history of results for a specific task.
        
        Args:
            task_id: The ID of the task to get the result history for
            
        Returns:
            list: A list of result packages for the task
        """
        return self.result_history.get(task_id, [])
    
    def get_all_results(self) -> Dict[str, ResultPackage]:
        """
        Get all stored results.
        
        Returns:
            dict: A dictionary mapping task IDs to their most recent result packages
        """
        return self.results
    
    def get_results_by_status(self, status: str) -> Dict[str, ResultPackage]:
        """
        Get all results with a specific status.
        
        Args:
            status: The status to filter by (e.g., "success", "failure", "timeout")
            
        Returns:
            dict: A dictionary mapping task IDs to their result packages
        """
        return {
            task_id: result for task_id, result in self.results.items()
            if result.status == status
        }
    
    def get_success_rate(self) -> float:
        """
        Calculate the success rate of all processed tasks.
        
        Returns:
            float: The success rate as a percentage (0-100)
        """
        if not self.results:
            return 0.0
            
        successful_tasks = len(self.get_results_by_status("success"))
        total_tasks = len(self.results)
        
        return (successful_tasks / total_tasks) * 100.0
    
    def get_average_execution_time(self) -> float:
        """
        Calculate the average execution time of all processed tasks.
        
        Returns:
            float: The average execution time in seconds
        """
        if not self.results:
            return 0.0
            
        total_time = sum(result.execution_time for result in self.results.values())
        total_tasks = len(self.results)
        
        return total_time / total_tasks
    
    def get_error_distribution(self) -> Dict[str, int]:
        """
        Calculate the distribution of error types across failed tasks.
        
        Returns:
            dict: A dictionary mapping error types to their counts
        """
        error_counts: Dict[str, int] = {}
        
        for result in self.results.values():
            if result.status == "failure" and result.error:
                error_type = self._categorize_error(result.error)
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return error_counts