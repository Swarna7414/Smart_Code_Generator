import re
import json
from groq import Groq


class MultiLanguageAgent:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model

    def generate(self, task: str) -> dict:
        prompt = f"""You are an expert polyglot programmer and technical writer.

TASK: {task}

Respond with a single valid JSON object using this exact structure:

{{
  "summary": "2-3 sentence overview of what this task covers and what languages/frameworks are involved",
  "implementations": [
    {{
      "language": "Language or Framework name",
      "code": "Complete, correct, runnable code",
      "explanation": "2-3 sentences about the approach and any language-specific notes",
      "difficulty": "Easy",
      "difficulty_score": 1,
      "frameworks": ["relevant library or framework names, empty array if none"]
    }}
  ],
  "comparison": "Detailed paragraph comparing all implementations — syntax, verbosity, type system, tooling, performance",
  "key_differences": [
    "Specific difference 1",
    "Specific difference 2",
    "Specific difference 3"
  ],
  "recommendation": "Which language/approach is best for this specific task and why"
}}

Rules:
- difficulty_score is an integer from 1 (easiest) to 5 (hardest)
- difficulty is one of: Easy, Medium, Hard
- Include every language mentioned in the task
- Include framework-based alternatives where relevant (e.g. NumPy for Python, Streams for Java)
- Write complete, working code — not pseudocode
- Output ONLY the JSON object. No text before or after it."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4096,
        )

        raw = response.choices[0].message.content.strip()
        return self._parse(raw)

    def _parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return {
            "summary": text[:600] if len(text) > 600 else text,
            "implementations": [],
            "comparison": "",
            "key_differences": [],
            "recommendation": "",
        }
