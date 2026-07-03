from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Diagnostic:
    code: str
    path: str
    message: str

    def line(self) -> str:
        return f"{self.code} {self.path}: {self.message}"
