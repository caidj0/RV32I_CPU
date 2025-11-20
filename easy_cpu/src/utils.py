from abc import ABC
import contextlib
from dataclasses import dataclass
import io
import os
from typing import Callable, Any, Self
from assassyn.frontend import *
from assassyn.ir.expr.call import Bind

Bool = Bits(1)


class ValueWrapper:
    value: Value
    valid: Value

    def __init__(self, dtype: Callable[[Any], Value], default_valid: bool, initializer: Any = 0):
        self.value = dtype(initializer)
        self.valid = Bool(int(default_valid))

    def bind_with(self, bound: tuple[Module | Bind, str]):
        with Condition(self.valid):
            receiver, name = bound
            receiver.bind(**{name: self.value})

    def set(self, value: Value):
        self.value |= value
        self.valid |= Bool(1)


def pop_or(port: Port, default_value: Value) -> Value:
    valid = port.valid()
    value = valid.select(port.peek(), default_value)
    with Condition(valid):
        port.pop()
    return value


def peek_or(port: Port, default_value: Value) -> Value:
    valid = port.valid()
    value = valid.select(port.peek(), default_value)
    return value


def forward_ports(receiver: Module | Bind, ports: list[Port]):
    for port in ports:
        name = port.name
        with Condition(port.valid()):
            receiver.bind(**{name: port.pop()})


def to_one_hot(value: Value, select_number: int) -> Value:
    return Bits(select_number)(1) << value


def run_quietly(func: Callable[[Any], Any], *args, **kwargs) -> tuple[Any | None, str, str]:
    """Runs a function while capturing all output."""
    """Original version from assassyn."""
    stdout = io.StringIO()
    stderr = io.StringIO()
    result = None

    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            with open(os.devnull, "w") as devnull:
                # 重定向原始文件描述符，捕获低层系统调用的输出
                old_stdout = os.dup(1)
                old_stderr = os.dup(2)
                os.dup2(devnull.fileno(), 1)
                os.dup2(devnull.fileno(), 2)
                try:
                    result = func(*args, **kwargs)
                finally:
                    os.dup2(old_stdout, 1)
                    os.dup2(old_stderr, 2)
        except Exception as e:
            stderr.write(f"Error: {str(e)}\n")

    return result, stdout.getvalue(), stderr.getvalue()


class RecodeWrapper(ABC):
    def bind_with(self, receiver: Module | Bind, skips: list[str] = []):
        for name, v in self.__dict__.items():
            if name in skips or not isinstance(v, ValueWrapper):
                continue
            v.bind_with((receiver, name))
