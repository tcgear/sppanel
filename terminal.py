from __future__ import annotations

import fcntl
import json
import logging
import os
import pty
import queue
import select
import shutil
import signal
import struct
import termios
import threading
import time
from collections.abc import Iterator

try:
    from .config import AgentConfig
    from .grpc_client import GrpcClient
    from .proto import nezha_pb2
except ImportError:
    from config import AgentConfig
    from grpc_client import GrpcClient
    from proto import nezha_pb2

log = logging.getLogger(__name__)

STREAM_ID_HEADER = b"\xff\x05\xff\x05"


class TerminalHandler:
    def __init__(self, config: AgentConfig, grpc_client: GrpcClient) -> None:
        self.config = config
        self.grpc_client = grpc_client

    def handle(self, task) -> None:
        if self.config.disable_command_execute:
            log.info("Command execution is disabled for this agent")
            return

        stream_id = self._parse_stream_id(task.data)
        if not stream_id:
            log.error("Terminal task missing StreamID")
            return

        log.info("Terminal init %s", stream_id)
        session = TerminalSession(stream_id, self.grpc_client)
        thread = threading.Thread(target=session.run, name=f"terminal-{stream_id}", daemon=True)
        thread.start()

    @staticmethod
    def _parse_stream_id(data: str) -> str:
        try:
            payload = json.loads(data or "{}")
        except json.JSONDecodeError as exc:
            log.error("Terminal task parse error: %s", exc)
            return ""
        return str(payload.get("StreamID") or payload.get("stream_id") or payload.get("streamId") or "")


class TerminalSession:
    def __init__(self, stream_id: str, grpc_client: GrpcClient) -> None:
        self.stream_id = stream_id
        self.grpc_client = grpc_client
        self.outgoing: queue.Queue[bytes | None] = queue.Queue()
        self.stop = threading.Event()
        self.master_fd: int | None = None
        self.child_pid: int | None = None

    def run(self) -> None:
        try:
            self.child_pid, self.master_fd = pty.fork()
            if self.child_pid == 0:
                self._exec_shell()
                raise SystemExit(127)

            self.outgoing.put(STREAM_ID_HEADER + self.stream_id.encode("utf-8"))
            threads = [
                threading.Thread(target=self._read_pty_output, name=f"terminal-output-{self.stream_id}", daemon=True),
                threading.Thread(target=self._keepalive, name=f"terminal-keepalive-{self.stream_id}", daemon=True),
            ]
            for thread in threads:
                thread.start()

            assert self.grpc_client.stub is not None
            for item in self.grpc_client.stub.IOStream(self._request_iterator()):
                if self.stop.is_set():
                    break
                self._handle_input(bytes(item.data))
        except Exception as exc:
            log.error("Terminal IOStream failed for %s: %s", self.stream_id, exc)
        finally:
            self.close()
            log.info("Terminal session closed for %s", self.stream_id)

    def _exec_shell(self) -> None:
        env = os.environ.copy()
        env["TERM"] = "xterm"
        shell = self._select_shell()
        os.execvpe(shell, [shell], env)

    def _request_iterator(self) -> Iterator[object]:
        while not self.stop.is_set():
            try:
                data = self.outgoing.get(timeout=1)
            except queue.Empty:
                continue
            if data is None:
                break
            yield nezha_pb2.IOStreamData(data=data)

    def _read_pty_output(self) -> None:
        fd = self.master_fd
        if fd is None:
            return
        try:
            while not self.stop.is_set():
                try:
                    ready, _, _ = select.select([fd], [], [], 0.5)
                except OSError:
                    break
                if not ready:
                    continue
                try:
                    data = os.read(fd, 10240)
                except OSError:
                    break
                if not data:
                    break
                self.outgoing.put(data)
        finally:
            self.stop.set()
            self.outgoing.put(None)

    def _keepalive(self) -> None:
        while not self.stop.wait(30):
            self.outgoing.put(b"")

    def _handle_input(self, raw: bytes) -> None:
        fd = self.master_fd
        if not raw or fd is None:
            return
        data = self._strip_control_prefix(raw)
        data = self._handle_resize_prefix(data)
        if data:
            try:
                os.write(fd, data)
            except OSError:
                self.stop.set()

    def _handle_resize_prefix(self, raw: bytes) -> bytes:
        text = self._decode_control_text(raw)
        start = text.find("{")
        if start == -1 or ('"Rows"' not in text and '"rows"' not in text):
            return raw

        end = self._find_json_end(text, start)
        if end <= start:
            return raw

        try:
            size = json.loads(text[start : end + 1])
            rows = int(size.get("Rows", size.get("rows", 24)))
            cols = int(size.get("Cols", size.get("cols", 80)))
            self._resize(cols, rows)
            log.debug("Terminal resize for %s: %sx%s", self.stream_id, cols, rows)
            remaining = text[:start] + text[end + 1 :]
            return remaining.encode("utf-8")
        except Exception:
            return raw

    def _resize(self, cols: int, rows: int) -> None:
        if self.master_fd is None:
            return
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        if self.child_pid:
            try:
                os.kill(self.child_pid, signal.SIGWINCH)
            except OSError:
                pass

    def close(self) -> None:
        self.stop.set()
        self.outgoing.put(None)
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
        if self.child_pid is not None:
            try:
                os.kill(self.child_pid, signal.SIGHUP)
            except OSError:
                pass
            try:
                os.waitpid(self.child_pid, os.WNOHANG)
            except ChildProcessError:
                pass
            self.child_pid = None

    @staticmethod
    def _select_shell() -> str:
        for shell in (os.environ.get("SHELL"), "zsh", "fish", "bash", "sh"):
            if shell and shutil.which(shell):
                return shell
        return "/bin/sh"

    @staticmethod
    def _strip_control_prefix(raw: bytes) -> bytes:
        if len(raw) > 1 and raw[0] == 0x01:
            rest = raw[1:]
            if all(byte in (9, 10, 13) or 32 <= byte <= 126 for byte in rest):
                return rest
        return raw

    @staticmethod
    def _decode_control_text(raw: bytes) -> str:
        if len(raw) >= 4 and len(raw) % 2 == 0:
            odd_nulls = sum(1 for idx in range(1, len(raw), 2) if raw[idx] == 0)
            even_nulls = sum(1 for idx in range(0, len(raw), 2) if raw[idx] == 0)
            if odd_nulls >= len(raw) // 4:
                return raw.decode("utf-16le", errors="ignore")
            if even_nulls >= len(raw) // 4:
                return raw.decode("utf-16be", errors="ignore")
        return raw.decode("utf-8", errors="ignore")

    @staticmethod
    def _find_json_end(text: str, start: int) -> int:
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return index
        return -1
