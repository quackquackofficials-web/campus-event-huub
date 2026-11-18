"""Domain models for Campus Event Hub."""
from .event import Event, ArtsEvent, TechEvent, SportsEvent, GeneralEvent, event_model_for

__all__ = [
    "Event", "ArtsEvent", "TechEvent", "SportsEvent",
    "GeneralEvent", "event_model_for"
]
