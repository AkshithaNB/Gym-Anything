
# Gym-Anything

### A Framework for Reliable and Verifiable Software-Agent Training Environments

## 1. Project Overview

Gym-Anything is a framework designed to develop, execute and evaluate software agents across multiple application environments.

It aims to improve the reliability and verifiability of agents performing multi-step tasks in different software applications.

## 2. Objectives

- Develop agents capable of performing tasks across multiple environments.
- Support environment creation and readiness auditing.
- Execute user instructions through specialized agents.
- Verify task outcomes against application state.
- Maintain execution and verification evidence.
- Evaluate agent performance using measurable metrics.

## 3. System Architecture

The framework includes:

- Creation Agent
- Audit Agent
- Execution Agent
- Environment Selector
- Verification Module
- Evaluation Module

## 4. Supported Environments

### Task Manager
Supports task creation, updating, deletion and retrieval.

### Google Forms
Supports form-question understanding, profile-based answer generation and form filling. Final submission can be reviewed manually.

### Shopping Sandbox
Supports product searching, filtering, sorting and cart operations using synthetic products.

## 5. Technology Stack

- Python
- Flask
- SQLite
- HTML, CSS and JavaScript
- Playwright
- JSON

## 6. Project Structure

```text
Gym-Anything/
├── agent_state/
├── agents/
├── app/
├── environments/
├── evaluation/
├── evidence/
├── tasks/
├── tests/
├── user_profile/
├── verification/
├── requirements.txt
└── README.md
```

## 7. Installation

Clone the repository:

```bash
git clone https://github.com/AkshithaNB/Gym-Anything.git
cd Gym-Anything
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install Playwright browsers if required:

```bash
playwright install
```

## 8. Running the Application

Start the main application:

```bash
python -m app.application
```

Open:

```text
http://127.0.0.1:5000
```

Start the Shopping environment in a separate terminal:

```bash
python environments/shopping_env/app.py
```

Open:

```text
http://127.0.0.1:5001
```

## 9. Evidence and Evaluation

The `evidence/` directory stores execution and verification logs.

The `evaluation/` directory stores evaluation-related files and results.

Evaluation metrics include:

- Task Success Rate
- Verification Agreement
- Execution Time
- Number of Execution Steps
- Environment Setup Success Rate

Actual experimental results should be reported based on completed test runs.

## 10. Reproducibility

1. Clone the repository.
2. Install the required dependencies.
3. Configure the required user profile and environment settings.
4. Start the main application and required environment servers.
5. Execute test instructions through the dashboard.
6. Inspect execution and verification logs.
7. Compare actual application state with expected outcomes.

## 11. Safety and Limitations

- Shopping operations use a synthetic product environment.
- Google Forms answers should be reviewed before final submission.
- Test data should be used during evaluation.
- Agent execution and verification may have environment-specific limitations.

## 12. Contributors

- Akshitha
- Team Member 2
- Team Member 3

## 13. Repository

https://github.com/AkshithaNB/Gym-Anything
