"""Small, local interpreter for the supported scheduling phrases."""

import re

SPECIALTIES = {"primary care": "primary_care", "dermatology": "dermatology"}
LOCATIONS = {name: name for name in ("downtown", "uptown", "lakeside")}


def normalize(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def mentions(text, phrase):
    return f" {phrase} " in f" {normalize(text)} "


def intent(text):
    if any(mentions(text, phrase) for phrase in
           ("pain", "symptoms", "medication", "should i", "medical advice", "rash")):
        return "medical_advice"
    if any(mentions(text, phrase) for phrase in
           ("human", "person", "representative", "handoff")):
        return "user_requested"
    if any(mentions(text, phrase) for phrase in
           ("cancel", "reschedule", "my appointment", "my appointments")):
        return "unsupported_request"
    if any(mentions(text, phrase) for phrase in ("book", "schedule", "make an appointment")):
        return "book"
    if any(mentions(text, phrase) for phrase in ("provider", "providers", "doctor", "doctors")):
        return "providers"
    return "unsupported_request"


def extract(text, choices):
    matches = [value for label, value in choices.items() if mentions(text, label)]
    return matches[0] if len(matches) == 1 else None
