# Generated-like dynamic protobuf module for python_nezha_agent/proto/nezha.proto.
# It avoids a protoc build step while keeping the standard *_pb2 API shape used by gRPC.

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory


def _field(name, number, field_type, label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL, type_name=None):
    item = descriptor_pb2.FieldDescriptorProto(
        name=name,
        number=number,
        label=label,
        type=field_type,
    )
    if type_name:
        item.type_name = type_name
    return item


def _message(name, fields):
    msg = descriptor_pb2.DescriptorProto(name=name)
    msg.field.extend(fields)
    return msg


_file = descriptor_pb2.FileDescriptorProto(
    name="nezha.proto",
    package="proto",
    syntax="proto3",
)

_file.message_type.extend(
    [
        _message(
            "Host",
            [
                _field("platform", 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("platform_version", 2, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("cpu", 3, descriptor_pb2.FieldDescriptorProto.TYPE_STRING, descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED),
                _field("mem_total", 4, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("disk_total", 5, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("swap_total", 6, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("arch", 7, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("virtualization", 8, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("boot_time", 9, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("version", 10, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("gpu", 11, descriptor_pb2.FieldDescriptorProto.TYPE_STRING, descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED),
            ],
        ),
        _message(
            "State",
            [
                _field("cpu", 1, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE),
                _field("mem_used", 2, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("swap_used", 3, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("disk_used", 4, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("net_in_transfer", 5, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("net_out_transfer", 6, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("net_in_speed", 7, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("net_out_speed", 8, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("uptime", 9, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("load1", 10, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE),
                _field("load5", 11, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE),
                _field("load15", 12, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE),
                _field("tcp_conn_count", 13, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("udp_conn_count", 14, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("process_count", 15, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("temperatures", 16, descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE, descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED, ".proto.State_SensorTemperature"),
                _field("gpu", 17, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE, descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED),
            ],
        ),
        _message(
            "State_SensorTemperature",
            [
                _field("name", 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("temperature", 2, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE),
            ],
        ),
        _message(
            "Task",
            [
                _field("id", 1, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("type", 2, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("data", 3, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
            ],
        ),
        _message(
            "TaskResult",
            [
                _field("id", 1, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("type", 2, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("delay", 3, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
                _field("data", 4, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("successful", 5, descriptor_pb2.FieldDescriptorProto.TYPE_BOOL),
            ],
        ),
        _message("Receipt", [_field("proced", 1, descriptor_pb2.FieldDescriptorProto.TYPE_BOOL)]),
        _message("Uint64Receipt", [_field("data", 1, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64)]),
        _message("IOStreamData", [_field("data", 1, descriptor_pb2.FieldDescriptorProto.TYPE_BYTES)]),
        _message(
            "GeoIP",
            [
                _field("use6", 1, descriptor_pb2.FieldDescriptorProto.TYPE_BOOL),
                _field("ip", 2, descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE, type_name=".proto.IP"),
                _field("country_code", 3, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("dashboard_boot_time", 4, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
            ],
        ),
        _message(
            "IP",
            [
                _field("ipv4", 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("ipv6", 2, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
            ],
        ),
    ]
)

_pool = descriptor_pool.Default()
try:
    DESCRIPTOR = _pool.AddSerializedFile(_file.SerializeToString())
except TypeError:
    DESCRIPTOR = _pool.FindFileByName("nezha.proto")

Host = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.Host"))
State = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.State"))
State_SensorTemperature = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.State_SensorTemperature"))
Task = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.Task"))
TaskResult = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.TaskResult"))
Receipt = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.Receipt"))
Uint64Receipt = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.Uint64Receipt"))
IOStreamData = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.IOStreamData"))
GeoIP = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.GeoIP"))
IP = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.IP"))

__all__ = [
    "Host",
    "State",
    "State_SensorTemperature",
    "Task",
    "TaskResult",
    "Receipt",
    "Uint64Receipt",
    "IOStreamData",
    "GeoIP",
    "IP",
]
