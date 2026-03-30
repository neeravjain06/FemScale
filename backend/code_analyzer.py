def analyze_code(code: str):
    insights = []
    code_lower = code.lower()

    def add(message, topic, link):
        insights.append({
            "message": message,
            "topic": topic,
            "link": link
        })

    if "for " in code_lower or "while " in code_lower:
        add(
            "Your code uses loops — performance depends on input size.",
            "loops",
            "https://www.w3schools.com/python/python_for_loops.asp"
        )

    if "def " in code_lower:
        add(
            "You defined a function — great for reusable code.",
            "functions",
            "https://www.w3schools.com/python/python_functions.asp"
        )

    if "print(" in code_lower:
        add(
            "Print statements display output in logs.",
            "print",
            "https://www.w3schools.com/python/ref_func_print.asp"
        )

    if "[" in code_lower:
        add(
            "Lists are dynamic arrays — very efficient for storage.",
            "lists",
            "https://www.w3schools.com/python/python_lists.asp"
        )

    if "import " in code_lower:
        add(
            "Imports bring external libraries into your code.",
            "modules",
            "https://www.w3schools.com/python/python_modules.asp"
        )

    if not insights:
        add(
            "Simple code detected — should execute very fast.",
            "basics",
            "https://www.w3schools.com/python/"
        )

    return insights