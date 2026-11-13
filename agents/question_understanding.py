
def understand_question(question):
    """
    Identify what information a form question is requesting.
    """

    question = question.lower().strip()

    question_types = {
        "full_name": ["full name", "your name"],
        "email": ["email", "email address"],
        "college": ["college", "university", "institution"],
        "department": ["department", "branch", "major"],
        "year_of_study": ["year of study", "current year", "which year"],
        "skills": ["skills", "programming languages", "technical skills"],
        "ai_interest": ["interest in ai", "why do you want to join"],
    }

    for field, keywords in question_types.items():
        if any(keyword in question for keyword in keywords):
            return field

    return None


if __name__ == "__main__":
    questions = [
        "What is your full name?",
        "Which college do you attend?",
        "Describe your technical skills.",
        "Describe your previous project experience."
    ]

    for question in questions:
        result = understand_question(question)

        print("Question:", question)
        print("Identified field:", result)
        print()
