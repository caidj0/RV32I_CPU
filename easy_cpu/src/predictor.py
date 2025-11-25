from abc import ABC, abstractmethod
from dataclasses import dataclass
from assassyn.frontend import *
from assassyn.frontend import Value
from utils import Bool


@dataclass
class PredictFeedback:
    addr: Value
    predict_branch: Value
    actual_branch: Value


class Predictor(Downstream, ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def build(self, branch_addr: Value, feed_back: PredictFeedback) -> Value:
        pass


class AlwaysBranchPredictor(Predictor):
    def __init__(self):
        super().__init__()

    @downstream.combinational
    def build(self, branch_addr: Value, feed_back: PredictFeedback) -> Value:
        with Condition(branch_addr.valid()):
            return Bool(1) | Bool(1)


class NeverBranchPredictor(Predictor):
    def __init__(self):
        super().__init__()

    @downstream.combinational
    def build(self, branch_addr: Value, feed_back: PredictFeedback) -> Value:
        with Condition(branch_addr.valid()):
            return Bool(0) | Bool(0)
