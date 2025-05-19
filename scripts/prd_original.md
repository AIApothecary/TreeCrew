The full PRD v3.0 based on the forked integration of the agent-zero repo, treating the orchestrator as a core extension.

Additionally, I’ll produce:

1. A feature-by-feature comparison spreadsheet showing which features agent-zero already provides and which are new enhancements from the v2.2 spec.


# Claude Code Orchestrator Web App – PRD v3.0

## Introduction and Overview

The Claude Code Orchestrator Web App (v3.0) is a comprehensive AI-driven development orchestrator built as a direct extension of the open-source **Agent Zero** AI framework. This product enables developers to break down high-level requirements into actionable tasks, leverage AI to execute and manage those tasks, and maintain full control through a rich web-based interface. By forking the Agent Zero repository and extending its codebase within a private branch, we integrate advanced task management features (from the prior v2.2 spec) into Agent Zero’s robust multi-agent architecture. The goal is to preserve and enhance all major v2.2 features – such as AI-guided task breakdown, context management, and scalable agent deployment – while maintaining seamless compatibility with Agent Zero’s existing capabilities.

**Key Objectives:**

* **Seamless Integration:** Claude Code Orchestrator is implemented *within* the Agent Zero codebase (not as a plugin), reusing Agent Zero’s core logic for agent reasoning, tools, and UI wherever possible. Custom features build atop this foundation, ensuring the orchestrator feels like a natural evolution of the framework.
* **AI-Driven Development Workflow:** Empower users to input high-level specifications (e.g. a PRD or user story) and have the system automatically generate, organize, and execute a structured task list. The orchestrator employs Claude (or other AI models via API) to parse requirements into tasks and subtasks, determine priorities, and manage execution with minimal manual overhead.
* **Human-in-the-Loop Control:** While automation is central, the human user remains in control. The web UI will allow users to review and adjust task breakdowns, refine context and prompts, provide feedback on intermediate results, and approve critical decisions. This ensures **precision-first** development, where AI suggestions are vetted for accuracy and relevance before execution.
* **Scalability and Performance:** The system will support parallel task processing via an **elastic agent container pool**, launching multiple agent instances (containers) to handle tasks concurrently. At least 5 agents will be pre-warmed and ready, reducing latency when new tasks or subtasks start. The architecture will scale these agents up or down based on load, optimizing resource use.
* **Rich Web Interface:** A feature-complete web application provides an intuitive dashboard for orchestrating AI agents. Key UI components include a **Task Board** for monitoring tasks/subtasks, a **References/Knowledge panel** for documentation and context, import/export workflows for tasks, and real-time **Agent Logs** (with AI “thoughts” and tool usage) for transparency. The interface builds on Agent Zero’s existing web UI foundation but extends it for multi-task management and enhanced user controls.

**Out of Scope:** This PRD does not cover model training or the development of new AI models. It assumes existing AI APIs (Anthropic Claude, OpenAI, etc.) are available via keys and focuses on orchestrating those. Low-level improvements to Agent Zero’s base reasoning (beyond prompt enhancements for precision) are also out of scope. The primary focus is integrating and extending features at the orchestration layer and UI.

## Background

Claude Code Orchestrator v2.2 introduced a powerful set of features aimed at streamlining AI-assisted software development. However, v2.2 was not built on Agent Zero and existed as a separate prototype. For v3.0, we are **migrating and integrating those features into Agent Zero’s framework**. Agent Zero provides a dynamic agentic platform with multi-agent cooperation, tool usage, and a web interface. By using Agent Zero as a base, we avoid reinventing core agent functionalities (like prompt management, tool execution, and memory) and instead focus on **enhancing** them with orchestrator-specific capabilities.

Agent Zero’s relevant existing features that we will leverage include:

* **Hierarchical Agents:** Agent Zero supports spawning subordinate agents to handle subtasks. This aligns with our task breakdown feature – we will utilize this mechanism (the `call_subordinate` tool) to implement AI-driven task delegation.
* **Tool System:** Agent Zero has a modular tool interface with default tools (knowledge base search, web content fetch, code execution, communication, etc.) and allows adding new custom tools. We will extend this by adding tools like **BrowserAutomation** (Playwright integration) and **DocumentationFetcher** (Context7 integration) as new capabilities the agent can invoke.
* **Prompt Customization and Memory:** The framework’s behavior is controlled by system prompts in the `prompts/` directory, and it maintains persistent memory of past interactions. We will update prompts to incorporate Task Master-style instructions (for task planning) and ensure that context (like imported docs or previous tasks) is stored/retrieved via the memory system.
* **Web UI Infrastructure:** Agent Zero’s web UI already streams agent outputs, supports chat sessions, and offers interactive controls (stop, intervene, etc.). We will reuse its frontend/backend structure, expanding it to handle multiple tasks and additional UI panels. The existing UI elements (like the chat panel, settings, and log streaming) will be augmented rather than replaced.

By standing on Agent Zero’s shoulders, the orchestrator can implement v2.2’s features more efficiently and reliably. The following sections detail each major feature and requirement of Claude Code Orchestrator v3.0, describing how it will be realized in the context of the Agent Zero codebase.

## Functional Requirements

### 1. AI-Driven Task Breakdown (Task Master Integration)

One of the centerpiece features is an AI-driven mechanism to break down high-level requirements into structured tasks and subtasks. Claude Code Orchestrator will embed **Claude Task Master** logic directly into Agent Zero, enabling automatic project planning within the agent’s workflow.

**Description:** The user can provide a high-level spec or Product Requirement Document (PRD) (via file upload or text input). The orchestrator will parse this document and generate a hierarchical task list (epics → tasks → subtasks) with descriptions, acceptance criteria, and priority. It uses Claude (or chosen LLM) under the hood to perform this breakdown, guided by Task Master’s algorithms:

* **PRD Parsing:** The system can automatically analyze a PRD and produce structured tasks based on its content. In practice, the orchestrator agent (Agent 0) will be primed with a Task Master system prompt instructing it how to identify requirements and break them into tasks. The PRD content is provided as input, and the agent’s output is a machine-readable task list (e.g. in JSON or Markdown format).
* **Task Structuring:** Each generated task will include details like title, description, estimated complexity, dependencies, and status. This creates a “shared language” between human and AI for what needs to be done. We will define a standardized **task schema** (possibly inspired by Task Master’s `tasks.json` format) to represent tasks in the system. The agent will follow this schema when outputting tasks.
* **Intelligent Sequencing:** The orchestrator should determine task dependencies and suggest an execution order. For example, if Task B depends on Task A, the system notes that relationship and will not execute B before A is done. The AI analysis of the PRD will include identifying prerequisite tasks and labeling each task with prerequisites (by ID). The UI will visualize these dependencies (e.g., parent/child tasks or arrows between tasks in the board).
* **Complexity Analysis & Subtasking:** The AI will also gauge task complexity and break down tasks that are too large. For any task the model flags as complex or vague, it can create subtasks, ensuring that each action item is granular and actionable. This prevents bottlenecks by continuously refining tasks until they are manageable.
* **Research-Backed Expansion (optional):** If enabled, the system can use external knowledge (via tools like Perplexity or web search) to enrich task breakdown. For example, if a task requires using a new technology, the agent can perform a quick research step to ensure subtasks include best practices. (This will utilize Agent Zero’s existing web search tool or custom integrations; it’s an extension of Task Master’s “research-backed subtask generation” but within our orchestrator context.)

