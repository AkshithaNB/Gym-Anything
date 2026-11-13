import re

ENVIRONMENT_KEYWORDS = {
    "task_manager": [
        "task manager",
        "create task",
        "create a task",
        "add task",
        "add a task",
        "make a task",
        "new task",
        "task called",
        "task named",
        "update task",
        "complete task",
        "mark task",
        "task status",
        "manage tasks"
    ],
    "google_forms": [
        "google form",
        "google forms",
        "fill form",
        "fill the form",
        "complete form",
        "registration form",
        "form fields"
    ],
    "shopping": [
        "shopping",
        "shop for",
        "find products",
        "search products",
        "buy",
        "product",
        "products",
        "shoes",
        "sneakers",
        "cart",
        "add to cart",
        "filter products",
        "sort products"
    ]
}

STRONG_KEYWORDS = {
    "task_manager": [
        "task manager", "create task", "create a task",
        "add task", "add a task", "make a task",
        "task called", "task named", "update task",
        "complete task", "mark task"
    ],
    "google_forms": [
        "google form", "google forms",
        "fill form", "fill the form",
        "complete form", "registration form"
    ],
    "shopping": [
        "shopping", "shop for", "buy",
        "shoes", "sneakers", "add to cart",
        "filter products", "search products"
    ]
}


def classify_environment(prompt):

    text = prompt.lower().strip()
    scores = {}
    strong_matches = {}

    for environment, keywords in ENVIRONMENT_KEYWORDS.items():

        matches = []

        for keyword in keywords:

            pattern = r"\b" + re.escape(keyword) + r"\b"

            if re.search(pattern, text):
                matches.append(keyword)

        scores[environment] = len(matches)

        strong_matches[environment] = any(
            keyword in matches
            for keyword in STRONG_KEYWORDS[environment]
        )

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    best_environment, best_score = ranked[0]
    second_score = ranked[1][1]

    if best_score == 0:

        return {
            "environment": "ambiguous",
            "confidence": 0,
            "reason": "No environment could be identified."
        }

    if best_score == second_score:

        return {
            "environment": "ambiguous",
            "confidence": 0,
            "reason": "Multiple environments match the prompt."
        }

    if best_score < 2 and not strong_matches[best_environment]:

        return {
            "environment": "ambiguous",
            "confidence": 0.3,
            "reason": "The prompt needs clarification."
        }

    return {
        "environment": best_environment,
        "confidence": min(best_score / 3, 1.0),
        "reason": f"Detected {best_environment} from the prompt."
    }