import re
from groq import Groq


class ReflectionModule:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model

    def reflect_and_refine(
        self,
        task: str,
        code: str,
        execution_result: dict,
        error_info: dict,
    ) -> tuple[str, str]:
        stdout = execution_result.get("stdout", "").strip()
        stderr = execution_result.get("stderr", "").strip()

        prompt = f"""You are an expert Python programmer doing code review and debugging.

ORIGINAL TASK:
{task}

CURRENT CODE:
{code}

EXECUTION RESULTS:
- stdout: {stdout if stdout else "(empty)"}
- stderr: {stderr if stderr else "(empty)"}

ERROR DETAILS:
- Type: {error_info["type"]}
- Message: {error_info["message"]}
- Line: {error_info.get("line_number", "unknown")}

YOUR JOB:
1. Identify exactly what is wrong with the code
2. Write a complete, corrected Python solution

FORMAT:
ANALYSIS:
<2-4 sentences explaining the root cause and what needs to change>

FIXED CODE:
<complete corrected Python code, raw code only, no markdown fences>"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2048,
        )
        full_response = response.choices[0].message.content.strip()

        analysis, fixed_code = self._parse_response(full_response, code)
        return fixed_code, analysis

    def _parse_response(self, response: str, fallback_code: str) -> tuple[str, str]:
        analysis = ""
        fixed_code = ""

        if "ANALYSIS:" in response and "FIXED CODE:" in response:
            parts = response.split("FIXED CODE:", 1)
            analysis = parts[0].replace("ANALYSIS:", "").strip()
            fixed_code = parts[1].strip()
        else:
            analysis = response
            for pattern in [
                r"```python\s*\n(.*?)\n```",
                r"```\s*\n(.*?)\n```",
            ]:
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    fixed_code = match.group(1).strip()
                    break

        if not fixed_code:
            fixed_code = fallback_code

        fence_match = re.search(r"```(?:python)?\s*\n(.*?)\n```", fixed_code, re.DOTALL)
        if fence_match:
            fixed_code = fence_match.group(1).strip()

        return analysis, fixed_code
