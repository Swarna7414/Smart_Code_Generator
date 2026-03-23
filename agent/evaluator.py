from collections import Counter


class Evaluator:
    def compute_metrics(self, session: dict) -> dict:
        iterations = session.get("iterations", [])
        success = session.get("success", False)
        total_time = session.get("total_time", 0.0)
        n = len(iterations)

        error_types = [
            it["error"]["type"]
            for it in iterations
            if it.get("status") == "failed" and "error" in it
        ]

        exec_times = [
            it["execution"].get("elapsed", 0.0)
            for it in iterations
            if "execution" in it
        ]

        code_lengths = [
            len(it.get("code", "").splitlines())
            for it in iterations
        ]

        return {
            "total_iterations": n,
            "success": success,
            "total_time_s": total_time,
            "avg_exec_time_s": round(sum(exec_times) / len(exec_times), 3) if exec_times else 0,
            "error_types": error_types,
            "error_distribution": dict(Counter(error_types)),
            "code_lengths": code_lengths,
            "iterations_to_success": n if success else None,
        }

    def build_chart_data(self, iterations: list) -> dict:
        labels = [f"Iter {it['iteration']}" for it in iterations]
        statuses = [1 if it.get("status") == "success" else 0 for it in iterations]
        exec_times = [it["execution"].get("elapsed", 0) for it in iterations if "execution" in it]
        code_lengths = [len(it.get("code", "").splitlines()) for it in iterations]

        error_types = [
            it["error"]["type"]
            for it in iterations
            if it.get("status") == "failed" and "error" in it
        ]
        error_dist = dict(Counter(error_types))

        return {
            "labels": labels,
            "statuses": statuses,
            "exec_times": exec_times,
            "code_lengths": code_lengths,
            "error_distribution": error_dist,
        }
