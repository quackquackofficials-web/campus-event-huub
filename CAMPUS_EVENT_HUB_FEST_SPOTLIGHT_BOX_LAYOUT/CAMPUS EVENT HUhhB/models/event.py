"""Object-oriented event models used by the Flask application.

OOP concepts demonstrated:
- Abstraction: Event is an abstract base class.
- Encapsulation: event data is stored in the private __details attribute.
- Inheritance: ArtsEvent, TechEvent, SportsEvent and GeneralEvent inherit Event.
- Polymorphism: each subclass overrides event_kind().
"""
from abc import ABC, abstractmethod


class Event(ABC):
    def __init__(self, details):
        self.__details = dict(details)

    @property
    def details(self):
        # Return a copy so callers cannot mutate the internal record.
        return dict(self.__details)

    @property
    def title(self):
        return self.__details.get("title", "")

    @property
    def venue(self):
        return self.__details.get("venue", "")

    @abstractmethod
    def event_kind(self):
        """Return a label specific to the event family."""
        raise NotImplementedError

    def as_dict(self):
        result = self.details
        result["event_kind"] = self.event_kind()
        return result


class ArtsEvent(Event):
    def event_kind(self):
        return "YVIDH Arts Fest Event"


class TechEvent(Event):
    def event_kind(self):
        return "YVIDH Tech Fest Event"


class SportsEvent(Event):
    def event_kind(self):
        return "Sports Competition"


class GeneralEvent(Event):
    def event_kind(self):
        return "Campus Celebration / Special Event"


def event_model_for(details):
    fest = details.get("fest")
    if fest == "yvidh-arts":
        return ArtsEvent(details)
    if fest == "yvidh-tech":
        return TechEvent(details)
    if fest in {"rapido", "spike"}:
        return SportsEvent(details)
    return GeneralEvent(details)
