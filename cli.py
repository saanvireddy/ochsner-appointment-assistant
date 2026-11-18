"""Interactive appointment workflow. Run with python cli.py."""

import argparse
import logging
import re
from datetime import date

from intent import LOCATIONS, SPECIALTIES, extract, intent
from scheduling_api import SchedulingAPI, SchedulingError


class Handoff(Exception):
    def __init__(self, reason, message):
        self.reason = reason
        self.message = message


HANDOFF_MESSAGES = {
    "user_requested": "You asked to speak with a person.",
    "medical_advice": "This assistant handles scheduling. A clinician can help with medical questions.",
    "unsupported_request": "This request needs help from the scheduling team.",
}


def handoff(api, reason, message):
    print(message)
    logging.info("handoff reason=%s", reason)
    try:
        result = api.request("/handoffs", body={"reason": reason, "summary": message})
        if result.get("handoffId"):
            print(f"Human handoff queued. Reference: {result['handoffId']}")
            return
    except SchedulingError:
        pass
    print("Please contact the clinic's scheduling team directly.")


def ask(prompt):
    answer = input(prompt).strip()
    route = intent(answer)
    if route in ("user_requested", "medical_advice"):
        raise Handoff(route, HANDOFF_MESSAGES[route])
    return answer


def filter_value(text, label, choices):
    value = extract(text, choices)
    if value is not None:
        return value
    answer = ask(f"Which {label} ({', '.join(choices)})? ")
    value = choices.get(answer.lower().replace("_", " "))
    if value is None:
        raise Handoff("unsupported_request", f"I could not select a supported {label}.")
    return value


def identify(api):
    for _ in range(2):
        phone = ask("Phone (e.g. 555-0101): ")
        dob = ask("Date of birth (YYYY-MM-DD): ")
        try:
            date.fromisoformat(dob)
            valid_date = re.fullmatch(r"\d{4}-\d{2}-\d{2}", dob)
        except ValueError:
            valid_date = False
        if not re.fullmatch(r"\d{3}-\d{4}", phone) or not valid_date:
            print("Use the displayed phone and date formats.")
            continue
        matches = api.request("/patients/search", params={"phone": phone, "dob": dob})["matches"]
        if len(matches) == 1:
            return matches[0]["patientId"]
        if matches:
            zip_code = ask("What is your ZIP code? ")
            narrowed = [patient for patient in matches if patient.get("zipCode") == zip_code]
            if len(narrowed) == 1:
                return narrowed[0]["patientId"]
            break
        print("No patient matched those details. Please check them.")
    raise Handoff("identity_unclear", "I could not verify the patient for this booking.")


def describe_slot(slot, names):
    provider = names.get(slot["providerId"], slot["providerId"])
    return f"{slot['startTime']} | {provider} | {slot['location']}"


def book(api, filters, providers):
    patient_id = identify(api)
    result = api.request("/availability", params={**filters, "patientId": patient_id})
    slots = [slot for slot in result["slots"] if slot["available"]]
    if not slots:
        raise Handoff("no_availability", "No appointments are available for that search.")

    names = {provider["providerId"]: provider["name"] for provider in providers}
    for number, slot in enumerate(slots, start=1):
        print(f"{number}. {describe_slot(slot, names)}")
    while True:
        choice = ask("Choose a slot number or type back: ")
        if choice.lower() == "back":
            return
        options = {str(number): slot for number, slot in enumerate(slots, start=1)}
        if choice in options:
            selected = options[choice]
            break
        print("Choose one of the displayed numbers.")

    print(f"Selected: {describe_slot(selected, names)}")
    if ask("Type yes to book this appointment: ").lower() != "yes":
        print("Booking canceled.")
        return

    try:
        result = api.request("/appointments", body={
            "patientId": patient_id, "slotId": selected["slotId"], "confirmed": True,
        })
        appointment = result["appointment"]
        reference = appointment["appointmentId"]
    except SchedulingError as error:
        if error.status == 409:
            raise Handoff("no_availability", "That slot is no longer available.") from None
        if error.status == 400:
            raise Handoff("api_failure", "The scheduler rejected the booking.") from None
        raise Handoff("api_failure", "Booking status is unknown. Please have scheduling verify it.") from None
    except (KeyError, TypeError):
        raise Handoff("api_failure", "Booking status is unknown. Please have scheduling verify it.") from None

    print(f"Booked: {describe_slot(appointment, names)} | Reference: {reference}")


def run(api):
    print("Appointment assistant. Ask to find a provider or book an appointment.")
    print("Use synthetic information only. Type quit at the main prompt to exit.")
    while True:
        try:
            text = input("\nHow can I help? ").strip()
            if text.lower() == "quit":
                return
            if not text:
                continue
            route = intent(text)
            logging.info("intent=%s", route)
            if route in HANDOFF_MESSAGES:
                raise Handoff(route, HANDOFF_MESSAGES[route])
            filters = {
                "specialty": filter_value(text, "specialty", SPECIALTIES),
                "location": filter_value(text, "location", LOCATIONS),
            }
            providers = api.request("/providers", params=filters)["providers"]
            if route == "book":
                book(api, filters, providers)
            elif providers:
                for provider in providers:
                    print(f"{provider['name']} | {', '.join(provider['locations'])}")
            else:
                print("No providers matched that search.")
        except Handoff as error:
            handoff(api, error.reason, error.message)
        except (SchedulingError, KeyError, TypeError):
            handoff(api, "api_failure", "The scheduler could not complete the request.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:4010")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        run(SchedulingAPI(args.base_url))
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")


if __name__ == "__main__":
    main()
