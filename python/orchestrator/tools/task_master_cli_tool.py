import subprocess
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class TaskMasterCliTool:
    """
    A wrapper for the Task Master CLI tool (task-master-ai).
    It assumes 'task-master' command is available in the system PATH.
    """
    def __init__(self, agent: Optional[Any] = None, cli_command: str = "task-master"):
        """
        Initializes the TaskMasterCliTool.
        Args:
            agent: An optional agent instance (for future use or context).
            cli_command: The command to run Task Master CLI.
        """
        self.agent = agent 
        self.cli_command = cli_command
        logger.info(f"TaskMasterCliTool initialized to use command: '{self.cli_command}'")

    async def _execute_command(self, command_args: List[str]) -> Dict[str, Any]:
        """
        Asynchronously executes a Task Master CLI command.
        Args:
            command_args: A list of arguments for the command.
        Returns:
            A dictionary containing the success status, result, and error.
        """
        full_command = [self.cli_command] + command_args
        logger.debug(f"Executing Task Master command: {' '.join(full_command)}")
        try:
            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            stdout_str = stdout.decode('utf-8').strip()
            stderr_str = stderr.decode('utf-8').strip()

            if process.returncode == 0:
                # Task Master CLI often outputs JSON directly or after "Result:\n"
                # Some informational commands might just print text.
                # We attempt to parse JSON, but fall back to text if it fails.
                parsed_result: Any = stdout_str 
                try:
                    # Check for "Result:\n" prefix and try to parse what's after it
                    if "Result:\n" in stdout_str:
                        json_part = stdout_str.split("Result:\n", 1)[1].strip()
                        if json_part: # Ensure there's content after "Result:\n"
                           parsed_result = json.loads(json_part)
                    # If no "Result:\n" or if json_part was empty, try parsing the whole string if it looks like JSON
                    elif (stdout_str.startswith("{") and stdout_str.endswith("}")) or \
                         (stdout_str.startswith("[") and stdout_str.endswith("]")):
                        parsed_result = json.loads(stdout_str)
                    # If it's not clearly JSON, keep it as string.
                except json.JSONDecodeError:
                    logger.warning(f"Command output was not valid JSON, returning as string. Raw output: {stdout_str}")
                    # parsed_result remains stdout_str
                
                logger.debug(f"Command successful. Parsed/Raw Output: {parsed_result}")
                return {"success": True, "result": parsed_result, "error": None}
            else:
                logger.error(f"Command failed with return code {process.returncode}. Stderr: {stderr_str}. Stdout: {stdout_str}")
                return {"success": False, "result": stdout_str, "error": stderr_str or f"Command failed with exit code {process.returncode}"}
        except FileNotFoundError:
            logger.error(f"Task Master CLI command '{self.cli_command}' not found. Ensure it is installed and in PATH.")
            return {"success": False, "result": None, "error": f"Command '{self.cli_command}' not found."}
        except Exception as e:
            logger.error(f"An unexpected error occurred while executing command {' '.join(full_command)}: {e}")
            return {"success": False, "result": None, "error": str(e)}

    async def get_next_task(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        args = ["next"]
        if file_path:
            args.extend(["--file", file_path]) # Corrected from -f to --file for consistency
        return await self._execute_command(args)

    async def get_task(self, task_id: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        args = ["show", task_id]
        if file_path:
            args.extend(["--file", file_path])
        return await self._execute_command(args)

    async def get_tasks(self, status: Optional[str] = None, file_path: Optional[str] = None, with_subtasks: bool = False) -> Dict[str, Any]:
        args = ["list"]
        if status:
            args.extend(["--status", status])
        if file_path:
            args.extend(["--file", file_path])
        if with_subtasks:
            args.append("--with-subtasks")
        return await self._execute_command(args)

    async def set_task_status(self, task_id: str, status: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        args = ["set-status", "--id", task_id, "--status", status] # Corrected from -i, -s to --id, --status
        if file_path:
            args.extend(["--file", file_path])
        return await self._execute_command(args)

    async def update_task(self, task_id: str, prompt: str, research: bool = False, file_path: Optional[str] = None) -> Dict[str, Any]:
        args = ["update-task", "--id", task_id, "--prompt", prompt] # Corrected from -i, -p
        if research:
            args.append("--research")
        if file_path:
            args.extend(["--file", file_path])
        return await self._execute_command(args)

    async def update_subtask(self, subtask_id: str, prompt: str, research: bool = False, file_path: Optional[str] = None) -> Dict[str, Any]:
        args = ["update-subtask", "--id", subtask_id, "--prompt", prompt] # Corrected from -i, -p
        if research:
            args.append("--research")
        if file_path:
            args.extend(["--file", file_path])
        return await self._execute_command(args)
    
    async def add_task(self, prompt: str, dependencies: Optional[List[str]] = None, priority: str = "medium", research: bool = False, file_path: Optional[str] = None) -> Dict[str, Any]:
        args = ["add-task", "--prompt", prompt, "--priority", priority] # Corrected from -p
        if dependencies:
            args.extend(["--dependencies", ",".join(dependencies)])
        if research:
            args.append("--research")
        if file_path:
            args.extend(["--file", file_path])
        return await self._execute_command(args)

    # Add other Task Master CLI commands as methods here if needed
    # e.g., parse_prd, expand_task, etc.