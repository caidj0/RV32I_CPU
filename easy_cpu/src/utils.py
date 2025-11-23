from abc import ABC
import contextlib
from dataclasses import dataclass
import io
import os
from typing import Callable, Any, Self
from assassyn.frontend import *
from assassyn.ir.expr.call import Bind
from assassyn.ir.const import Const

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

    def select(self, cond: Value, value: Value):
        self.value = cond.select(value, self.value)
        self.valid = cond.select(Bool(1), self.valid)


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


# For sext in assassyn is implemented incorrectly
def sext(value: Value, target_type: DType) -> Value:
    dtype: DType = value.dtype  # pyright: ignore[reportAssignmentType]
    bits: int = dtype.bits
    target_bits = target_type.bits
    delta_bits = target_bits - bits

    assert delta_bits > 0

    is_negative = value[bits - 1 : bits - 1]
    higher = is_negative.select(Bits(delta_bits)((1 << delta_bits) - 1), Bits(delta_bits)(0))
    return higher.concat(value).bitcast(target_type)


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
