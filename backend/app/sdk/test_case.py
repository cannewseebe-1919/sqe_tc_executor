"""TestCase base class for TC scripts."""

import inspect
import json
import sys
import time


class TestCase:
    """Base class for all test cases.

    Subclasses define steps using the @step decorator on methods.
    Methods are executed in alphabetical order by default.

    Class attributes:
        app_package: Target app package name.
        timeout_per_step: Default timeout per step in seconds.
    """

    app_package: str = ""
    timeout_per_step: int = 30

    def run(self):
        """Execute all @step-decorated methods in order."""
        steps = self._collect_steps()
        total = len(steps)
        print(json.dumps({
            "type": "execution_start",
            "total_steps": total,
            "test_class": self.__class__.__name__,
        }), flush=True)

        results = []
        for i, (method_name, method) in enumerate(steps):
            result = method()
            if isinstance(result, dict):
                results.append(result)
                # Abort on crash-level errors
                if result.get("error_type") in ("APP_CRASH", "KERNEL_PANIC", "SYSTEM_UI_CRASH"):
                    print(json.dumps({
                        "type": "execution_abort",
                        "reason": result["error_type"],
                        "at_step": method_name,
                    }), flush=True)
                    break

        passed = sum(1 for r in results if r.get("status") == "PASSED")
        failed = sum(1 for r in results if r.get("status") == "FAILED")
        print(json.dumps({
            "type": "execution_end",
            "total": len(results),
            "passed": passed,
            "failed": failed,
        }), flush=True)

    def _collect_steps(self) -> list[tuple[str, callable]]:
        """Collect all @step-decorated methods, sorted by name."""
        steps = []
        for name in sorted(dir(self)):
            method = getattr(self, name, None)
            if callable(method) and hasattr(method, "__wrapped__"):
                inner = method.__wrapped__ if hasattr(method, "__wrapped__") else method
                if hasattr(method, "_step_name") or name.startswith("step_"):
                    steps.append((name, method))
            elif callable(method) and hasattr(method, "_step_name"):
                steps.append((name, method))
        return steps


# Auto-run when executed as script
def _auto_run():
    """Find TestCase subclass in __main__ module and run it."""
    import __main__
    for name, obj in inspect.getmembers(__main__):
        if (
            inspect.isclass(obj)
            and issubclass(obj, TestCase)
            and obj is not TestCase
        ):
            instance = obj()
            instance.run()
            return
    print("No TestCase subclass found", file=sys.stderr)
    sys.exit(1)
