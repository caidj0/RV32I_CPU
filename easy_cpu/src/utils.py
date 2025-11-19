from assassyn.frontend import *

Bool = Bits(1)

def pop_or(port: Port, default_value: Value) -> Value:
    valid = port.valid()
    value = valid.select(port.peek(), default_value)
    with Condition(valid):
        port.pop()
    return value