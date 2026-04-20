"""Serialization scaffolding.

Provides abstract :class:`Serializer` / :class:`Deserializer` base classes and
a format registry. Users are expected to subclass these for their own domain
types. The FeelUOwn music-model-specific implementations have been stripped;
see the git history at upstream for reference implementations.
"""

from .base import (
    SerializerError,
    DeserializerError,
    Serializer,
    Deserializer,
    SerializerMeta,
    SimpleSerializerMixin,
)


_MAPPING: dict = {}
_DE_MAPPING: dict = {}


def register_serializer(type_, serializer_cls):
    _MAPPING[type_] = serializer_cls


def register_deserializer(type_, deserializer_cls):
    _DE_MAPPING[type_] = deserializer_cls


def get_serializer(format_):
    if format_ not in _MAPPING:
        raise SerializerError(f"Serializer for format:{format_} not found")
    return _MAPPING.get(format_)


def get_deserializer(format_: str):
    if format_ not in _DE_MAPPING:
        raise DeserializerError(f"Deserializer for format:{format_} not found")
    return _DE_MAPPING[format_]


def serialize(format_, obj, **options):
    serializer = get_serializer(format_)(**options)
    return serializer.serialize(obj)


def deserialize(format_, obj, **options):
    deserializer = get_deserializer(format_)(**options)
    return deserializer.deserialize(obj)


__all__ = (
    'SerializerError',
    'DeserializerError',
    'Serializer',
    'Deserializer',
    'SerializerMeta',
    'SimpleSerializerMixin',
    'register_serializer',
    'register_deserializer',
    'get_serializer',
    'get_deserializer',
    'serialize',
    'deserialize',
)
