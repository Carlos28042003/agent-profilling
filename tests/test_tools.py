from agentic_profiling.tools import calculator, python_exec


def test_calculator_arithmetic():
    assert calculator("1234 * 5678 + 91011") == "7097663"
    assert calculator("2^10") == "1024"
    assert calculator("1998 - 1975") == "23"


def test_calculator_functions():
    assert calculator("sqrt(2)").startswith("1.41421356")


def test_calculator_rejects_code():
    assert calculator('__import__("os")').startswith("Error")
    assert calculator("(1).__class__").startswith("Error")
    assert calculator("1 +").startswith("Error")


def test_python_exec_prints():
    assert python_exec("print(sum(range(10)))") == "45"


def test_python_exec_strips_code_fences():
    assert python_exec("```python\nprint(2 + 2)\n```") == "4"


def test_python_exec_reports_errors():
    assert "ZeroDivisionError" in python_exec("print(1 / 0)")


def test_python_exec_timeout():
    assert "timed out" in python_exec("while True: pass", timeout=1)


def test_python_exec_no_output_hint():
    assert "print()" in python_exec("x = 1")
