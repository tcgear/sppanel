from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Sequence

import grpc

try:
    from .config import AgentConfig
    from .proto import nezha_pb2_grpc
except ImportError:
    from config import AgentConfig
    from proto import nezha_pb2_grpc

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Credentials:
    client_secret: str
    client_uuid: str


class AuthInterceptor(grpc.UnaryUnaryClientInterceptor, grpc.UnaryStreamClientInterceptor, grpc.StreamStreamClientInterceptor):
    def __init__(self, credentials: Credentials) -> None:
        self.credentials = credentials

    def _metadata(self, metadata: Sequence[tuple[str, str]] | None) -> list[tuple[str, str]]:
        merged = list(metadata or [])
        merged.append(("client-secret", self.credentials.client_secret))
        merged.append(("client-uuid", self.credentials.client_uuid))
        return merged

    def intercept_unary_unary(self, continuation, client_call_details, request):
        details = _ClientCallDetails(client_call_details, self._metadata(client_call_details.metadata))
        return continuation(details, request)

    def intercept_unary_stream(self, continuation, client_call_details, request):
        details = _ClientCallDetails(client_call_details, self._metadata(client_call_details.metadata))
        return continuation(details, request)

    def intercept_stream_stream(self, continuation, client_call_details, request_iterator):
        details = _ClientCallDetails(client_call_details, self._metadata(client_call_details.metadata))
        return continuation(details, request_iterator)


class _ClientCallDetails(grpc.ClientCallDetails):
    def __init__(self, source: grpc.ClientCallDetails, metadata: Iterable[tuple[str, str]]) -> None:
        self.method = source.method
        self.timeout = source.timeout
        self.metadata = list(metadata)
        self.credentials = source.credentials
        self.wait_for_ready = source.wait_for_ready
        self.compression = source.compression


class GrpcClient:
    def __init__(self, auth: AuthInterceptor) -> None:
        self.auth = auth
        self.channel: grpc.Channel | None = None
        self.stub: nezha_pb2_grpc.NezhaServiceStub | None = None

    def connect(self, config: AgentConfig) -> bool:
        self.disconnect()
        target = self._normalize_server(config.server)
        options = (
            ("grpc.keepalive_time_ms", 30_000),
            ("grpc.keepalive_timeout_ms", 10_000),
            ("grpc.keepalive_permit_without_calls", 1),
        )
        try:
            if config.tls:
                if config.insecure_tls:
                    # Python gRPC cannot disable verification per channel cleanly; use default TLS and rely on system trust.
                    log.warning("insecure_tls requested, but Python gRPC uses default certificate verification")
                credentials = grpc.ssl_channel_credentials(root_certificates=None)
                base_channel = grpc.secure_channel(target, credentials, options=options)
            else:
                base_channel = grpc.insecure_channel(target, options=options)

            self.channel = grpc.intercept_channel(base_channel, self.auth)
            self.stub = nezha_pb2_grpc.NezhaServiceStub(self.channel)
            grpc.channel_ready_future(base_channel).result(timeout=10)
            log.info("Connection to %s established", target)
            return True
        except Exception as exc:
            log.error("Failed to connect to dashboard: %s", exc)
            self.disconnect()
            return False

    def disconnect(self) -> None:
        if self.channel is not None:
            close = getattr(self.channel, "close", None)
            if close is not None:
                close()
        self.channel = None
        self.stub = None

    @staticmethod
    def _normalize_server(server: str) -> str:
        if server.startswith("http://"):
            return server[7:]
        if server.startswith("https://"):
            return server[8:]
        return server
