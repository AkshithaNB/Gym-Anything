
import subprocess
import json


def understand_question(question, profile):
    prompt = f"""
You are a question-understanding component for a browser automation agent.

Identify which saved profile field best answers the form question.

Available profile fields:
{json.dumps(list(profile.keys()))}

Form question:
{question}

Rules:
1. Return a profile field only if it is genuinely relevant.
2. If no profile field is relevant, return "unknown".
3. Never invent personal information.
4. Never generate an answer.
5. Return ONLY valid JSON.

Required format:
{{"field": "email"}}

If unknown:
{{"field": "unknown"}}
"""

    try:
        
        result = subprocess.run(
            ["ollama", "run", "llama3:8b", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60
        )

        if result.returncode != 0:
            print("Ollama error:", result.stderr)
            return None

        output = result.stdout.strip()

        start = output.find("{")
        end = output.rfind("}") + 1

        if start == -1 or end <= start:
            return None

        response = json.loads(output[start:end])

        field = response.get("field")

        if field == "unknown":
            return None

        if field not in profile:
            return None

        return field

    except Exception as error:
        print("Question understanding error:", error)
        return None
if __name__ == "__main__":
    profile = {
        "full_name": "Akshitha",
        "college": "Jain University",
        "department": "AIML",
        "skills": ["Python", "Java"]
    }

    questions = [
        "What is your full name?",
        "Which institution are you studying at?",
        "Describe your previous internship experience."
    ]

    for question in questions:
        result = understand_question(question, profile)
        print(question, "->", result)