# Gym-Anything
### A Framework for Reliable and Verifiable Software-Agent Training Environments

## 1. Project Overview

Gym-Anything is a framework designed to develop, execute, and evaluate software agents across multiple application environments.

The framework enables agents to understand user instructions, select appropriate environments, perform tasks, and independently verify execution results.

It aims to improve the reliability, accountability, and verifiability of software agents performing multi-step tasks.

## 2. Problem Statement

Software agents can perform tasks across applications, but ensuring that their actions are correct and that the intended outcomes have actually occurred remains challenging.

Gym-Anything addresses this problem through specialized agents, controlled execution environments, independent verification, and execution evidence.

## 3. Key Objectives

- Develop agents capable of executing tasks across multiple environments.
- Support environment creation and readiness auditing.
- Understand and interpret natural-language instructions.
- Execute tasks through specialized agents.
- Verify outcomes against actual application state.
- Maintain execution and verification evidence.
- Evaluate agent performance using measurable metrics.

## 4. System Architecture

The framework consists of the following components:

| Component | Responsibility |
|---|---|
| Creation Agent | Structures user instructions into executable tasks. |
| Audit Agent | Checks task and environment readiness. |
| Environment Selector | Selects the appropriate execution environment. |
| Execution Agent | Performs the requested task. |
| Verification Module | Independently checks execution results. |
| Evaluation Module | Measures agent performance. |

### Workflow

User Instruction → Creation Agent → Audit Agent → Environment Selector → Execution Agent → Independent Verifier → Evaluation and Evidence

## 5. Supported Environments

### 5.1 Task Manager

- Create tasks.
- Update task details and status.
- Delete tasks.
- Retrieve existing tasks.
- Store task information using SQLite.

### 5.2 Google Forms Environment

- Inspect and understand form questions.
- Retrieve relevant information from the logged-in user's profile.
- Match questions with saved profile information.
- Generate AI-assisted draft answers for open-ended questions.
- Allow users to approve, edit, or reject suggested answers.
- Fill supported form fields using Playwright.
- Verify filled answers independently.

Final form submission remains under user control.

### 5.3 Shopping Sandbox

- Search available synthetic products.
- Filter and sort products.
- Add products to the shopping cart.
- Remove products from the cart.
- View cart contents.

The shopping environment is simulated and does not perform real purchases or payments.

## 6. Multi-Agent Architecture

Gym-Anything uses specialized agents to divide responsibilities across the execution workflow.

- **Creation Agent:** Converts user instructions into structured tasks.
- **Audit Agent:** Checks whether the requested task and environment are ready.
- **Environment Selector:** Determines which environment should handle the task.
- **Execution Agent:** Carries out the task.
- **Independent Verifier:** Checks whether the expected result was achieved.
- **Evaluation Module:** Records performance-related metrics.

## 7. Technology Stack

- Python
- Flask
- SQLite
- Playwright
- Ollama / Llama 3
- HTML
- CSS
- JavaScript
- JSON

## 8. Project Structure

```text
Gym-Anything/
│
├── agents/
│   ├── agent_session.py
│   ├── creation_agent.py
│   ├── audit_agent.py
│   ├── environment_selector.py
│   ├── execution_agent.py
│   ├── google_forms_agent.py
│   └── shopping_execution_agent.py
│
├── app/
│   ├── application.py
│   ├── auth.py
│   ├── database.py
│   └── templates/
│
├── environments/
│   └── shopping_env/
│       ├── app.py
│       ├── products.json
│       └── templates/
│
├── evaluation/
├── tasks/
├── tests/
├── verification/
├── requirements.txt
├── .gitignore
└── README.md
```

## 9. Installation

### Step 1: Clone the repository

```bash
git clone https://github.com/AkshithaNB/Gym-Anything.git
cd Gym-Anything
```

### Step 2: Create a virtual environment

```bash
python -m venv .venv
```

### Step 3: Activate the environment (Windows)

```powershell
.venv\Scripts\Activate.ps1
```

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Install Playwright browsers

```bash
playwright install
```

## 10. Running the Application

### Main Gym-Anything Application

Start the main application from the project directory:

```powershell
python -c "from app.application import app; app.run(host='127.0.0.1', port=5055, debug=False, threaded=True)"
```

Open:

http://127.0.0.1:5055

### Shopping Sandbox

Open a separate terminal and run:

```powershell
python environments/shopping_env/app.py
```

Open:

http://127.0.0.1:5001

## 11. Verification and Evaluation

The Independent Verifier checks whether the expected task outcomes match the actual execution results.

The framework includes evaluation-related metrics such as:

- Task Success Rate
- Verification Agreement
- Execution Time
- Number of Execution Steps
- Environment Setup Success Rate

Execution and verification evidence is maintained in the project for inspection.

Actual performance metrics should be reported based on completed experimental runs.

## 12. Safety and Limitations

- Google Forms answers require user review before final submission.
- Shopping operations use synthetic product data.
- No real purchases or payments are performed.
- User-specific information should only be accessed for the authenticated user.
- Supported form field types and application interactions may vary.
- Agent execution can be affected by changes in external application interfaces.

## 13. Future Enhancements

- Support additional application environments.
- Improve handling of dropdowns, radio buttons, and checkboxes.
- Strengthen multi-user data isolation.
- Expand independent verification mechanisms.
- Introduce more comprehensive evaluation benchmarks.
- Improve agent reliability across complex multi-step workflows.

## 14. Repository

GitHub: https://github.com/AkshithaNB/Gym-Anything
