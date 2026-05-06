from typing import Callable

_FUNC_NAME = "_pycliped_user_func"


def compile_user_code(body: str) -> Callable[[str], object]:
    """Wrap the user-supplied function body in a `def` and return the function.

    `body` is the indented contents of a function whose argument is `text`.
    A `return` is permitted but not required (None means "no change").
    """
    indented = "\n".join("    " + line if line else "" for line in body.splitlines())
    if not indented.strip():
        indented = "    return text"
    source = f"def {_FUNC_NAME}(text):\n{indented}\n"
    namespace: dict = {}
    code = compile(source, "<pycliped-user-code>", "exec")
    exec(code, namespace)
    return namespace[_FUNC_NAME]


def run_user_code(func: Callable[[str], object], text: str):
    """Run the compiled user function. Returns the value verbatim (or None)."""
    result = func(text)
    if result is None:
        return None
    if not isinstance(result, str):
        result = str(result)
    return result
