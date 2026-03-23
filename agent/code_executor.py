import subprocess
import sys
import tempfile
import os
import time


class CodeExecutor:
    def execute(self, code: str, test_cases: str = "", timeout: int = 10) -> dict:
        full_code = code
        if test_cases.strip():
            full_code = code + "\n\n" + test_cases

        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(full_code)
                tmp = f.name

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"

            t0 = time.time()
            result = subprocess.run(
                [sys.executable, "-X", "utf8", tmp],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=env,
            )
            elapsed = time.time() - t0

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "elapsed": round(elapsed, 3),
                "timed_out": False,
                "full_code": full_code,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"TimeoutError: Execution exceeded {timeout} seconds.",
                "return_code": -1,
                "elapsed": float(timeout),
                "timed_out": True,
                "full_code": full_code,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "elapsed": 0.0,
                "timed_out": False,
                "full_code": full_code,
            }
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
