import time
from datetime import datetime
from typing import Iterator

from .code_generator import CodeGenerator
from .code_executor import CodeExecutor
from .error_parser import parse_error
from .reflection import ReflectionModule
from .task_classifier import TaskClassifier
from .multi_language_agent import MultiLanguageAgent


class AgentLoopController:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.generator = CodeGenerator(api_key, model)
        self.executor = CodeExecutor()
        self.reflector = ReflectionModule(api_key, model)
        self.classifier = TaskClassifier()
        self.multi_agent = MultiLanguageAgent(api_key, model)

    def run(
        self,
        task: str,
        test_cases: str,
        max_iterations: int = 5,
        timeout: int = 10,
    ) -> Iterator[dict]:
        start_time = time.time()

        yield self._evt("start", f"Agent started - max {max_iterations} iterations, {timeout}s timeout")

        yield self._evt("classifying", "Detecting task type and target languages...")
        classification = self.classifier.classify(task)
        mode = classification["mode"]
        languages = classification.get("languages", ["Python"])

        yield self._evt(
            "classified",
            f"Mode: {mode.upper()} | Languages: {', '.join(languages)}",
            mode=mode,
            languages=languages,
        )

        if mode == "analyze":
            yield from self._run_analyze(task)
        else:
            yield from self._run_execute(task, test_cases, max_iterations, timeout, start_time)

    def _run_analyze(self, task: str) -> Iterator[dict]:
        yield self._evt("analyzing", "Generating multi-language analysis with LLM")
        try:
            result = self.multi_agent.generate(task)
            langs = [impl["language"] for impl in result.get("implementations", [])]
            label = ", ".join(langs) if langs else "response ready"

            yield self._evt("analysis_ready", f"Analysis complete: {label}", analysis=result)
            yield self._evt(
                "complete",
                "Analysis finished.",
                success=True,
                mode="analyze",
                final_code="",
                total_time=0,
                iterations_count=0,
                iterations=[],
                analysis=result,
            )
        except Exception as exc:
            yield self._evt("failed", f"Analysis failed: {exc}", error=str(exc))

    def _run_execute(
        self, task: str, test_cases: str, max_iterations: int, timeout: int, start_time: float
    ) -> Iterator[dict]:
        all_iterations: list[dict] = []

        yield self._evt("generating", "Generating initial code with LLM")
        try:
            code, _ = self.generator.generate(task, test_cases)
        except Exception as exc:
            yield self._evt("failed", f"LLM call failed: {exc}", error=str(exc))
            return

        yield self._evt("code_ready", f"Initial code ready ({self._line_count(code)} lines)", code=code, iteration=0)

        for iteration in range(1, max_iterations + 1):
            yield self._evt(
                "executing",
                f"Executing code - iteration {iteration}/{max_iterations}",
                code=code,
                iteration=iteration,
            )

            exec_result = self.executor.execute(code, test_cases, timeout)
            iter_data: dict = {
                "iteration": iteration,
                "code": code,
                "execution": exec_result,
                "timestamp": self._ts(),
            }

            if exec_result["success"]:
                iter_data["status"] = "success"
                all_iterations.append(iter_data)

                yield self._evt(
                    "success",
                    f"Code passed on iteration {iteration}",
                    code=code,
                    iteration=iteration,
                    execution=exec_result,
                    iteration_data=iter_data,
                )
                yield self._evt(
                    "complete",
                    f"Task completed successfully in {iteration} iteration(s).",
                    iterations=all_iterations,
                    final_code=code,
                    success=True,
                    mode="execute",
                    total_time=round(time.time() - start_time, 2),
                    iterations_count=iteration,
                )
                return

            error_info = parse_error(exec_result)
            iter_data["status"] = "failed"
            iter_data["error"] = error_info
            all_iterations.append(iter_data)

            yield self._evt(
                "error",
                f"Error on iteration {iteration}: {error_info['type']}: {error_info['message'][:120]}",
                code=code,
                iteration=iteration,
                execution=exec_result,
                error=error_info,
                iteration_data=iter_data,
            )

            if iteration < max_iterations:
                yield self._evt("reflecting", "Sending error to LLM for reflection and fix", iteration=iteration)
                try:
                    new_code, reflection = self.reflector.reflect_and_refine(
                        task, code, exec_result, error_info
                    )
                    iter_data["reflection"] = reflection
                    code = new_code
                    yield self._evt(
                        "refined",
                        "Code refined based on error feedback",
                        new_code=new_code,
                        reflection=reflection,
                        iteration=iteration,
                    )
                except Exception as exc:
                    yield self._evt("error", f"Reflection failed: {exc}", iteration=iteration)

        yield self._evt(
            "complete",
            f"Reached max iterations ({max_iterations}) without full success.",
            iterations=all_iterations,
            final_code=code,
            success=False,
            mode="execute",
            total_time=round(time.time() - start_time, 2),
            iterations_count=max_iterations,
        )

    def _evt(self, event_type: str, message: str, **kwargs) -> dict:
        return {"type": event_type, "message": message, "timestamp": self._ts(), **kwargs}

    @staticmethod
    def _ts() -> str:
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def _line_count(code: str) -> int:
        return len(code.strip().splitlines())