**How Integrated:** We will create a **Task Planner module** (within the agent’s logic) that orchestrates this breakdown. Likely, this will be implemented as:

* A specialized **system prompt** (e.g., `prompts/default/taskmaster.system.md`) that instructs the agent how to output structured tasks from a PRD input.
* A **task planning routine** in the backend: possibly triggered when a user uploads a PRD or clicks “Generate Tasks”. This routine could call the main Agent Zero reasoning loop with the Task Master prompt and PRD text as input. The agent’s output (the structured tasks) will then be parsed into the internal task data structures.
* Reuse Agent Zero’s multi-agent feature: Agent Zero’s design allows an agent to call a subordinate to handle a subtask. We can leverage this by having the main agent delegate the task breakdown to a subordinate agent that is configured with the Task Master prompt. For example, Agent0 could issue a command `call_subordinate` with instruction “Parse this PRD and list tasks”, and the subordinate (Agent1) returns the tasks list. This keeps the main agent’s context clean for overseeing execution.
* The **output tasks** will be stored in a central Task Manager (likely maintained in memory and periodically saved to a file like `tasks.yaml` or database for persistence). Each task will have a unique ID, status (pending/ongoing/completed), and possibly an assigned agent instance.

**User Flow:** The user can initiate task breakdown in two ways:

1. **From Scratch:** On the UI, the user clicks “New Project” or “Import PRD”, pastes or uploads a requirements document. They then press “Generate Task List”. The system processes for a short time, then the Task Board populates with the resulting tasks and subtasks, organized hierarchically.
2. **Ad Hoc Query:** The user might also ask in natural language (via chat) something like “Break down the requirements for feature X into tasks.” The agent (with Task Master logic) will respond with structured tasks in the chat, which the system can optionally import into the Task Board.

**Acceptance Criteria:**

* Given a reasonably detailed PRD (1-2 pages of text), the system generates a task list that covers all major requirements from the document. Key details from the PRD should be reflected in task descriptions.
* Dependencies and ordering make sense (e.g., setup tasks come before implementation tasks, research tasks precede coding tasks if needed).
* Tasks are neither too broad nor too fine-grained: each task should be completable by an AI agent in a single session (or broken further if not).
* The user can edit the generated tasks through the UI (rename, reassign, change priority, or even add/remove tasks) to correct or refine the breakdown.
* The Task Master logic should run **within the orchestrator’s environment** – no requirement for external tools beyond the AI API. (If the design uses an external Task Master library or MCP server, it must be embedded or invoked behind the scenes without user needing to manage it.)

**Implementation Notes:** The Task breakdown prompt and logic draws heavily from Claude Task Master’s approach. We may reference the open-source Claude Task Master repository for prompt ideas or even incorporate parts of its logic (ensuring license compliance). The **MCP (Model Control Protocol)** integration mentioned in Task Master is not required for our web app; instead, we’ll directly call the AI API. We must ensure the agent’s output strictly follows a parseable format (JSON/YAML) so the application can consume it. If the agent’s first attempt is not perfectly structured, we might implement a post-processing step or iterative prompting (asking the agent to correct format). Also, we will integrate the **multi-model support** aspect by allowing the orchestrator to use different AI backends (Claude, OpenAI GPT-4, etc.) configured via API keys (leveraging Agent Zero’s existing model plug-in system). However, Claude will be the primary target model given its strength in task analysis.

### 2. Bulk Import of Tasks (Files/Folders in Markdown, YAML, JSON, TOML)

The orchestrator shall allow users to import existing task definitions in bulk, rather than relying only on AI generation. This accommodates teams that may already have a task list or prefer to initially outline tasks themselves. Supported formats include **Markdown**, **YAML**, **JSON**, and **TOML**, covering common structured text and data file types.

**Description:** Users can select a file (or an entire folder containing multiple files) that describes tasks or project plans. For example:

* A Markdown file with a checklist or bullet list of tasks.
* A YAML/JSON file structured as an array of task objects (with fields like title, description, etc.).
* A TOML file with tasks defined (possibly less common, but included for completeness).
* Even another PRD or design doc from which tasks can be parsed (though that overlaps with the AI-driven parsing feature).

Upon import, the system will parse these files and convert their contents into internal task objects, populating the Task Board. If a folder is imported, the system will traverse it and import all recognized files (e.g., a folder of `.md` files where each file is a user story with tasks).

**How Integrated:** We will implement an **Import Parser** component within the backend:

* For each supported format, use a parsing library or custom parser. (For Markdown, we might need to detect list items or headings as tasks; for YAML/JSON/TOML, we can directly parse into data structures since those are machine-readable.)
* Agent Zero’s codebase can accommodate this as a utility module, e.g., a new file `import_tasks.py` or within the `knowledge` import logic. (Agent Zero already has an “Import knowledge” feature in the UI – possibly for importing knowledge base documents. We might extend that to handle task files as well. If not directly reusable, we create a parallel import pipeline for tasks.)
* **User Interface:** In the UI’s sidebar or top menu, provide an “Import Tasks” button. Clicking it opens a file picker (allowing multi-select or folder selection). After the user selects files, the front-end sends them (or their content) to the backend.
* The backend then processes each file:

  * If Markdown: find lines that look like tasks. For example, lines starting with `- [ ]` or `- [x]` (if using checklist syntax) or ordered lists. Also, could interpret top-level headings as big tasks and sub-bullets as subtasks.
  * If YAML/JSON/TOML: attempt to parse. Expect a list of tasks or a dictionary of tasks. We will document the expected schema in user docs (e.g., JSON array of objects with keys: `id`, `title`, `desc`, `deps`, etc., or a YAML equivalent).
* The parsed tasks are then merged into the orchestrator’s Task Manager:

  * If the board is empty (new project), they simply populate it.
  * If there are existing tasks, the user should be prompted whether to append these tasks or replace the current set. (For safety, default to append and allow the user to manually remove duplicates or unwanted tasks.)
* The Task Board UI updates to show the imported tasks. Any hierarchy (task/subtask) present in the files should be reflected (for example, Markdown indents or YAML nesting).

**Conflict Handling:** If an imported task list has IDs or names that clash with existing tasks, the system will auto-resolve:

* It might ignore provided IDs and generate new unique IDs for each task.
* If a task with the same title exists, append a suffix or ask user how to handle (skip duplicate or import anyway).

**Acceptance Criteria:**

* The system successfully reads a Markdown file with a list of tasks and displays all tasks on the board with correct titles and structure.
* The system successfully reads YAML/JSON/TOML files following documented schema and imports tasks accordingly.
* Importing a folder containing multiple files results in all tasks from all files being aggregated.
* The import operation should be robust against minor format issues: e.g., if a Markdown file has some text not in list form, the parser should skip it without failing the whole import. Similarly, non-task content in files should be ignored.
* Performance: importing, say, a 100-task JSON file should be near-instant (<2 seconds to appear in UI) to ensure a smooth user experience.

**Implementation Notes:** The import feature does not directly use AI; it’s deterministic parsing. We will leverage existing Python libraries where possible:

* Markdown: could use a library like `markdown` to parse to HTML and then extract list items, or simpler regex for list lines.
* YAML/JSON/TOML: use `PyYAML` for YAML, `json` module for JSON, `toml` library for TOML.
* Keep this parsing code modular and well-tested, as it’s an important bridge between human planning and AI execution.

We must also integrate this with **Agent Zero’s logging and memory**. For instance, after import, we might want to log an entry (in agent logs) that “User imported X tasks from file Y”. Also, consider storing the original file path or name with each task for traceability (so user knows which file a task came from, if needed).

