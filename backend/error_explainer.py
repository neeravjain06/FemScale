def explain_error(stderr: str):
    """
    FINAL VERSION — robust + demo-ready
    Always returns structured error info
    """

    if not stderr:
        return {
            "title": "Unknown Error",
            "explanation": "No error message was captured.",
            "fix": "Check your code or logs for issues.",
            "link": "https://www.w3schools.com/python/"
        }

    error_lower = stderr.lower()

    # 🔥 TYPE ERROR (your main case)
    if "typeerror" in error_lower or "unsupported operand" in error_lower:
        return {
            "title": "Type Error",
            "explanation": stderr.strip(),
            "fix": "You are using incompatible data types (e.g., int + string). Convert using int(), str(), or float().",
            "link": "https://www.w3schools.com/python/python_casting.asp"
        }

    # 🔹 NAME ERROR
    if "nameerror" in error_lower:
        return {
            "title": "Name Error",
            "explanation": stderr.strip(),
            "fix": "You are using a variable that has not been defined.",
            "link": "https://www.w3schools.com/python/python_variables.asp"
        }

    # 🔹 ZERO DIVISION
    if "zerodivisionerror" in error_lower:
        return {
            "title": "Division by Zero",
            "explanation": stderr.strip(),
            "fix": "Ensure the denominator is not zero before division.",
            "link": "https://www.w3schools.com/python/python_operators.asp"
        }

    # 🔹 SYNTAX ERROR
    if "syntaxerror" in error_lower:
        return {
            "title": "Syntax Error",
            "explanation": stderr.strip(),
            "fix": "Check for missing colons, brackets, or incorrect indentation.",
            "link": "https://www.w3schools.com/python/python_syntax.asp"
        }

    # 🔹 TIMEOUT
    if "timeout" in error_lower:
        return {
            "title": "Execution Timeout",
            "explanation": "Your code took too long to execute.",
            "fix": "Optimize loops or reduce computational complexity.",
            "link": "https://www.w3schools.com/python/"
        }

    # 🔥 FALLBACK (VERY IMPORTANT)
    return {
        "title": "Runtime Error",
        "explanation": stderr.strip(),
        "fix": "Check your code logic and inputs carefully.",
        "link": "https://www.w3schools.com/python/"
    }