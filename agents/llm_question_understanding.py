
import subprocess
import json


def understand_question(question, profile):
    """
    Identify the saved profile field relevant to a form question.
    This function does not generate answers.
    """

    prompt = f"""
You are a question-understanding component.

Identify which saved profile field best answers the form question.

Available profile fields:
{json.dumps(list(profile.keys()))}

Form question:
{question}

Rules:
1. Return a field only if genuinely relevant.
2. If no field is relevant, return unknown.
3. Never invent personal information.
4. Return only valid JSON.

Required format:
{{"field": "department"}}

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

        if field == "unknown" or field not in profile:
            return None

        return field

    except Exception as error:
        print("Question understanding error:", error)
        return None


def generate_answer(question, profile):
    """
    Generate a personalised draft using saved profile information.
    The generated answer must be reviewed by the user.
    """

    relevant_profile = {
        key: value
        for key, value in profile.items()
        if value not in (None, "", [], {})
        and key not in ("id", "password_hash", "created_at")
    }

    prompt = f"""
You are an answer-generation component for a Google Forms assistant.

Form question:
{question}

User's saved profile:
{json.dumps(relevant_profile, ensure_ascii=False)}

Instructions:
1. Generate a natural, meaningful answer to the form question.
2. Use only information supported by the saved profile.
3. You may write in first person when appropriate.
4. Never invent achievements, experience, qualifications,
   motivations, or personal history.
5. Do not return a list of profile keywords.
6. Do not include explanations about how you generated the answer.
7. If the profile does not provide enough information to answer
   reliably, return exactly: NEEDS_USER_INPUT.
8. Keep the answer concise and relevant to the question.

Return only the answer.
"""

    try:
        result = subprocess.run(
            ["ollama", "run", "llama3:8b", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90
        )

        if result.returncode != 0:
            print("Ollama generation error:", result.stderr)
            return None

        answer = result.stdout.strip()

        if not answer or "NEEDS_USER_INPUT" in answer:
            return None

        return answer

    except Exception as error:
        print("Answer generation error:", error)
        return None
