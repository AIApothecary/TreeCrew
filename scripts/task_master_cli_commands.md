# Task Master CLI Commands Reference

This document contains the command reference for the Task Master CLI, as output by the `task-master` command.

 _____         _      __  __           _
 |_   _|_ _ ___| | __ |  \/  | __ _ ___| |_ ___ _ __
   | |/ _` / __| |/ / | |\/| |/ _` / __| __/ _ \ '__|
   | | (_| \__ \   <  | |  | | (_| \__ \ ||  __/ |
   |_|\__,_|___/_|\_\ |_|  |_|\__,_|___/\__\___|_|

by https://x.com/eyaltoledano
╭──────────────────────────────────────────╮
│                                          │
│   Version: unknown   Project: TreeCrew   │
│                                          │
╰──────────────────────────────────────────╯


╭─────────────────────╮
│                     │
│   Task Master CLI   │
│                     │
╰─────────────────────╯


╭─────────────────────────────────╮
│  Project Setup & Configuration  │
╰─────────────────────────────────╯
    init                        [--name=<name>] [--description=<desc>]          Initialize a new project with Task Master      
                                [-y]                                            structure
    models                                                                      View current AI model configuration and        
                                                                                available models
    models --setup                                                              Run interactive setup to configure AI models
    models --set-main           <model_id>                                      Set the primary model for task generation
    models --set-research       <model_id>                                      Set the model for research operations
    models --set-fallback       <model_id>                                      Set the fallback model (optional)


╭───────────────────╮
│  Task Generation  │
╰───────────────────╯
    parse-prd                   --input=<file.txt> [--num-tasks=10]             Generate tasks from a PRD document
    generate                                                                    Create individual task files from tasks.json


╭───────────────────╮
│  Task Management  │
╰───────────────────╯
    list                        [--status=<status>] [--with-subtasks]           List all tasks with their status
    set-status                  --id=<id> --status=<status>                     Update task status (done, pending, etc.)
    update                      --from=<id> --prompt="<context>"                Update multiple tasks based on new             
                                                                                requirements
    update-task                 --id=<id> --prompt="<context>"                  Update a single specific task with new         
                                                                                information
    update-subtask              --id=<parentId.subtaskId>                       Append additional information to a subtask
                                --prompt="<context>"
    add-task                    --prompt="<text>" [--dependencies=<ids>]        Add a new task using AI
                                [--priority=<priority>]
    remove-task                 --id=<id> [-y]                                  Permanently remove a task or subtask


╭──────────────────────╮
│  Subtask Management  │
╰──────────────────────╯
    add-subtask                 --parent=<id> --title="<title>"                 Add a new subtask to a parent task
                                [--description="<desc>"]
    add-subtask                 --parent=<id> --task-id=<id>                    Convert an existing task into a subtask
    remove-subtask              --id=<parentId.subtaskId> [--convert]           Remove a subtask (optionally convert to        
                                                                                standalone task)
    clear-subtasks              --id=<id>                                       Remove all subtasks from specified tasks
    clear-subtasks --all                                                        Remove subtasks from all tasks


╭─────────────────────────────╮
│  Task Analysis & Breakdown  │
╰─────────────────────────────╯
    analyze-complexity          [--research] [--threshold=5]                    Analyze tasks and generate expansion           
                                                                                recommendations
    complexity-report           [--file=<path>]                                 Display the complexity analysis report
    expand                      --id=<id> [--num=5] [--research]                Break down tasks into detailed subtasks
                                [--prompt="<context>"]
    expand --all                [--force] [--research]                          Expand all pending tasks with subtasks


╭─────────────────────────────╮
│  Task Navigation & Viewing  │
╰─────────────────────────────╯