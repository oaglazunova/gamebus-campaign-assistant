from __future__ import annotations

from campaign_assistant.metadata.models import MetadataBundle


def load_gamebus_metadata(*args, **kwargs) -> MetadataBundle:
    """
    Placeholder for future GameBus-native metadata loading.

    For now this returns an empty bundle, so the rest of the system can already
    be written against a stable adapter interface.
    """
    bundle = MetadataBundle()
    bundle.notes.append("GameBus-native metadata adapter is not implemented yet.")
    return bundle