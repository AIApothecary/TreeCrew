# Subtask 1.6: Orchestrator Architecture Design

This document outlines the architectural design for the Claude Code Orchestrator, an extension of the Agent Zero project.

## 1. Existing Agent Zero Architecture Analysis (Completed)

*   **Status:** Completed.
*   **Key Findings:**
    *   Agent Zero possesses a structured `Agent` class ([`TreeCrew/agent.py`](TreeCrew/agent.py:0)) and a `Tool` base class ([`TreeCrew/python/helpers/tool.py`](TreeCrew/python/helpers/tool.py:0)).
    *   Tools are Python files dynamically loaded from the [`TreeCrew/python/tools/`](TreeCrew/python/tools/) directory.
    *   Tool invocation is triggered by JSON output from the agent's Language Model (LLM), parsed by `Agent.process_tools()`.
    *   The `Agent.get_tool()` method handles the dynamic loading and instantiation of these tools.
    *   An `extensions` system ([`TreeCrew/python/extensions/`](TreeCrew/python/extensions/)) allows for hooking into various agent lifecycle events.
    *   Hierarchical agent structures are supported, notably via the [`call_subordinate.py`](TreeCrew/python/tools/call_subordinate.py:0) tool.

## 2. Core Orchestrator Components

The orchestrator will be composed of the following key components:

*   **Task Master Interface:**
    *   **Responsibility:** Abstract all interactions with the Task Master system (e.g., fetching tasks, updating statuses).
    *   **Implementation:** A new tool (e.g., `task_master_cli_tool.py` in `python/tools/`) callable by the Orchestrator Agent. This tool will use Python's `subprocess` module to execute `task-master` CLI commands.
*   **Orchestration Engine (Main Orchestrator Agent):**
    *   **Responsibility:** The central coordinating component. It fetches tasks (via `Task Master Interface`), determines task readiness based on dependencies, selects/configures worker agents, assigns tasks, manages context delivery, and processes incoming results.
    *   **Implementation:** Can be a specialized instance of the existing `Agent` class or a new, dedicated class. It will leverage `AgentContext` and potentially the `call_subordinate.py` tool for certain types of agent interactions, though primary worker management will be via the Agent Pool Manager.
*   **Agent Zero Worker Pool Manager:**
    *   **Responsibility:** Manages a pool of Agent Zero instances (workers) for parallel task execution. This includes pre-warming instances, dynamic scaling (up/down based on load), assigning tasks from a queue to idle workers, and monitoring worker health.
*   **Context Manager:**
    *   **Responsibility:** Gathers, prepares, and optimizes context for each task. It may also support human-in-the-loop review and adjustment of context before a task is dispatched to a worker agent.
    *   **Integration:** The Orchestration Engine will query the Context Manager to obtain the necessary context for a task, which is then included in the `TaskPackage` sent to the worker.
*   **Results Processor:**
    *   **Responsibility:** Consumes task results from worker agents (via the Results Queue), interprets them (e.g., extracts generated code, status, logs), and uses the `Task Master Interface` tool to update the corresponding task in the Task Master system.

## 3. Component Interactions, Data Flow, IPC, Error Handling, and Logging

### 3.1. Tool System Integration

*   The **Orchestration Engine** will primarily use the new `task_master_cli_tool.py` to interact with the Task Master system (e.g., `task_master_cli_tool:next_task`, `task_master_cli_tool:set_status --id=X --status=Y`).
*   **Agent Zero Worker Instances**, when executing tasks assigned by the Agent Pool Manager, will use their own existing tools (e.g., [`code_execution_tool.py`](TreeCrew/python/tools/code_execution_tool.py:0), the new `playwright_tool.py`) as defined by their internal logic and the task at hand. The orchestrator provides the task and context but does not directly control the worker's internal tool use for task execution.
*   New tools (like `task_master_cli_tool.py` and `playwright_tool.py`) will be placed in [`TreeCrew/python/tools/`](TreeCrew/python/tools/) and will adhere to the base `Tool` class structure, making them discoverable by any agent.

### 3.2. Agent Pool Manager & Worker Interactions

*   **Inter-Process Communication (IPC):**
    *   **Task Queue:** The Orchestration Engine places `TaskPackage` (JSON) messages onto this queue.
    *   **Results Queue:** Worker Agents (via the Agent Pool Manager or directly) place `ResultPackage` (JSON) messages onto this queue.
    *   **IPC Library Recommendation:** **Celery with Redis** is recommended for a balance of features (retries, monitoring via Flower) and ease of setup. RabbitMQ can be used if more complex routing or extreme robustness is required. For initial, single-machine development, Python's `multiprocessing.Queue` could be a temporary, simpler alternative, with a plan to migrate.
