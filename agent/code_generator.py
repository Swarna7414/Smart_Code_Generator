import re
from groq import Groq


class CodeGenerator:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model

    def generate(self, task: str, test_cases: str = "") -> tuple[str, str]:
        prompt = self._build_prompt(task, test_cases)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content
        code = self._extract_code(raw)
        return code, raw

    def _build_prompt(self, task: str, test_cases: str) -> str:
        prompt = f"""You are an expert Python programmer. Your job is to write a complete, correct Python solution.

TASK:
{task}
"""
        if test_cases.strip():
            prompt += f"""
TEST CASES (will be appended to your code and executed):
{test_cases}

IMPORTANT: Define all functions/classes that the test cases reference.
The test cases will run immediately after your code, make sure they can call your functions directly.
"""
        prompt += """
RULES:
- Write complete, runnable Python code
- Include all necessary imports
- Handle edge cases properly
- If tests are provided, ensure they pass
- Print output so execution is observable

OUTPUT ONLY raw Python code. NO markdown fences, NO ```python, NO explanations."""
        return prompt

    def _extract_code(self, text: str) -> str:
        for pattern in [
            r"```python\s*\n(.*?)\n```",
            r"```\s*\n(.*?)\n```",
            r"```python(.*?)```",
            r"```(.*?)```",
        ]:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        return text.strip()
