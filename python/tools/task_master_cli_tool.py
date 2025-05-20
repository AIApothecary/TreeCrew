"""
Task Master CLI Tool for Claude Code Orchestrator

This module implements a tool for Agent Zero that provides a command-line
interface for interacting with the Task Master system.
"""

import logging
import subprocess
import json
import os
import sys
from typing import Dict, List, Any, Optional, Union, TypedDict

# Import the Tool base class from Agent Zero
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from python.helpers.tool import Tool, Response

# Configure logging
logger = logging.getLogger(__name__)

class TaskMasterCliTool(Tool):
    """
    A tool for Agent Zero that provides a command-line interface for
    interacting with the Task Master system.
    
    This tool allows Agent Zero to execute Task Master CLI commands and
    process their results.
    """
    
    def __init__(self, agent, name="task_master_cli", method=None, args=None, message="", **kwargs):
        """Initialize the Task Master CLI tool."""
        super().__init__(agent=agent, name=name, method=method, args=args or {}, message=message, **kwargs)
        
        # Tool metadata
        self.description = "Execute Task Master CLI commands and process their results"
        self.usage = "task_master_cli <command> [options]"
        self.options = {
            "command": {
                "type": "string",
                "description": "The Task Master CLI command to execute (e.g., 'list', 'next', 'show')",
                "required": True
            },
            "args": {
                "type": "object",
                "description": "Arguments for the Task Master CLI command",
                "required": False
            }
        }
        
        # Check if task-master is installed
        self._check_task_master_installed()
        
        logger.info("Task Master CLI tool initialized")
    
    def _check_task_master_installed(self) -> None:
        """
        Check if the task-master CLI is installed.
        
        Raises:
            RuntimeError: If task-master is not installed
        """
        try:
            result = subprocess.run(
                ["task-master", "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                raise RuntimeError("task-master CLI is not installed or not working properly")
                
            logger.info(f"task-master CLI version: {result.stdout.strip()}")
            
        except FileNotFoundError:
            logger.warning("task-master CLI not found, will attempt to use npx")
    
    def _build_command(self, command: str, args: Dict[str, Any]) -> List[str]:
        """
        Build the task-master CLI command with arguments.
        
        Args:
            command: The Task Master CLI command to execute
            args: Arguments for the command
            
        Returns:
            list: The command and its arguments as a list
        """
        # Start with the base command
        cmd = ["task-master", command]
        
        # Add arguments
        for key, value in args.items():
            if key == "id" and command in ["show", "set-status", "update-task", "update-subtask", "expand"]:
                # For commands that take an ID as a positional argument
                cmd.insert(2, str(value))
            elif key == "from" and command == "update":
                # For the update command's --from argument
                cmd.append(f"--from={value}")
            elif key == "status" and command == "set-status":
                # For the set-status command's --status argument
                cmd.append(f"--status={value}")
            elif key == "prompt" and command in ["update", "update-task", "update-subtask", "add-task"]:
                # For commands that take a prompt
                cmd.append(f"--prompt={value}")
            elif key == "file":
                # For the --file argument
                cmd.append(f"--file={value}")
            elif isinstance(value, bool) and value:
                # For boolean flags
                cmd.append(f"--{key}")
            elif not isinstance(value, bool):
                # For other arguments
                cmd.append(f"--{key}={value}")
        
        return cmd
    
    def _execute_command(self, cmd: List[str]) -> Dict[str, Any]:
        """
        Execute a task-master CLI command.
        
        Args:
            cmd: The command and its arguments as a list
            
        Returns:
            dict: The result of the command execution
        """
        try:
            # Try to execute the command directly
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0 and "task-master" in cmd[0]:
                # If the direct command failed, try using npx
                logger.warning("Direct command failed, trying with npx")
                npx_cmd = ["npx", "task-master-ai"] + cmd[1:]
                result = subprocess.run(
                    npx_cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "command": " ".join(cmd)
            }
        
        # Process the result
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd),
            "returncode": result.returncode
        }
    
    def _parse_output(self, command: str, output: str) -> Any:
        """
        Parse the output of a task-master CLI command.
        
        Args:
            command: The Task Master CLI command that was executed
            output: The output of the command
            
        Returns:
            The parsed output, which could be a dictionary, list, or string
        """
        # For commands that return JSON
        if command in ["list", "next", "show"] and output.strip().startswith("{"):
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON output for command '{command}'")
        
        # For commands that return a list of tasks
        if command == "list" and not output.strip().startswith("{"):
            tasks = []
            current_task: Dict[str, str] = {}
            
            for line in output.strip().split("\n"):
                if line.strip().startswith("Task"):
                    if current_task:
                        tasks.append(current_task)
                    current_task = {"id": line.split()[1].rstrip(":")}
                elif ":" in line and current_task:
                    key, value = line.split(":", 1)
                    current_task[key.strip().lower()] = value.strip()
            
            if current_task:
                tasks.append(current_task)
                
            return tasks
        
        # For other commands, return the raw output
        return output.strip()
    
    async def _execute_wrapper(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapper for the execute method to handle the options parameter.
        
        Args:
            options: The options for the tool execution
            
        Returns:
            dict: The result of the tool execution
        """
        result = await self.execute(options=options)
        
        # Convert Response to Dict for helper methods
        return {
            "success": True,
            "command": options.get("command", ""),
            "result": result.message
        }
    
    async def execute(self, **kwargs) -> Response:
        """
        Execute the Task Master CLI tool.
        
        Args:
            **kwargs: Additional arguments for the tool execution
            
        Returns:
            Response: The result of the tool execution
        """
        options = kwargs.get("options", {})
        command = options.get("command")
        args = options.get("args", {})
        
        if not command:
            return Response(
                message="Command is required",
                break_loop=False
            )
        
        # Build the command
        cmd = self._build_command(command, args)
        
        # Execute the command
        execution_result = self._execute_command(cmd)
        
        if not execution_result["success"]:
            error_message = f"Command execution failed: {execution_result['stderr'] or 'Unknown error'}\nCommand: {execution_result['command']}"
            return Response(
                message=error_message,
                break_loop=False
            )
        
        # Parse the output
        parsed_output = self._parse_output(command, execution_result["stdout"])
        
        # Format the response
        result_message = f"Command executed successfully: {execution_result['command']}\n\n"
        result_message += f"Result:\n{json.dumps(parsed_output, indent=2)}"
        
        return Response(
            message=result_message,
            break_loop=False
        )
    
    async def get_tasks(self, status: Optional[str] = None, with_subtasks: bool = False) -> Dict[str, Any]:
        """
        Get a list of tasks from Task Master.
        
        Args:
            status: Filter tasks by status (e.g., "pending", "done")
            with_subtasks: Include subtasks in the result
            
        Returns:
            dict: The result of the command execution
        """
        args = {}
        if status:
            args["status"] = status
        if with_subtasks:
            args["with-subtasks"] = "true"
        
        return await self._execute_wrapper({
            "command": "list",
            "args": args
        })
    
    async def get_next_task(self) -> Dict[str, Any]:
        """
        Get the next task to work on from Task Master.
        
        Returns:
            dict: The result of the command execution
        """
        return await self._execute_wrapper({
            "command": "next"
        })
    
    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        Get details for a specific task from Task Master.
        
        Args:
            task_id: The ID of the task to get details for
            
        Returns:
            dict: The result of the command execution
        """
        return await self._execute_wrapper({
            "command": "show",
            "args": {
                "id": task_id
            }
        })
    
    async def set_task_status(self, task_id: str, status: str) -> Dict[str, Any]:
        """
        Set the status of a task in Task Master.
        
        Args:
            task_id: The ID of the task to set the status for
            status: The status to set (e.g., "pending", "done")
            
        Returns:
            dict: The result of the command execution
        """
        return await self._execute_wrapper({
            "command": "set-status",
            "args": {
                "id": task_id,
                "status": status
            }
        })
    
    async def update_task(self, task_id: str, prompt: str, research: bool = False) -> Dict[str, Any]:
        """
        Update a task in Task Master.
        
        Args:
            task_id: The ID of the task to update
            prompt: The update prompt
            research: Whether to use research mode
            
        Returns:
            dict: The result of the command execution
        """
        args = {
            "id": task_id,
            "prompt": prompt
        }
        
        if research:
            args["research"] = "true"
        
        return await self._execute_wrapper({
            "command": "update-task",
            "args": args
        })
    
    async def update_subtask(self, subtask_id: str, prompt: str, research: bool = False) -> Dict[str, Any]:
        """
        Update a subtask in Task Master.
        
        Args:
            subtask_id: The ID of the subtask to update
            prompt: The update prompt
            research: Whether to use research mode
            
        Returns:
            dict: The result of the command execution
        """
        args = {
            "id": subtask_id,
            "prompt": prompt
        }
        
        if research:
            args["research"] = "true"
        
        return await self._execute_wrapper({
            "command": "update-subtask",
            "args": args
        })
    
    async def add_task(self, prompt: str, dependencies: Optional[str] = None,
                priority: Optional[str] = None, research: bool = False) -> Dict[str, Any]:
        """
        Add a new task to Task Master.
        
        Args:
            prompt: The task description
            dependencies: Comma-separated list of task IDs that this task depends on
            priority: The priority of the task (e.g., "high", "medium", "low")
            research: Whether to use research mode
            
        Returns:
            dict: The result of the command execution
        """
        args = {
            "prompt": prompt
        }
        
        if dependencies:
            args["dependencies"] = dependencies
        
        if priority:
            args["priority"] = priority
        
        if research:
            args["research"] = "true"
        
        return await self._execute_wrapper({
            "command": "add-task",
            "args": args
        })
    
    async def expand_task(self, task_id: str, num: Optional[int] = None,
                   research: bool = False, force: bool = False) -> Dict[str, Any]:
        """
        Expand a task into subtasks in Task Master.
        
        Args:
            task_id: The ID of the task to expand
            num: The number of subtasks to create
            research: Whether to use research mode
            force: Whether to force expansion (clear existing subtasks)
            
        Returns:
            dict: The result of the command execution
        """
        args = {
            "id": task_id
        }
        
        if num:
            args["num"] = str(num)
        
        if research:
            args["research"] = "true"
        
        if force:
            args["force"] = "true"
        
        return await self._execute_wrapper({
            "command": "expand",
            "args": args
        })