### 3. Human-in-the-Loop Context Optimization

While Agent Zero’s agents are autonomous, the orchestrator will introduce explicit features for **human-guided context optimization**. This means before or during an agent’s execution of a task, the system will allow the user to adjust what information (context) the agent sees and how the prompt is formulated – ensuring the AI has the most precise and relevant context.

**Description:** For each task or agent session, the orchestrator prepares a **Context Package**: a collection of relevant data to include in the prompt (such as code snippets, documentation, previous discussion, acceptance criteria, etc.). The user can review and tweak this package:

* When a task is about to start, the UI will show a **Context Preview**, listing what information will be given to the agent (for example: “Task description: ..., Related requirements: ..., Snippet from file X: ..., etc.”). The user can add or remove items from this context before execution.
* The user can also edit the task prompt phrasing. Perhaps the orchestrator auto-generates a prompt like “Implement the user login feature as described. Requirements: ... Constraints: ...”. The user could modify wording or add an emphasis (e.g. “Make sure to follow security best practices.”) before letting the agent proceed.
* During agent execution, if the user notices the agent is going off-track or missing some info, they can pause the agent and use a **“Nudge” or “Refine Context”** action. This might open a modal allowing the user to inject additional instructions or data into the agent’s context window, then resume.

**How Integrated:** Agent Zero already supports real-time user intervention (you can stop the agent mid-run and give it new instructions). We build on this by formalizing a UI and workflow for context management:

* **Context Panel:** In the web UI, alongside the chat/log, there will be a “Context” sidebar or modal. This displays all pieces of context currently prepared for the agent’s prompt. It might categorize them (e.g., “Task Description”, “Project Knowledge Base”, “Recent Code Changes”, “Imported Docs”, etc.).
* The user can toggle pieces on/off (include or exclude) via checkboxes or remove them. They can also manually paste in additional context (for instance, a code snippet or a link to an external reference).
* Under the hood, the **prompt assembly logic** (likely in Agent Zero’s `prepare.py` or similar) will check the user’s selections. Only the approved context items are concatenated into the prompt that is sent to the model. (Agent Zero normally automatically pulls from memory and knowledge files; we will route that through our UI controls.)
* **UI Flow for New Tasks:** When the user clicks “Run Task” on a task from the board, the system does not immediately unleash the agent. Instead, it transitions to a “Preparation” state:

  1. The context panel populates with initial suggestions (task details, relevant docs, etc. as determined by system).
  2. The user reviews and hits “Confirm & Run” to actually start the agent.
  3. Optionally, we can have a setting to auto-run without confirmation for trivial tasks, but default is to ask for review (this enforces human-in-loop on critical tasks).
* **Automated Context Suggestions:** The orchestrator should help the user by automatically finding relevant context. For example:

  * If a task involves a specific file or function (the task description might mention “Update `auth.py` function”), the system could fetch the content of that file or function and list it in the context panel (perhaps using Agent Zero’s knowledge tool or an internal index).
  * If the project has a knowledge base or documentation, and the task matches certain keywords (e.g., a task about “database schema”), the system can search the knowledge base for “database schema” and suggest those notes for inclusion.
  * We will likely index the project’s repository and recent codebase in Agent Zero’s memory (Agent Zero has a knowledge ingestion mechanism). The orchestrator can query this index for each task to pre-gather possibly useful info.
* **Context7 integration here:** The *Context7 documentation sync* (discussed next) will feed into this context system. If new library docs are fetched, they appear as context items for relevant tasks.

**Acceptance Criteria:**

* Before running a task, the user can see a list of context items and the exact prompt to be sent. They can modify it easily (e.g. remove a doc chunk that seems irrelevant or edit wording).
* The agent receives only the context that was approved. (We can verify by checking the logs that extraneous info was not included.)
* If the user intervenes mid-run with new context or instructions, the agent incorporates it. For instance, if the agent is coding and the user adds “Note: Use environment variables for secrets”, the agent acknowledges and adjusts its plan.
* The UI for this is intuitive and not cumbersome. The user should feel they have *control* without needing to micromanage every token. Defaults should be sensible so that in many cases the user just quickly scans and hits “Run”.
* There should be an easy way to accept all default context if the user trusts it (e.g., a single click if everything looks fine).

**Implementation Notes:** This feature primarily affects the **frontend UI** and the prompt assembly process:

* We will extend the front-end (likely built with Svelte/React or similar) to add the Context panel and editing capabilities. Also, a “pause and edit context” button during execution.
* On the backend, we might maintain a mapping of task → recommended context items. This could be prepared when tasks are created or when the user opens the task. Possibly a background job can pre-fetch context when a task moves to “ready” state.
* We must be careful about the token limit: the UI should indicate roughly how much context is going in (e.g., “\~1200 tokens of context selected”). If the user tries to include too much, we might warn or truncate lowest priority items.
* Agent Zero’s architecture uses a **system prompt + conversation history + knowledge**. We will intercept the knowledge insertion step: normally Agent Zero might auto-load all files from a knowledge folder. In our orchestrator, we will likely have a dynamic knowledge base per task. We might implement a custom tool or memory scope for “current task context” that replaces or augments the default memory.
* Also consider **privacy/security**: if the user has imported sensitive documents as context, those are staying local (the agent sends them to the model though, so same as any LLM usage). We should just note that user should not include anything they don’t want to send to the AI API.

### 4. Context7 Documentation Sync (Auto Documentation Retrieval)

To enhance the agent’s capabilities and context, the orchestrator integrates with **Context7**, an external documentation database service. This feature ensures that whenever the project introduces a new dependency (library, framework, API), the relevant official documentation is automatically fetched and made available to the agent.

**Description:** **Context7** is essentially a live knowledge base of libraries and frameworks. By connecting to it, our orchestrator can pull in up-to-date docs for things the agent might need to know, without the user manually searching for it. The system will monitor for events such as:

* A new package being installed (for example, the agent runs `pip install someLibrary` in a code execution, or the user adds a dependency to a config).
* The agent attempting to use an unfamiliar API or library (e.g., calling a function from a module that wasn’t previously seen).
* The user explicitly adding a new technology to the project.

When such an event is detected, the orchestrator triggers a **doc sync**:

