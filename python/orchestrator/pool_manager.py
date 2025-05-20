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
import os

from pydantic import SecretStr 
from dotenv import load_dotenv # Import load_dotenv

from .engine import TaskPackage, ResultPackage

# Langchain imports for AI model interaction
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage 
from langchain_core.exceptions import OutputParserException

# Load environment variables from .env file
load_dotenv() # Call load_dotenv at module level

# Configure logging
logger = logging.getLogger(__name__)

class AgentWorker:
    """
    Represents an AI agent worker that can execute tasks.
    
    This class encapsulates the state and capabilities of an individual
    AI agent worker in the pool.
    """
    
    def __init__(self, worker_id: str, worker_type: str, capabilities: List[str], agent_profile: Dict[str, Any]):
        self.worker_id = worker_id
        self.worker_type = worker_type
        self.capabilities = capabilities
        self.agent_profile = agent_profile
        self.busy = False
        self.current_task: Optional[str] = None
        self.last_active = time.time()
        self.results: Dict[str, ResultPackage] = {}
        
        self.ai_client: Any = None
        self.api_key_env_var: Optional[str] = self.agent_profile.get("api_key_env")
        
        logger.debug(f"Worker {self.worker_id} initialized with profile: {self.agent_profile.get('model_name', 'N/A')}")

    def _initialize_ai_client(self) -> bool:
        if self.ai_client:
            return True

        provider = self.agent_profile.get("model_provider")
        model_name_any = self.agent_profile.get("model_name")
        
        if not isinstance(model_name_any, str):
            logger.error(f"Model name is not a string or is missing in agent profile for worker {self.worker_id}. Profile value: {model_name_any}")
            return False
        model_name: str = model_name_any 

        api_key_str: Optional[str] = None
        # The environment variable name to look for the API key
        # This can be specified in the agent_profile via "api_key_env"
        # or defaults to provider-specific common names.
        effective_api_key_env_var_name: Optional[str] = self.api_key_env_var
        
        if provider == "anthropic":
            if not effective_api_key_env_var_name: 
                effective_api_key_env_var_name = "ANTHROPIC_API_KEY" # Default for Anthropic
            api_key_str = os.environ.get(effective_api_key_env_var_name)
            if not api_key_str:
                 logger.warning(
                    f"Anthropic API key string not found using env var '{effective_api_key_env_var_name}'. "
                    f"ChatAnthropic will attempt to find it via its default mechanisms if not passed explicitly."
                )
        # elif provider == "openai":
        #     if not effective_api_key_env_var_name:
        #         effective_api_key_env_var_name = "OPENAI_API_KEY"
        #     api_key_str = os.environ.get(effective_api_key_env_var_name)
        #     if not api_key_str:
        #         logger.warning(f"OpenAI API key string not found using env var '{effective_api_key_env_var_name}'.")
        # else:
        #     logger.warning(f"Provider '{provider}' specified, but no explicit API key env var name in profile and no default lookup configured here.")
        
        try:
            if provider == "anthropic":
                client_args: Dict[str, Any] = { # Explicitly type client_args
                    "model_name": model_name,
                    "max_tokens_to_sample": self.agent_profile.get('max_tokens_to_sample', self.agent_profile.get('max_tokens', 4096)),
                    "temperature": self.agent_profile.get('temperature', 0.7),
                    "timeout": None,
                    "stop": None
                }
                if api_key_str: 
                    client_args["api_key"] = SecretStr(api_key_str) # Use "api_key" alias
                
                self.ai_client = ChatAnthropic(**client_args)
                logger.info(f"Anthropic client initialized for worker {self.worker_id} with model {model_name}")

            # elif provider == "openai":
            #     from langchain_openai import ChatOpenAI
            #     client_args_openai: Dict[str, Any] = {"model_name": model_name, ...}
            #     if api_key_str:
            #         client_args_openai["api_key"] = SecretStr(api_key_str)
            #     self.ai_client = ChatOpenAI(**client_args_openai)
            #     logger.info(f"OpenAI client initialized for worker {self.worker_id} with model {model_name}")
            else:
                logger.error(f"Unsupported model provider: {provider} for worker {self.worker_id}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to initialize AI client for worker {self.worker_id}, provider {provider}: {e}")
            return False

    def can_handle(self, task_type: str) -> bool:
        return task_type in self.capabilities
    
    def assign_task(self, task_id: str) -> None:
        self.busy = True
        self.current_task = task_id
        self.last_active = time.time()
    
    def release(self) -> None:
        self.busy = False
        self.current_task = None
        self.last_active = time.time()
    
    def set_result(self, task_id: str, result: ResultPackage) -> None:
        self.results[task_id] = result
    
    def get_result(self, task_id: str) -> Optional[ResultPackage]:
        return self.results.get(task_id)
    
    def clear_result(self, task_id: str) -> None:
        if task_id in self.results:
            del self.results[task_id]

    async def execute_task_on_model(self, task: TaskPackage) -> None:
        logger.info(f"Worker {self.worker_id} (profile: {self.agent_profile.get('model_name')}) starting task {task.task_id}")
        start_time = time.time()
        
        if not self.ai_client:
            if not self._initialize_ai_client():
                error_msg = f"AI Client for worker {self.worker_id} could not be initialized."
                result_pkg = ResultPackage(
                    task_id=task.task_id,
                    status="failure",
                    result=None, 
                    error=error_msg,
                    execution_time=time.time() - start_time,
                    metadata={"worker_id": self.worker_id, "agent_profile_name": self.agent_profile.get('model_name', 'N/A')}
                )
                self.set_result(task.task_id, result_pkg)
                logger.error(f"Worker {self.worker_id} failed task {task.task_id}: {error_msg}")
                return

        messages: List[Union[SystemMessage, HumanMessage]] = [] 
        
        if task.context and isinstance(task.context, dict) and "system_prompt" in task.context:
            system_prompt_content = task.context.get("system_prompt") 
            if isinstance(system_prompt_content, str): 
                messages.append(SystemMessage(content=system_prompt_content))
        messages.append(HumanMessage(content=task.prompt))

        try:
            response = await self.ai_client.ainvoke(messages)
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            result_pkg = ResultPackage(
                task_id=task.task_id,
                status="success",
                result=response_content,
                error=None,
                execution_time=time.time() - start_time,
                metadata={
                    "worker_id": self.worker_id,
                    "agent_profile_name": self.agent_profile.get('model_name', 'N/A'),
                    "model_provider": self.agent_profile.get('model_provider')
                }
            )
            logger.info(f"Worker {self.worker_id} (profile: {self.agent_profile.get('model_name')}) completed task {task.task_id}")
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id} (profile: {self.agent_profile.get('model_name')}) API call failed for task {task.task_id}: {e}")
            result_pkg = ResultPackage(
                task_id=task.task_id,
                status="failure",
                result=None,
                error=str(e),
                execution_time=time.time() - start_time,
                metadata={
                    "worker_id": self.worker_id,
                    "agent_profile_name": self.agent_profile.get('model_name', 'N/A'),
                    "model_provider": self.agent_profile.get('model_provider')
                }
            )
        
        self.set_result(task.task_id, result_pkg)


class PoolManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config: Dict[str, Any] = config if config is not None else {}
        self.workers: Dict[str, AgentWorker] = {}
        
        self.defined_worker_types: Dict[str, List[str]] = {
            "code": ["code", "refactor", "implement"],
            "architect": ["design", "architecture"],
            "debug": ["debug", "fix", "test"],
            "general": ["general", "research", "analyze"]
        }
        
        self.agent_profiles: Dict[str, Any] = {}
        self.worker_type_to_profile_mapping: Dict[str, str] = {}
        self.worker_counts: Dict[str, int] = {}

        pool_config = self.config.get("worker_pool", {})
        self.agent_profiles = pool_config.get("agent_profiles", {})
        self.worker_type_to_profile_mapping = pool_config.get("worker_type_to_profile_mapping", {})
        self.worker_counts = pool_config.get("worker_counts", {})

        if not self.agent_profiles:
            logger.warning("No agent_profiles defined in worker_pool configuration. Workers may not function correctly.")
        if not self.worker_type_to_profile_mapping:
            logger.warning("No worker_type_to_profile_mapping defined. Cannot map worker types to profiles.")
        
        self._initialize_worker_pool()
        
        logger.info("Pool Manager initialized with %d workers", len(self.workers))
    
    def _initialize_worker_pool(self) -> None:
        for worker_type, capabilities in self.defined_worker_types.items():
            count = self.worker_counts.get(worker_type, 0)
            if count == 0:
                continue

            profile_name = self.worker_type_to_profile_mapping.get(worker_type)
            if not profile_name:
                logger.error(f"No agent profile mapped for worker type '{worker_type}'. Cannot create these workers.")
                continue
            
            agent_profile = self.agent_profiles.get(profile_name)
            if not agent_profile:
                logger.error(f"Agent profile '{profile_name}' (for worker type '{worker_type}') not found in agent_profiles. Cannot create these workers.")
                continue
            
            for i in range(count):
                worker_id = f"{worker_type}-{uuid.uuid4().hex[:8]}"
                try:
                    self.workers[worker_id] = AgentWorker(worker_id, worker_type, capabilities, agent_profile)
                    logger.debug(f"Created worker {worker_id} of type {worker_type} with profile '{profile_name}' (model: {agent_profile.get('model_name')})")
                except Exception as e:
                    logger.error(f"Failed to create worker {worker_id} of type {worker_type} with profile '{profile_name}': {e}")

    async def get_available_worker(self, task_type: str) -> Optional[str]:
        available_workers = [
            worker_id for worker_id, worker in self.workers.items()
            if worker.can_handle(task_type) and not worker.busy
        ]
        
        if not available_workers:
            logger.warning(f"No available workers for task type: {task_type}")
            return None
        
        available_workers.sort(
            key=lambda worker_id: self.workers[worker_id].last_active
        )
        
        return available_workers[0] if available_workers else None
    
    async def assign_task(self, worker_id: str, task: TaskPackage) -> str:
        worker = self.workers.get(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")
        
        if worker.busy:
            raise ValueError(f"Worker {worker_id} is busy")
        
        if not worker.can_handle(task.task_type):
            raise ValueError(
                f"Worker {worker_id} (type: {worker.worker_type}) cannot handle task type {task.task_type}. Capabilities: {worker.capabilities}"
            )
        
        worker.assign_task(task.task_id)
        asyncio.create_task(worker.execute_task_on_model(task))
        
        logger.info(f"Assigned task {task.task_id} to worker {worker_id} (profile: {worker.agent_profile.get('model_name')})")
        return worker_id
    
    async def release_worker(self, worker_id: str) -> None:
        worker = self.workers.get(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")
        
        worker.release()
        logger.info(f"Released worker {worker_id}")
    
    async def get_task_result(self, worker_id: str, task_id: str) -> Optional[ResultPackage]:
        worker = self.workers.get(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")
        
        result = worker.get_result(task_id)
        if result:
            worker.clear_result(task_id)
        
        return result
    
    async def get_worker_status(self, worker_id: str) -> Dict[str, Any]:
        worker = self.workers.get(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")
        
        return {
            "worker_id": worker.worker_id,
            "worker_type": worker.worker_type,
            "capabilities": worker.capabilities,
            "busy": worker.busy,
            "current_task": worker.current_task,
            "last_active": worker.last_active,
            "agent_profile_name": worker.agent_profile.get('model_name', 'N/A')
        }
    
    async def get_all_worker_statuses(self) -> Dict[str, Dict[str, Any]]:
        return {
            worker_id: await self.get_worker_status(worker_id)
            for worker_id in self.workers
        }