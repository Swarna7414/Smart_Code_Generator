import re


def parse_error(execution_result: dict) -> dict:
    stderr = execution_result.get("stderr", "")
    stdout = execution_result.get("stdout", "")

    if execution_result.get("timed_out"):
        return {
            "type": "TimeoutError",
            "message": "Execution exceeded the time limit.",
            "line_number": None,
            "traceback": stderr,
        }

    combined = stdout + "\n" + stderr

    error_type = "UnknownError"
    error_message = "An unknown error occurred."
    line_number = None

    type_match = re.search(r"(\w+(?:Error|Exception|Warning)):\s*(.*?)(?:\n|$)", combined)
    if type_match:
        error_type = type_match.group(1)
        error_message = type_match.group(2).strip()

    line_match = re.search(r'File ".*?", line (\d+)', combined)
    if line_match:
        line_number = int(line_match.group(1))

    if "AssertionError" in combined:
        error_type = "AssertionError"
        assert_msg = re.search(r"AssertionError:\s*(.*?)(?:\n|$)", combined)
        error_message = assert_msg.group(1).strip() if assert_msg else "Assertion failed."

    return {
        "type": error_type,
        "message": error_message,
        "line_number": line_number,
        "traceback": stderr.strip() or stdout.strip(),
    }