*   **Data Formats (JSON):**
    *   **TaskPackage:**
      ```json
      {
        "task_id": "unique_task_identifier_from_task_master",
        "task_title": "Brief title of the task",
        "task_description": "Detailed description of the task",
        "context_data": {
          "relevant_files": [{"path": "path/to/file.py", "content": "...", "is_read_only": true}],
          "documentation_snippets": ["doc snippet 1", "doc snippet 2"],
          "user_instructions": "Specific user guidance for this task",
          "previous_attempts_summary": "Summary of what was tried if this is a retry"
        },
        "worker_config_overrides": { // Optional
          "timeout_seconds": 3600
        },
        "submission_timestamp": "YYYY-MM-DDTHH:MM:SSZ"
      }
      ```
    *   **ResultPackage:**
      ```json
      {
        "task_id": "unique_task_identifier_from_task_master",
        "worker_id": "identifier_of_the_worker_agent",
        "status": "completed | failed | timeout | completed_with_clarification_needed",
        "output": {
          "files_modified": [{"path": "path/to/file.py", "diff": "...", "new_content": "..."}],
          "stdout": "...",
          "stderr": "...",
          "artifacts_generated": ["path/to/artifact1.zip"]
        },
        "error_details": { // If status indicates failure
          "error_message": "...",
          "error_type": "...",
          "traceback": "..."
        },
        "execution_time_seconds": 120.5,
        "completion_timestamp": "YYYY-MM-DDTHH:MM:SSZ"
      }
      ```
*   **Control/Health Signals:** The Agent Pool Manager may use lightweight mechanisms (OS signals, heartbeat messages) for worker health checks and control.

### 3.3. Role of `call_subordinate.py`
*   The [`call_subordinate.py`](TreeCrew/python/tools/call_subordinate.py:0) tool is suited for direct, synchronous, hierarchical agent calls.
*   It is **not the primary mechanism** for the Orchestrator Engine to manage asynchronous task execution by workers in the pool. The Agent Pool Manager and IPC queues handle this.
*   It might be used for initial prototyping before the full pool is ready, or if the Orchestrator needs to delegate a specific, synchronous sub-function to a non-pool helper agent.

### 3.4. Worker Isolation: Docker vs. Multiprocessing
*   **Python `multiprocessing`:**
    *   **Pros:** Simpler initial setup, lower overhead for I/O-bound tasks, uses built-in libraries.
    *   **Cons:** Weaker isolation (GIL, dependency conflicts, shared state risks), harder resource management.
*   **Docker Containers:**
    *   **Pros:** Strong isolation (filesystem, environment, dependencies), consistent environments via images, better resource control (CPU/memory limits), easier multi-machine scaling, enhanced security. Agent Zero's `AgentConfig` already has Docker settings.
    *   **Cons:** Higher startup overhead per worker, added complexity of Docker management.
*   **Recommendation:** **Docker is preferred** for robust worker isolation, leveraging existing `AgentConfig` Docker settings. `multiprocessing` can be a fallback for development or very trusted, simple worker tasks.

### 3.5. Error Handling, Recovery, and Logging Details
*   **General Strategy:** Leverage Agent Zero's existing logging framework ([`python.helpers.log`](TreeCrew/python/helpers/log.py:0)). Implement structured logging (JSON) for all components.
*   **Worker Agent Errors:**
    *   **Logged Info:** `timestamp`, `task_id`, `worker_id`, `error_type` (e.g., "ToolExecutionError", "PythonException"), `error_message`, `full_traceback`, `tool_name_invoked`, `tool_args_provided`, context snippet.
    *   **Action:** Worker reports detailed error via Results Queue. Results Processor updates Task Master. Orchestrator decides retry/escalation.
*   **Agent Pool Manager Errors:**
    *   **Logged Info:** `timestamp`, `pool_manager_id`, `error_type` (e.g., "WorkerSpawnError", "IPCError"), `error_message`, `traceback`, `target_worker_id`, `queue_name`.
    *   **Action:** Critical log, monitoring alert, potential restart.
*   **Orchestration Engine Errors:**
    *   **Logged Info:** `timestamp`, `orchestrator_id`, `error_type` (e.g., "TaskMasterError", "ContextError"), `error_message`, `traceback`, `current_task_id`.
    *   **Action:** Log, potential task halt, intervention.
*   **Task Timeouts:**
    *   **Logged Info:** `timestamp`, `task_id`, `worker_id`, "TaskTimeout", `timeout_duration`, `last_activity`.
    *   **Action:** Pool Manager terminates/resets worker. Results Processor updates Task Master.
