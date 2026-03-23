class TaskClassifier:
    NON_PYTHON_LANGUAGES = [
        "java", "javascript", "typescript", "c++", "c#", "csharp", "rust",
        "go", "golang", "ruby", "php", "swift", "kotlin", "scala", "matlab",
        "haskell", "dart", "elixir", "clojure", "perl", "bash", "shell",
        "sql", "html", "css", "lua", "r language", "r programming",
    ]

    FRAMEWORKS = [
        "react", "vue", "angular", "node", "express", "spring", "django",
        "flask", "fastapi", "laravel", "rails", "asp.net", "tensorflow",
        "pytorch", "keras", "scikit-learn", "pandas", "numpy", "jquery",
        "bootstrap", "tailwind", "next.js", "nuxt", "svelte",
    ]

    ANALYZE_KEYWORDS = [
        "compare", "comparison", "versus", " vs ", "difference", "rate",
        "rating", "difficulty", "multiple language", "all language",
        "which is better", "pros and cons", "contrast",
    ]

    LANGUAGE_LABEL_MAP = {
        "c++": "C++",
        "c#": "C#",
        "csharp": "C#",
        "golang": "Go",
        "r language": "R",
        "r programming": "R",
    }

    def classify(self, task: str) -> dict:
        task_lower = task.lower()
        languages = []

        if "python" in task_lower:
            languages.append("Python")

        for lang in self.NON_PYTHON_LANGUAGES:
            if lang in task_lower:
                label = self.LANGUAGE_LABEL_MAP.get(lang, lang.title())
                if label not in languages:
                    languages.append(label)

        for fw in self.FRAMEWORKS:
            if fw in task_lower:
                label = fw.title() + " (framework)"
                if label not in languages:
                    languages.append(label)

        non_python = [l for l in languages if "Python" not in l and "framework" not in l]
        has_analyze_keyword = any(kw in task_lower for kw in self.ANALYZE_KEYWORDS)
        is_multi_language = len([l for l in languages if "framework" not in l]) > 1
        needs_analyze = bool(non_python) or has_analyze_keyword or is_multi_language

        return {
            "mode": "analyze" if needs_analyze else "execute",
            "languages": languages if languages else ["Python"],
            "needs_execution": not needs_analyze,
        }
