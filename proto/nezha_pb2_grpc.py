# Generated-like gRPC client bindings for python_nezha_agent/proto/nezha.proto.

import grpc

from . import nezha_pb2 as proto_dot_nezha__pb2


class NezhaServiceStub(object):
    def __init__(self, channel):
        self.ReportSystemState = channel.stream_stream(
            "/proto.NezhaService/ReportSystemState",
            request_serializer=proto_dot_nezha__pb2.State.SerializeToString,
            response_deserializer=proto_dot_nezha__pb2.Receipt.FromString,
        )
        self.ReportSystemInfo = channel.unary_unary(
            "/proto.NezhaService/ReportSystemInfo",
            request_serializer=proto_dot_nezha__pb2.Host.SerializeToString,
            response_deserializer=proto_dot_nezha__pb2.Receipt.FromString,
        )
        self.RequestTask = channel.stream_stream(
            "/proto.NezhaService/RequestTask",
            request_serializer=proto_dot_nezha__pb2.TaskResult.SerializeToString,
            response_deserializer=proto_dot_nezha__pb2.Task.FromString,
        )
        self.IOStream = channel.stream_stream(
            "/proto.NezhaService/IOStream",
            request_serializer=proto_dot_nezha__pb2.IOStreamData.SerializeToString,
            response_deserializer=proto_dot_nezha__pb2.IOStreamData.FromString,
        )
        self.ReportGeoIP = channel.unary_unary(
            "/proto.NezhaService/ReportGeoIP",
            request_serializer=proto_dot_nezha__pb2.GeoIP.SerializeToString,
            response_deserializer=proto_dot_nezha__pb2.GeoIP.FromString,
        )
        self.ReportSystemInfo2 = channel.unary_unary(
            "/proto.NezhaService/ReportSystemInfo2",
            request_serializer=proto_dot_nezha__pb2.Host.SerializeToString,
            response_deserializer=proto_dot_nezha__pb2.Uint64Receipt.FromString,
        )


class NezhaServiceServicer(object):
    def ReportSystemState(self, request_iterator, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def ReportSystemInfo(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def RequestTask(self, request_iterator, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def IOStream(self, request_iterator, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def ReportGeoIP(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def ReportSystemInfo2(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")