* It queries the Context7 API (or an MCP server providing Context7 access) for documentation on that package or API. For instance, if `requests` library is installed, it fetches the usage docs or reference for `requests`.
* The retrieved documentation (likely excerpts or relevant sections rather than an entire manual) is stored in the orchestrator’s knowledge base. This could be in a dedicated “Documentation” memory folder or database. Agent Zero can have a `knowledge/` directory; we might place fetched docs as Markdown or text files there, tagged by library name.
* The system also surfaces this info in the UI. For example, the References panel might highlight “New docs available: requests (click to view)”. So the user and agent both have access.
* We incorporate the new docs into context for future tasks automatically when relevant. For instance, if a task involves using that library, the context suggestion (from feature #3) will include pertinent doc snippets.

**Integration and Trigger Mechanism:**

* Hook into the **code execution tool**: Agent Zero’s code execution tool can be observed. After it executes a command, we can parse the output or the command itself. If it’s a package installation (`pip install` or similar), we log that event.
* Hook into dependency files: If the project has a `requirements.txt` or `package.json` that gets updated (we might detect file changes via the agent’s actions), that can trigger a sync.
* Alternatively, implement a small **dependency scanner** that runs whenever a new session starts: it could look at the project’s dependency files and see if any library is “new” (not yet in our doc cache). However, real-time detection via agent actions is more direct.

Once triggered:

* Use Context7: “Connects to Context7.com’s documentation database to provide up-to-date library and framework documentation.” We will likely use an API. If an API key or account is needed, we’ll add configuration for it. (Potentially, if Context7 is public, maybe no auth needed for certain usage.)
* If Context7 is unavailable, as a fallback, we could use an open documentation source like DevDocs or official docs scraped from the web. (However, that is secondary; primary assumption is Context7 or similar MCP server is accessible.)
* The retrieved content might be quite large. We should ideally filter or chunk it to what's relevant. Context7 might allow querying specific endpoints (for example, “requests.get usage example”). If so, we tailor queries to the agent’s needs (maybe based on what function the agent tried to use).
* Save documentation in a structured way. Possibly one file per library, or a database with sections. Mark it with version if applicable (though initially, we can assume latest version docs).

**Example Use Case:** The user’s project uses a new library “FooLib” for the first time. The agent tries to call `FooLib.do_something()` and fails or is unsure of the parameters. The orchestrator sees mention of “FooLib” which is not in its knowledge. It queries Context7 and finds documentation for `FooLib`. It then provides the agent with the function signature and examples from the docs, enabling the agent to use it correctly. This happens automatically, and the agent can say in the log, “Imported documentation for FooLib for reference.”

**UI Integration:** In the **References/Knowledge panel**, newly synced docs appear. The user can click to read them (for their own understanding) and they can be marked as included in context or not. Perhaps an icon indicator shows which docs are currently considered in the agent’s knowledge.

We may also allow the user to manually trigger a docs search: e.g., a search bar in the References panel where they can query the Context7 database for any tech documentation on demand.

**Acceptance Criteria:**

* When a known package is installed or referenced, the orchestrator pulls in documentation without needing user action, within a short delay (e.g., within a minute of detection, docs are available).
* The agent is able to utilize this information. This can be tested by having the agent answer a question or solve a task that requires understanding that library’s usage, which it couldn’t have done prior to doc sync.
* Documentation is stored and organized accessibly. If the same package is triggered again, it doesn’t fetch duplicate info (cache it).
* The user can see that docs were fetched (some kind of notification or log entry like “Context7: Synced documentation for FooLib v1.2”).
* If Context7 has multiple results or requires choosing (like multiple versions of a library), the system picks the appropriate one (maybe latest stable, or ask the user if ambiguity).

**Implementation Notes:** This feature will require adding a **Context7 API client**. We might incorporate an MCP client since Context7 is mentioned in MCP context; possibly we run an MCP request like other tools (Agent Zero’s extensibility could allow adding an MCP tool). However, an easier route might be direct API calls if available. We need to consult Context7’s documentation for usage (perhaps REST or GraphQL).

* We must guard against pulling huge amounts of text. We should target specific endpoints (like function reference pages).
* Perhaps integrate with the agent’s search ability: i.e., the agent itself could be instructed: “If you get an error or need docs, use the documentation\_search tool.” Then the agent might trigger it. But to keep it automatic, doing it from the orchestrator backend is more straightforward.
* Ensure to sanitize and not run any code from the docs (only treat them as text).
* License: Many docs have licenses; since this is for personal assistance, it should be fine, but we store them locally for user’s use only.

### 5. Playwright Integration for Browser Automation

Claude Code Orchestrator will empower agents to not only fetch static webpages but also **interact with web pages** (click, fill forms, take screenshots) via Playwright. This gives the AI the ability to perform end-to-end tasks like end-user testing, web scraping behind logins, or web-based automation as part of a task.

**Description:** We introduce a new agent **tool** called (for example) `browser_automation_tool` or simply `playwright_tool`. When invoked by the agent, this tool will launch a headless browser (via the Playwright Python library) and execute instructions. The agent can script these instructions in its prompt. Some functionalities include:

* Navigating to a URL.
* Clicking an element, entering text into forms.
* Taking a screenshot of the page or a specific element.
* Extracting text or data from the page (DOM queries).
* Possibly handling multiple pages or waiting for network events.

**Integration into Agent Zero:** As Agent Zero allows custom tools, we will implement the Playwright tool as a custom extension in the `python/tools/` directory:

* The tool will likely accept a **script or command sequence** as input. For example, the agent might output something like: `TOOL: browser_automation_tool | ACTION: "goto" | URL: "https://example.com"` or a mini-script.
* We need to design a mini-API for the agent to use. Simpler is allowing natural language steps, but more reliable is a structured set of commands. Possibly, we define that the agent should output a JSON with an array of actions (like `[{action: "goto", url: "...", wait: 5000}, {action: "click", selector: "#btnLogin"}]` etc.). However, writing JSON by the agent might be error-prone.
* Alternatively, we allow a simple scripting language like:

  * `navigate("https://example.com");`
  * `fill("#username", "user123");`
  * `fill("#password", "pass123");`
  * `click("#loginButton");`
  * `textContent("div.welcome-message");` (to retrieve some text)
  * `screenshot("homepage.png");`

  The agent could output these lines in a fenced code block with a special tag (like \`\`\`browser or so). The tool will parse and execute them sequentially.
* We will use Python’s Playwright library to implement each action. The tool will run in the background (potentially as an asyncio task since Playwright is async) and return results to the agent:

  * For actions like `textContent` or any data extraction, the result (text or value) is captured and returned as the tool’s output (so the agent can use it).
  * For `screenshot`, it will save an image (we can save to a file and perhaps return the file path or embed a base64? In the web UI, we could even display the screenshot for the user).
  * For navigation or clicks that don’t produce immediate data, the tool can just confirm “Done” or return any important events.
* **Security considerations:** Because this can browse the web, ensure that any page interactions are done in a sandbox. The user should also be aware of the actions (we might log the URLs visited and elements clicked in the agent log for transparency). Also, set a reasonable timeout for pages and perhaps block certain domains if needed (to prevent the agent from going to malicious sites unknowingly).

**User & Agent Usage:**

* In a task, if the agent needs to do something on the web (like fill out a form or scrape data), it will decide to use this tool. We will document in the system prompt (tools section) how to use the browser tool. For example: *“Use `browser_automation_tool` for interacting with webpages. Provide a sequence of actions to perform.”*
* The user can also manually instruct the agent to perform a browser task via natural language, e.g., “Go to our deployed site and run an automated test clicking through the signup flow.” The agent will then translate that into Playwright actions.
* The Web UI might also have a feature to directly launch a browser automation task: possibly a form where the user enters a URL and some instructions to test, which then creates a task for the agent to execute via Playwright.

**Acceptance Criteria:**

* The agent can successfully navigate to a given URL and retrieve page content through the Playwright tool. For example, a task “Scrape the latest article titles from example.com” results in the agent using the tool to open the page and returning the titles.
* The agent can handle a simple form. For instance, given a test login page (provided credentials), it fills and submits, and confirms success (perhaps by reading the page after login).
* Screenshots: The agent can take a screenshot and the user can see it. Possibly, after task completion, the UI could show an image thumbnail in the log or provide a download link.
* Robustness: If the agent provides a malformed action or script, the tool should handle it gracefully (return an error message to agent like “Invalid browser action” rather than crash). The agent should then be able to adjust (with its self-correcting reasoning).
* The browser automation runs without hanging the whole system. We should set timeouts for page loads (e.g., 10 seconds) and ensure the agent doesn’t get stuck waiting indefinitely.

**Implementation Notes:** We will need to add **Playwright** to the project dependencies (and ensure the Docker environment or environment has Playwright browsers installed). Agent Zero’s `requirements.txt` will be updated accordingly.

* We may use Playwright’s headless mode by default, with an option to see a headed browser if debugging (headed not needed in server context though).
* The tool’s implementation might be complex, so we will thoroughly test with known scenarios.
* This feature corresponds somewhat to Agent Zero’s upcoming “MCP” or future features (Agent Zero v0.8.1 announcement referenced browser use in an update). If Agent Zero’s repository already has some form of browser integration (e.g., through a different tool or plans for one), we will either use it or ensure our implementation aligns with their patterns.
* Document to users how to enable this (some systems might require running `playwright install` to get browsers – we should handle that in our setup).

### 6. Elastic Agent Container Pool (Pre-warmed Agents & Scaling)

To handle multiple tasks and subtasks efficiently, the orchestrator will manage an **elastic pool of agent instances**. Instead of a single monolithic agent handling everything sequentially, we can run tasks in parallel or isolate them in separate contexts by assigning them to different agent containers. This improves throughput and avoids context confusion between unrelated tasks.

**Description:** The system will maintain at least **5 pre-warmed agent containers** (this number configurable) running and ready to accept tasks. “Pre-warmed” means the container has loaded the necessary environment: the Agent Zero runtime, models or API connections established, and possibly the initial prompt pre-loaded (but waiting idle). When a new task needs to run:

* The Orchestrator picks an idle agent from the pool and assigns the task to it. The task’s context (prompt, tools, memory specific to that task) is injected, and that agent executes independently.
* If all agents are busy and a new task comes in, the orchestrator can decide to spin up a new agent instance (scaling out) up to some limit, or queue the task until one is free. The scale-out threshold might be if >80% of agents busy, spawn 1-2 more, etc.
* When agents finish tasks, they can either terminate (and be replaced by a fresh pre-warmed one) or be reset to an idle state for reuse. Resetting might involve clearing their memory (to avoid leakage of old task info into new tasks) and reloading the base prompt.

**Implementation Approaches:**

* **Process-based Isolation:** Each agent container could correspond to a separate process (or thread, but process is safer for isolation given Python GIL and potential heavy operations). We can use Python’s multiprocessing, or run multiple instances of Agent Zero via some orchestrator component. Since Agent Zero is Dockerized, one idea is literally running multiple Docker container instances. However, spinning up a full container for each task might be heavy. Instead, within our Python app, we might instantiate multiple agent **threads** each with its own Agent state. Agent Zero’s architecture might not be inherently thread-safe, so separate processes are likely better.
* We might create an **AgentManager** class that starts N worker processes on launch (the "pre-warmed pool"). Each process might run a minimal loop to wait for a task assignment (via an IPC mechanism or queue).
* Communication with agents: Could be as simple as sending tasks through a queue and getting results back. Or we leverage Agent Zero’s existing communication (maybe run each agent as a local web server? Possibly overkill).
* Simpler: use Python’s `multiprocessing.Process` to start agent via CLI. For instance, Agent Zero has a CLI mode (run\_cli.py). We could initialize agents in CLI mode and pipe commands to them. But integrating that with our web UI might be complex.
* Instead, treat each agent like an object we call functions on, but in separate process. Possibly use `multiprocessing.Pipe` or a library like `ray` or `celery` for distributing tasks. Given scope, a custom lightweight manager likely suffices.
* Pre-warming means we start them at app startup. They will load the model (if using local model) or test API connectivity. That way, first task doesn’t pay the startup cost.
* Each agent should have an identifier (0 through 4 for initial, then 5,6… for new ones). Agent 0 in Agent Zero context is the root agent of a chain; here we might not strictly align these numbers with that concept, but we can label pool agents differently to avoid confusion (maybe “Worker1… Worker5”).

**Task Assignment Logic:**

* Default: The main orchestrator (Agent Zero in our fork) could act as a supervisor that doesn’t itself solve tasks, but delegates tasks to pool agents. This is analogous to having Agent0 only do orchestration and Agents1+ do actual work, but in our design each agent in pool might act like an Agent0 of its own isolated context for its task.
* When a task is launched from the Task Board, the Orchestrator picks a free agent process, sends it the task prompt and context. That agent then goes through the usual Agent Zero loop (system prompt + user prompt (task) → reasoning → tool calls → etc.) until task completion.
* The orchestrator monitors progress. It can stream the agent’s output back to the web UI (so the user sees live thoughts/logs of that particular agent). This implies we need to capture STDOUT or logs from that agent process and route them to the frontend, possibly tagging them by task/agent.
* After completion, the orchestrator collects the result (which might be code written, or answer given, etc.), marks the task as done, and either kills or resets the agent.

**Scaling:**

* We set a max agents perhaps (maybe 10 or 20 to avoid runaway resource usage) unless user configures more. If tasks exceed capacity, we queue them or politely inform user.
* If an agent process crashes or becomes unresponsive (perhaps due to a bug or long operation), we implement a timeout. If exceeded, we terminate that process and start a new one, and mark the task as failed (with option to retry).
* The pool size can be configurable in settings (via UI’s settings page under “Development” or similar).
* We will also allow scaling *down*: if agents have been idle for a long time (say 10 minutes), we might shut some down to free resources. This is not critical for initial version but good to consider.

**Acceptance Criteria:**

* The system can run multiple tasks in parallel. For example, the user starts Task A (agent1 takes it), then immediately starts Task B (agent2 takes it). Both run concurrently and their logs are separately viewable. They do not interfere with each other’s variables or memory.
* Task isolation: If Task A’s agent learned some context or had a certain chain of thought, none of that leaks to Task B’s agent (unless intentionally shared via orchestrator). This ensures precision and avoids confusion.
* Throughput: Starting a task is quick (if an agent is free, it should start near instantly). There’s no significant model re-loading delay on each task.
* If 5 tasks are running and a 6th is started, the orchestrator either successfully spawns a new agent to handle it or queues it. If spawned, the new agent doesn’t significantly slow down others (assuming the hardware can handle parallel load or the model calls are mostly API-based).
* Shutting down: The orchestrator can gracefully terminate all agent processes on app exit.

**Implementation Notes:** We must clearly delineate which parts of Agent Zero code run in each process. Possibly we will run `Agent()` class instances in subprocesses. Each process might need to initialize the model (which for API might just be storing the API key, for local might be loading weights into memory – careful if large model, parallel might be heavy).

* If using remote APIs (Claude, OpenAI), parallel calls are fine as long as we mind rate limits.
* Logging: likely we implement an **IPC logging mechanism**. The agent processes can send log lines to the main process. We might override Agent Zero’s default logging to instead emit through a pipe/socket to orchestrator, which then relays to UI. Another method: have each agent process run a lightweight HTTP server that streams events (similar to how `run_ui.py` does, but per agent). That might be too complex; a simpler queue of events might do.
* Reusing Agent Zero’s existing multi-agent logic vs our pool: Agent Zero’s built-in multi-agent is a *hierarchical chain* within one process. Our pool is more about parallel horizontal scaling. They can coexist: e.g., a pool agent could still spawn its own sub-agents for subtasks if needed, but that would happen inside its process. We should allow that (so an agent in pool might recursively use Agent Zero’s delegation if a task itself needs to be broken down further during execution).
* We need to adjust how “Agent0, Agent1” labels appear in logs. If each process considers itself Agent0 (with its subagents as 1,2,...), the logs from two tasks might both refer to “Agent 0: ...”. To avoid confusion on the UI, we may label logs with the task name or ID instead of just “Agent 0”. For example, prefix log lines with “\[Task #4] Agent 0: ...”. This way the user knows which task’s agent is speaking. The UI could filter logs per task.
* **Resource usage:** Document that running many agents in parallel will use more CPU/memory. For large models or local inference, parallel might be limited by hardware. In that case, the benefit is more for API usage or smaller models. Possibly allow configuration of concurrency.

### 7. Precision-First Prompt and Context Planning

Claude Code Orchestrator is designed with a **precision-first** philosophy: it emphasizes careful planning of prompts and context to guide the AI agents to produce accurate, relevant outputs. Instead of throwing a maximum amount of information at the model (which can dilute focus), the orchestrator selects the minimal *necessary* context and crafts prompts explicitly targeted to the task at hand.

**Description:** This is more of a guiding principle affecting multiple parts of the system:

* **Task-Focused System Prompts:** We will customize the system prompt for agents to prioritize correctness and to ask for clarification if unsure. For instance, the system prompt may instruct: *“If you are not certain about something or need more data, do not guess—either ask for clarification or use the appropriate tool to get more information.”* This ensures the agent doesn’t run off of faulty assumptions.
* **Prompt Templates per Task Type:** The orchestrator can use different prompt templates depending on the nature of the task. For example, a coding task prompt might start with a different template than a research task. By tailoring these, we ensure the AI is guided in the right direction (precision in understanding the goal).
* **Context Curation:** (As covered in feature #3) we include only relevant documentation in the prompt. The orchestrator might rank context items by relevance to the current task (perhaps by vector similarity or keyword matching) and only include top N items that fit in the model context window. This avoids overloading the model with irrelevant text.
* **Step-by-Step Planning:** The orchestrator encourages agents to break problems into steps internally. Agent Zero already has a notion of “Thoughts” and “Reflections” that the agent prints out as it reasons【7†output】. We will maintain or enhance this to have the agent explicitly plan before execution. For complex tasks, the agent might outline its approach (list of steps) as part of its answer, which the user can verify in real time due to streaming. If something looks off, the user can intervene early.
* **Validation and Verification:** After an agent completes a task, the orchestrator can perform a validation step. For example, if the task was to write code, the orchestrator could run tests or linting on the output; if the task was to answer a question, maybe quickly cross-check via a secondary query. This isn’t a full requirement for v3.0, but we design the system to accommodate adding such verifications easily (maybe a “verify\_task” hook that can be implemented per task type).
* **User Feedback Loop:** If the user marks a result as incorrect or suboptimal, the orchestrator will use that feedback to adjust prompts for similar future tasks. (A simple approach: keep track of corrections and incorporate them in a knowledge base that the agent references when similar context arises.)

**Integration:** Many of these are prompt/policy level adjustments rather than new UI components:

* We will update the default **Agent Zero system prompt** (prompts/default/agent.system.md or equivalent) to align with orchestrator usage. It should mention the orchestrator’s existence and instruct the agent about the new tools (like Playwright) and new expectations (like waiting for user context confirmation).
* Possibly create distinct system prompts for different types of agents in our system:

  * A **Planner Agent** prompt (used when doing Task Master breakdown) focusing on completeness of tasks.
  * An **Executor Agent** prompt (for coding/execution tasks) focusing on correctness and not exceeding context.
  * A **Research Agent** prompt (if we allocate one for web research tasks) focusing on factual accuracy.

  The orchestrator can choose which prompt to use when assigning a task to an agent from the pool, based on task category.
* Ensure that when assembling the final prompt (system + user + context), we follow a structured order that highlights the most critical info early (since models weight beginning of context somewhat more). For instance: system instructions, then a **brief** summary of the task in user prompt, then relevant context, then the direct request. We should avoid long meandering prompts.
* We might incorporate “7±2 rule” for context: try not to include more than \~7 distinct pieces of context to avoid overwhelming the model, unless absolutely needed.

**Acceptance Criteria:**

* Agents consistently produce outputs that are on-topic and correct given the info they have. We observe fewer instances of the agent hallucinating details that are not provided.
* When the agent is unsure or missing info, it explicitly uses tools or asks rather than guessing. For example, if asked to use a library function it doesn’t know, it will either invoke the documentation tool (Context7) or ask the user for guidance, instead of making up a function.
* The user sees that tasks get done with minimal iterations. A well-crafted prompt often leads the agent to solve it in one go, rather than requiring many back-and-forth corrections.
* Prompt and context planning does not slow down the workflow significantly. Any automated analysis (like context ranking) should be fast. The user still feels the system is responsive.

**Implementation Notes:** We will fine-tune the prompt templates through testing. We might borrow best practices from known prompting techniques:

* Use clear delimiters when inserting context (to avoid model confusion which part is instruction vs data).
* Possibly use few-shot examples in system prompt if that helps (though that eats into context; maybe not unless needed).
* Since this orchestrator might be used with models like Claude which have large context windows, we have room for detailed instructions. But precision-first means we won’t just fill it because we can; we will prioritize relevance.
* Document developers on how to adjust these prompts if they want to tweak the agent’s behavior (since it’s all in the forked code, making it transparent for future changes).

### 8. Feature-Complete Web UI (Task Board, References, Workflows, Logs)

The orchestrator’s Web UI will be an enhanced version of Agent Zero’s interface, providing comprehensive control and visibility into the AI’s operations. The design philosophy is to make the complex multi-agent system intuitive to use through visual organization and interactive elements.

**Major UI Components:**

* **Task Board:** A central dashboard listing all tasks and subtasks. This will resemble a project management board or list:

  * Each task is shown as a card with title, status (Not Started, In Progress, Completed, or Error), and possibly assignee (if multiple human users, but here assignee likely always an AI agent or can say “AI”).
  * If tasks have a hierarchical structure (tasks with subtasks), they can be shown nested (indentation) or collapsible under a parent.
  * The user can reorder tasks (drag-and-drop) if priorities change, mark tasks as blocked or on hold, and create new tasks manually via an “Add Task” button.
  * Task cards also provide controls: **Run** (if not started), **Pause/Stop** (if running), **View Log** (to inspect what happened), **Edit** (to modify description or context).
  * The Task Board updates in real time. For example, when an agent starts working on a task, that task card might highlight or show a spinner icon. When done, it might turn green or get a checkmark.
  * There could be filters or swimlanes (e.g., show tasks by status or by category) for better organization if many tasks.
* **Task Detail / Agent Log View:** When the user wants to dive into a specific task, they can select it to open a detailed view:

  * This shows the full **Agent conversation log** for that task – essentially what currently appears as the chat in Agent Zero UI, but scoped to that task’s agent. It will display the agent’s Thoughts, Reflections, tool uses, and outputs, streamed live as they occur (the same way Agent Zero’s terminal and web UI currently stream content).
  * The user can interact here as well: type messages to the agent (which could be used to give feedback or additional instructions mid-task). This is an important human-in-loop aspect: e.g., “Agent: I’m not sure how to proceed.” User can type: “Try approach X and see if that works.”
  * Also from this view, the user can access the Context panel (discussed in feature #3) to adjust context for this specific task before resuming/starting it.
  * If multiple tasks are running, the user can switch between their logs easily (maybe tabs or by clicking different tasks).
* **References/Knowledge Panel:** A sidebar (perhaps on the right side of the UI) that shows useful references:

  * **Documentation**: lists documents imported or fetched (like Context7 docs). They can be grouped (Project Docs, Library Docs, Requirements, etc.). The user can click to read them within the app (perhaps a modal or pane opens the doc text).
  * **Project Files**: possibly integrate with the file system to let user open a project file if needed for reference, or show diff of changes agents made.
  * **Memory/History**: any persistent notes or previous decisions could be shown.
  * Essentially, this panel complements the agent’s memory – it’s the information the agent has or can access, which the user might want to inspect too.
* **Import/Export Workflow UI:**

  * For **Importing tasks**: as mentioned, a file picker dialog or drag-and-drop area. We’ll allow dragging a file onto the Task Board to trigger import as well, which is a convenient UI gesture.
  * After import, maybe show a brief summary: “Imported 8 tasks from tasks.yaml” in a notification.
  * For **Exporting**: allow the user to export the current task list (and maybe their statuses) to a file (JSON or Markdown). This is useful for record-keeping or sharing progress. A button “Export Tasks” can produce a file download.
  * Possibly also export logs (e.g., “Download full log of this task”), leveraging Agent Zero’s HTML log saving. We can extend or reuse that: Agent Zero already saves each session to an HTML file; for orchestrator, maybe each task’s log can be saved similarly or combined.
* **Agent Pool/Status Monitor:** Since we have multiple agents, we might include an indicator of system status:

  * E.g., a small section showing “Agents: 2 active, 3 idle”. Could be just text or an icon, possibly in a status bar or settings.
  * If needed, allow user to force start more agents or shut them down for troubleshooting (mostly for advanced users).
  * Also possibly show resource usage (CPU/RAM) per agent if we can get that info, to help user understand load (not a must-have, but nice to have in dev mode).
* **General Controls and Preferences:**

  * Continue to have controls like in Agent Zero: Autoscroll toggle, Dark Mode toggle, Speech on/off (if supported), toggles to show/hide internal Thoughts/JSON (Agent Zero had these debug options). We will retain those, adjusting if needed for multi-agent (for instance, “Show JSON” might show structured data of each agent’s state).
  * Settings panel (like in Agent Zero’s UI) will be updated to include orchestrator settings (pool size, API keys for Context7 if needed, default model selection, etc.).

**UI Technology:** We will use the same stack as Agent Zero’s current web UI. (If it’s a single-page application served by Python, we’ll modify that; or if it’s templated, we’ll update accordingly.) We ensure the design is responsive (usable on various screen sizes) and accessible (clear indicators, readable text, etc.).

**Acceptance Criteria:**

* The Task Board clearly reflects the state of tasks at all times. Starting, updating, and completing tasks on the board happens in sync with actual agent activity.
* Users find it easy to track what the AI is doing for each task, thanks to separate logs and the ability to drill down into details without confusion.
* All features from v2.2 spec have a UI representation. For example, the Playwright results (like screenshots or extracted data) are visible to the user (perhaps in the log or as attachments in the log view).
* The UI performance remains smooth even with many tasks. If there are, say, 20 tasks (some running, some done), the interface should still be responsive. Live log streaming for one task should not freeze the whole app.
* No major UI bug when interacting concurrently (e.g., user could start one task, switch to editing another’s context, nothing breaks).
* Cross-browser compatibility: should work on modern browsers (Chrome, Firefox, Edge, Safari).

**Implementation Notes:** We will likely modify `run_ui.py` and the associated frontend files. If Agent Zero’s UI is React-based, we’ll alter or extend the components for tasks and logs. If it’s a custom framework, we adapt within that structure.

* We should utilize web sockets or similar push mechanism to update the frontend in real-time (Agent Zero likely already uses something like that for streaming agent output).
* For visuals, we might add icons (like a checklist or board icon for the Task Board, a book icon for References, etc., as cues).
* We need to thoroughly test UI with various scenarios (maybe create dummy tasks to simulate full board).
* Logging segmentation: ensure that when the user looks at one task’s log, they don’t accidentally see interleaved messages from another task. This might require tagging messages by task in the backend and filtering on frontend.
* *Internationalization/Localization:* not in scope now, but the UI should not hard-code text in too many places (use central config for easy changes).
* *Error handling:* e.g., if an agent fails or a tool error occurs, the UI should display that on the task card (maybe a red error icon) and allow the user to view the error details in the log.

---

## Architecture and Implementation Notes

**High-Level Architecture:** The Claude Code Orchestrator extends Agent Zero’s architecture by adding an orchestration layer on top of the core agent loop. Conceptually, we introduce a **Task Orchestrator component** that manages tasks, agents, and context, interfacing between the Web UI and the Agent Zero agents.

* **Agent Zero Core (Reused):** At the heart, each **agent instance** uses Agent Zero’s logic: taking input, consulting tools, and producing output via the LLM. We do not modify the fundamental agent reasoning loop, but we adjust its prompts and supply it with orchestrator-specific tools and memory.
* **Task Orchestrator (New):** This is a control module (running in the main process) responsible for:

  * Receiving user inputs (new tasks, user messages, file imports) from the web server.
  * Maintaining the **Task List** data structure and state of each task.
  * Assigning tasks to agents (from the pool) and tracking which agent is working on what.
  * Aggregating logs from agents and sending updates to UI.
  * Handling context assembly for tasks and providing that to agents.
  * Managing external integrations (Context7 API calls, etc.) and feeding results into agent memory.
* **Agent Pool (New):** A collection of agent worker processes. Each process runs an instance of Agent Zero (likely headless, i.e., no UI) waiting for tasks. The main orchestrator communicates via IPC (inter-process communication) to give tasks and retrieve results/logs.
* **Web Server & Frontend (Modified):** Agent Zero’s `run_ui.py` likely uses FastAPI or a similar server to serve the frontend and handle socket connections. We will extend the server endpoints/sockets:

  * New endpoints for task management (e.g., `/tasks` GET/POST for listing and creating tasks, `/tasks/import` for file import, etc.).
  * Extend the websocket or event stream to push task updates and log lines to the UI, possibly with a task identifier in each message.
  * Frontend code updates to add new panels and interactivity as described.

**Data Flow Example (End-to-End):**

1. **Task Creation:** User imports a PRD. The frontend calls `POST /tasks/import` with the file content. The server uses the Task Planner logic (Task Master integration) to parse/generate tasks. The Task Orchestrator saves these tasks in its list (maybe also in a persistent JSON on disk for recovery).
2. **Task Execution:** User clicks “Run” on Task 1. The request goes to `POST /tasks/1/start`. The Task Orchestrator finds an idle Agent process and dispatches Task 1 to it (sending over the task description and relevant context). It marks Task 1 as In Progress and notifies UI.

   * In the agent process, it initializes the agent’s memory with provided context (for instance, populate the /memory folder or inject directly into prompt), sets up the system prompt according to task type, then calls the Agent Zero loop to handle the task.
   * The agent’s output (thoughts, actions, etc.) are sent back to orchestrator in real time (via a socket or shared queue).
   * The orchestrator relays these to the UI, and they show up in the Task 1 log panel.
3. **Tool Use:** Suppose agent uses `browser_automation_tool`. The call goes to our custom tool implementation in that agent process. The tool executes Playwright actions and returns result, which becomes part of the agent’s next input.

   * If agent uses `documentation_fetch` tool (Context7), that might actually be implemented to call back to the main process (since maybe the main process holds the API key and can cache docs). If so, the agent process tool could RPC to orchestrator which then calls Context7 and returns data. This detail depends on ease of sharing Context7 client among agents.
4. **Completion:** The agent finishes the task (could be by reaching an answer or finishing code generation). The orchestrator marks the task as Completed, and possibly triggers any post-task steps (like run validation, or auto-start any dependent tasks if we implement that).

   * The agent process either resets (clears its state) ready for another task, or we terminate it if we plan to spawn fresh ones (but pre-warmed suggests we keep it alive).
   * A summary of result might be stored (like output artifacts, code files modified, etc.).
5. **Concurrent tasks:** Meanwhile, user could run Task 2, which flows similarly with another agent process. They operate independently, orchestrator juggles their outputs.

**Reusing vs Custom Implementation:**

* *Agent Zero’s multi-agent chain vs our pool:* We decided to implement parallel execution via separate processes, which is custom. We are not directly using Agent Zero’s internal subordinate mechanism for parallelism, because that is sequential in one process. However, the subordinate mechanism can still be used *within* a single task if needed. We ensure that doesn’t conflict (for example, if an agent process spawns subordinate agents internally, that’s fine; those subagents run within that same process and their output is handled by that process).
* *Memory and Knowledge:* Agent Zero has a memory directory and knowledge base. We might reuse this by partitioning per task. For instance, each agent process could use a separate subfolder of `/memory` named after the task or agent ID, so their memories don’t overlap. Similarly for `/knowledge` (for docs). Or simpler: since each is separate process, they can each mount the same memory directory but keyed by agent id, etc. We will implement a scheme for that (maybe pass an env variable to agent process telling it which memory subdir to use).
* *UI and Logging:* Reuse as much of Agent Zero’s existing UI code as possible. The base UI already can show chat logs, allow stopping, etc. We mostly add new views (task list, references) and possibly reuse the chat component for each task log. Logs saving to HTML (for offline) we’ll adapt: maybe store logs under `logs/task_<id>_session.html` similar to how Agent Zero does for each session.

**Extensibility:** The architecture should remain extensible for future enhancements:

* Adding new tools (like integration with other services) remains straightforward (just drop in new tool file).
* Potential to integrate alternative planning modules (for example, a different Task Master version or even a learning component that improves task breakdown over time).
* Multi-user support (if in future multiple people collaborate in UI) could be considered; our design currently assumes one user controlling the orchestrator, but tasks could be assigned to human too in theory.

**Risks and Mitigations:**

* **Complexity:** Combining multi-agent parallelism, new tools, and UI improvements is complex. To mitigate, we will develop incrementally and ensure each piece works on its own:

  * First, implement task breakdown and ensure we can get a static task list.
  * Then the pool mechanism with dummy tasks (like have agent just echo something) to verify multi-process comms.
  * Then integrate with actual agent tasks and gradually add context management, etc.
* **Performance issues** (particularly memory or CPU): If using local models, 5 parallel might be impossible on one machine. We expect initial usage with API models (Claude, etc.) so that’s fine. We will document that using local LLMs might need scaling down concurrency.
* **Reliability of AI outputs:** The system heavily relies on AI to correctly parse PRDs and follow instructions. We have user in loop to catch issues. Additionally, testing with various prompts and perhaps adding some deterministic parsing in critical parts (like tasks format) will be important.
* **UI overload:** We must keep the UI clean. To avoid overwhelming the user with information from multiple agents, we isolate contexts. Also will provide ways to collapse or hide completed tasks to reduce clutter.

With this architecture, a tech lead or developer can proceed to implement the components, confident about how they fit together in the extended Agent Zero framework.

---

## Feature Matrix (v2.2 Features vs Agent Zero vs v3.0 Implementation)

The following table enumerates each major feature from the v2.2 spec, indicating whether Agent Zero already has support for it, and what action we will take in v3.0 (reuse as-is, customize, or implement new):

| **Feature (v2.2)**                                                    | **Agent Zero Base Support**                                                                                                                                    | **v3.0 Action (Implement/Customize)**                                                                                                                                                                                                                                              |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AI-driven Task Breakdown** (Task Master logic)                      | **No (Not built-in)** – Agent Zero can delegate subtasks via sub-agents, but it has no automatic PRD-to-task parser.                                           | **Implement** – Integrate Claude Task Master functionality. Use Agent Zero’s multi-agent capabilities to perform task planning. New prompts and planning module added.                                                                                                             |
| **Bulk Import of Task files** (Markdown, YAML, JSON, TOML)            | **No (Partial)** – Agent Zero has “Import knowledge” for context, but not task import. No native task import workflow exists.                                  | **Implement** – Develop import parsers for each format. Add UI for file selection. Leverage Agent Zero’s knowledge import mechanism concept for tasks (new code).                                                                                                                  |
| **Human-in-the-loop Context Optimization**                            | **Partial** – Agent Zero allows user intervention and has a memory system, but no dedicated UI to tweak context before run.                                    | **Implement/Customize** – Create context preview/edit UI. Customize prompt assembly in Agent Zero to use selected context. Reuse Agent Zero’s interruption mechanism for mid-run adjustments.                                                                                      |
| **Context7 Documentation Sync** (auto doc for new deps)               | **No** – Agent Zero doesn’t auto-fetch external docs. It relies on user-provided knowledge or agent search.                                                    | **Implement** – Build new integration with Context7 API. Possibly use Agent Zero’s tool system (a new tool for documentation retrieval). Ensure fetched docs stored in knowledge base for agent use.                                                                               |
| **Playwright Browser Automation**                                     | **No** – Agent Zero has a web content fetcher (for static pages) but not full browser automation (as of current version).                                      | **Implement** – Add as new custom tool (`browser_automation_tool`). No base support, so we’ll write the Playwright integration from scratch.                                                                                                                                       |
| **Elastic Agent Container Pool** (multi-agent concurrency)            | **No** – Agent Zero runs as a single agent chain (though multi-agent is sequential within one process). No pool management exists.                             | **Implement** – Design and implement process pool for parallel agents. Not present in base, so create AgentManager, IPC, etc. Possibly customize run logic to coordinate multiple agents.                                                                                          |
| **Precision-first Prompt/Context Planning**                           | **Partial** – Agent Zero provides basic prompt templates and shows Thoughts, but doesn’t specifically optimize context (it can load all knowledge by default). | **Customize** – Refine system prompts and context inclusion strategy. Adjust Agent Zero’s prompt templates for precision. Possibly limit knowledge injection to relevant items (custom code).                                                                                      |
| **Feature-Complete Web UI** (task board, references, import UI, logs) | **Partial** – Agent Zero has a Web UI with chat sessions, settings, log streaming, but it lacks a task board or multi-task management interface.               | **Implement/Extend** – Build new UI components (task board, etc.) on top of Agent Zero’s UI. Reuse styling and socket connections of base UI. Extend backend routes for new features. Logs and settings will be adapted to multi-task context (customization of existing UI code). |
| **Task status tracking & management** (implied in v2.2)               | **No** – Agent Zero doesn’t track task statuses (only conversation state).                                                                                     | **Implement** – Internally represent tasks with states, update status as agents work. Show progress in UI.                                                                                                                                                                         |
| **Agent logs per task**                                               | **Yes (Base logging)** – Agent Zero already streams and saves logs for a session. But it doesn’t separate multiple sessions concurrently in one UI.            | **Customize** – Reuse logging mechanism, but tag logs by task. Possibly start a new log file per task. Modify UI to display logs per selected task instead of global chat.                                                                                                         |

*Notes:* “Partial” means some analogous capability exists but not to the extent needed. All new implementations will be done within the forked repo (no external plugins), modifying Agent Zero’s code where needed (notably in UI, tool additions, and introduction of the task orchestrator module).

---

