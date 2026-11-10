
import re


def parse_prompt(prompt, profile):
    """
    Combine saved profile details with details
    explicitly provided in the user's prompt.
    """

    details = profile.copy()

    patterns = {
        "full_name": r"(?:full name|name)\s*:\s*(.+)",
        "email": r"(?:email|email id)\s*:\s*(.+)",
        "college": r"(?:college|college name|university)\s*:\s*(.+)",
        "department": r"(?:department|branch)\s*:\s*(.+)",
        "year_of_study": r"(?:year|year of study)\s*:\s*(.+)",
        "skills": r"skills\s*:\s*(.+)",
        "ai_interest": r"(?:why interested in ai|ai interest)\s*:\s*(.+)"
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, prompt, re.IGNORECASE)

        if match:
            value = match.group(1).strip()

            if field == "skills":
                details[field] = [
                    item.strip()
                    for item in value.split(",")
                    if item.strip()
                ]
            else:
                details[field] = value

    return details