*   **IPC/Message Queue Errors:**
    *   **Logged Info:** `timestamp`, `component_source`, `queue_name`, `error_type` (e.g., "QueuePublishError"), `error_message`, `message_id`, `retry_count`.
    *   **Action:** Retry with backoff. Persistent errors: critical log, alert. Consider Dead Letter Queues (DLQs).
*   **Idempotency:** Design worker task execution to be idempotent where feasible.

### 3.6. Diagram of Orchestrator System
```mermaid
graph TD
    User_Input[User Input/PRD] --> TM_CLI{Task Master CLI}
    
    subgraph OrchestratorSystem[Orchestrator System]
        direction LR
        Orchestrator_Agent[Orchestration Engine / Main Agent]
        Task_Master_Tool[task_master_cli_tool.py]
        Context_Manager[Context Manager]
        Orchestrator_Config[Orchestrator Config <br> (e.g., orchestrator_config.yaml)]
        
        subgraph AgentPool[Agent Pool Subsystem]
           direction TB
           Agent_Pool_Manager[Agent Pool Manager]
           Task_Queue[(Task Queue <br> IPC: Celery/Redis <br> Data: JSON TaskPackage)]
           Results_Queue[(Results Queue <br> IPC: Celery/Redis <br> Data: JSON ResultPackage)]
           Worker_Instances[Agent Zero Worker Instances <br> (Pool - Docker Isolated)]
        end

        Results_Processor[Results Processor]

        Orchestrator_Agent -- Uses --> Task_Master_Tool
        Task_Master_Tool -- Interacts --> TM_CLI
        
        Orchestrator_Agent -- Gets Context --> Context_Manager
        Context_Manager -- Provides Context --> Orchestrator_Agent
        
        Orchestrator_Agent -- Publishes TaskPackage --> Task_Queue
        Agent_Pool_Manager -- Consumes & Dispatches --> Task_Queue
        
        Agent_Pool_Manager -- Manages & Assigns TaskPackage --> Worker_Instances
        
        Worker_Instances -- Publishes ResultPackage --> Results_Queue
        Results_Processor -- Consumes --> Results_Queue
        Results_Processor -- Updates Task --> Task_Master_Tool
        
        Orchestrator_Agent -- Reads --> Orchestrator_Config
        Agent_Pool_Manager -- Reads --> Orchestrator_Config
    end

    subgraph AZ_Worker[Agent Zero Worker Instance (Docker Container)]
        direction LR
        AZ_Worker_Core[Core Agent Logic]
        AZ_Tools[python/tools/*]
        AZ_Worker_Core -- Uses --> AZ_Tools
    end
    Worker_Instances --> AZ_Worker
```

## 4. Define Integration Points with Agent Zero
*   **Orchestrator as a Specialized Agent:** The Orchestration Engine will likely be a specialized `Agent` instance.
*   **Tool System:** New tools (e.g., `task_master_cli_tool.py`, `playwright_tool.py`) will reside in [`TreeCrew/python/tools/`](TreeCrew/python/tools/) and follow the base `Tool` class structure.
*   **Configuration:** Orchestrator-specific settings will be managed via a new configuration mechanism (see section 5.5), while individual worker agents will use/extend the existing `AgentConfig` from [`TreeCrew/agent.py`](TreeCrew/agent.py:0).

## 5. Non-Functional Requirements

*   **Scalability:** Addressed via Docker-isolated workers, message queue-based IPC, and dynamic scaling logic in the Agent Pool Manager.
*   **Performance:** Choice of IPC and pre-warmed agents are key.
*   **Maintainability:** Modular design with clear interfaces.
*   **Reliability:** Comprehensive error handling, retry mechanisms, and robust logging.
*   **Configuration Management for Orchestrator Components:**
    *   A dedicated configuration mechanism (e.g., `orchestrator_config.yaml` loaded at startup, or environment variables prefixed `ORCH_`) will manage settings for the Orchestration Engine, Agent Pool Manager, Context Manager, and Results Processor.
    *   **Key Settings:**
        *   IPC (Message Queue) connection details (host, port, credentials, queue names).
        *   Agent Pool: Min/max workers, default worker Docker image, resource limits per worker, health check parameters, task timeouts.
        *   Paths: Task Master CLI path, main log directory.
        *   Default LLM models for the Orchestrator Agent itself (if it uses one for complex decision-making).
    *   Individual Agent Zero worker instances will continue to be configured using the existing `AgentConfig` structure, potentially templated or customized by the Agent Pool Manager at spawn time.
    *   Sensitive data (API keys for external services, message broker credentials) should be sourced from environment variables or a secure secrets store, consistent with Agent Zero's current use of `.env` files.

## 6. Document the Architecture (This Document)
*   This document serves as the primary output for Subtask 1.6.

This concludes the architectural design for Subtask 1.6.