from dataclasses import dataclass


@dataclass
class Agent:
    idx: int
    e: float
    s: float
    h: float
    m: float
    i: float
    u: float
    p: float

    def as_dict(self) -> dict:
        return {
            "id": self.idx,
            "E": self.e,
            "S": self.s,
            "H": self.h,
            "M": self.m,
            "I": self.i,
            "U": self.u,
            "P": self.p,
        }
