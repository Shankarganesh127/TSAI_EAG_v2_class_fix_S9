# Agent Execution Flowchart

This flowchart illustrates the step-by-step logic of the Cortex-R Agent, focusing on the decision-making process within the main loop.

```mermaid
flowchart TD
    Start([User Input]) --> InitSession{Session Exists?}
    InitSession -- No --> CreateSession[Create New Session]
    InitSession -- Yes --> LoadSession[Load Session Context]
    
    CreateSession --> StartLoop
    LoadSession --> StartLoop
    
    subgraph AgentLoop [Core Agent Loop]
        StartLoop(Start Step 1..Max) --> Perception[Perception Module]
        
        Perception -->|Analyze Input| SelectTools{Tools Selected?}
        SelectTools -- No --> Abort[Abort Step]
        SelectTools -- Yes --> Planning[Planning Module]
        
        Planning -->|Generate Python Plan| ValidPlan{Valid solve function?}
        ValidPlan -- No --> RetryPlan[Retry / Error]
        ValidPlan -- Yes --> Execution[Execution Module]
        
        Execution -->|Run Sandbox| ResultCheck{Check Result}
        
        ResultCheck -- "FINAL_ANSWER" --> Success([Return Final Answer])
        ResultCheck -- "FURTHER_PROCESSING_REQUIRED" --> UpdateInput[Update Input with Intermediate Result]
        ResultCheck -- "Error / Other" --> RetryStep[Retry / Continue Loop]
        
        UpdateInput --> NextStep{Max Steps Reached?}
        RetryStep --> NextStep
        
        NextStep -- No --> StartLoop
        NextStep -- Yes --> MaxSteps([Return 'Max steps reached'])
    end
    
    Success --> UserOutput([Display to User])
    MaxSteps --> UserOutput
    Abort --> UserOutput
```

## ASCII Flowchart (Text Version)

```text
[User Input]
     |
     v
<Session Exists?> --No--> [Create New Session]
     |                          |
    Yes                         |
     v                          v
[Load Session Context] --> [Start Loop (Step 1..Max)]
                                |
                                v
                        [Perception Module]
                                |
                                v
                        <Tools Selected?> --No--> [Abort Step]
                                |
                               Yes
                                |
                                v
                        [Planning Module]
                                |
                                v
                        <Valid solve() function?> --No--> [Retry/Error]
                                |
                               Yes
                                |
                                v
                        [Execution Module (Sandbox)]
                                |
                                v
                        <Check Result>
                        /       |       \
        "FINAL_ANSWER" /        |        \ "Error/Other"
                      /         | "FURTHER_PROCESSING_REQUIRED"
                     v          v          v
          [Return Final Answer] [Update Input] [Retry/Continue]
                     |          |          |
                     |          v          |
                     |    <Max Steps Reached?>
                     |      /        \
                     |     No        Yes
                     |      |          \
                     |      v           v
                     |  [Start Loop]  [Return 'Max steps reached']
                     |
                     v
             [Display to User]
```

## Process Description

1.  **Initialization**: The agent checks if a session exists. If not, it creates one to store memory and context.
2.  **Perception**: The agent analyzes the user's input to understand intent and selects the relevant tools (e.g., Web Search, Documents, Math).
3.  **Planning**: A Large Language Model (LLM) generates a Python function (`solve()`) to execute the next logical step.
4.  **Execution**: The generated code is executed in a secure sandbox. The code calls the selected tools.
5.  **Result Evaluation**:
    *   **FINAL_ANSWER**: If the tool provides a complete answer, the loop ends, and the result is shown to the user.
    *   **FURTHER_PROCESSING_REQUIRED**: If the tool returns raw data (e.g., a long document), the agent feeds this data back into the loop as "input" for the next step, allowing it to summarize or analyze it.
    *   **Looping**: The agent continues this cycle until it finds an answer or hits the maximum number of steps (configured in `profiles.yaml`).
