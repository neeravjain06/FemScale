def estimate_complexity(code: str):
    code_lower = code.lower()

    loop_count = code_lower.count("for ") + code_lower.count("while ")

    # 🔥 PRIORITY 1: Nested loops
    if "for " in code_lower and code_lower.count("for ") > 1:
        return "O(n²)", "Nested loops detected → quadratic complexity."

    # 🔥 PRIORITY 2: Multiple loops
    if loop_count >= 2:
        return "O(n²)", "Multiple loops detected → likely quadratic."

    # 🔥 PRIORITY 3: Single loop
    if loop_count == 1:
        return "O(n)", "Single loop → linear complexity."

    # 🔥 PRIORITY 4: Recursion (optional heuristic)
    if "def " in code_lower and "return" in code_lower:
        return "O(1)", "Function detected but no loops → constant time."

    # 🔥 DEFAULT
    return "O(1)", "No loops detected → constant time."