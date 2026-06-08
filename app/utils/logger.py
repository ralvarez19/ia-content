"""Logger por job: cada job escribe a su propio logs.txt."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from threading import Lock


class JobLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        if not self.log_path.exists():
            self.log_path.write_text("", encoding="utf-8")

    def log(self, level: str, msg: str) -> None:
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level.upper():5}] {msg}\n"
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line)
        # Mirror a stdout para verlo en uvicorn
        print(line, end="", flush=True)

    def info(self, msg: str) -> None:  self.log("info", msg)
    def warn(self, msg: str) -> None:  self.log("warn", msg)
    def error(self, msg: str) -> None: self.log("error", msg)
    def step(self, msg: str) -> None:  self.log("step", msg)

    def read(self) -> str:
        if not self.log_path.exists():
            return ""
        return self.log_path.read_text(encoding="utf-8")
