I completed this within the assigned 2-hour window.

# Appointment scheduling CLI

A small Python prototype for provider lookup, appointment booking, and scheduling handoff. Use only the supplied synthetic data.

## Run locally

Python 3.8+ is sufficient. There are no packages to install or credentials to configure. From this directory, start the mock in one terminal:

```sh
python mock-api/server.py
```

Start the CLI in a second terminal:

```sh
python cli.py --verbose
```

Omit `--verbose` to hide diagnostic logs. Use `--base-url` if the mock is running on a different port. Restart the mock to reset its in-memory bookings.

## Demo

1. Enter `Which primary care providers are downtown?`. The list comes from the mock without an identity check.
2. Enter `Book a primary care appointment downtown`. Enter `555-0101` and `1985-04-12`, choose slot `1` on a fresh mock, and type `yes`. The CLI prints the reference returned by the scheduler. Try `no` first to see the confirmation gate.
3. Start another booking and enter `555-9999` and `1990-01-01` on both attempts. The CLI queues an identity handoff without including the input values.
4. Optional conflict demo: select the downtown primary-care slot marked `slot_conflict_001` in the fixture by matching its time in the displayed list. It returns 409 after confirmation and the CLI offers a human handoff.

## Code map and decisions

- `intent.py` recognizes a small vocabulary for booking, provider lookup, handoff, and medical questions. This is a deliberate rules-based baseline. It has limited phrasing coverage and needs no model or network credentials.
- `cli.py` owns the conversation and policy checks. It verifies a mock patient before asking for availability. If phone and DOB match multiple records, it asks for ZIP without exposing candidates. Only a standalone `yes` at the selected slot's confirmation prompt can reach the booking call. The flow discards its state when it returns to the main prompt.
- `scheduling_api.py` owns HTTP, timeouts, and method/path/status/latency logs. The CLI logs intent and handoff reason. Logs omit request parameters, bodies, and raw user input. The CLI never automatically retries a booking write, because a lost response can leave the outcome unknown.

## Limits and next steps

Phone, date of birth, and ZIP are fixture matching for the demo. A real workflow would use the organization's patient authentication and an approved human routing channel. The mock queues simulated handoffs. This prototype supports provider lookup and new bookings. Appointment lookup, rescheduling, and cancellation are future work.

The assignment describes an AI assistant. A next step is a model-backed interpreter with validated intent and filter output, while keeping identity collection and the booking authorization path in Python. I would also add explicit idempotency and a booking status check before enabling recovery from uncertain writes.

## Run the tests

From the project directory:

```sh
python -m unittest discover -s tests -v
```

The tests use canned API responses, so the mock server does not need to be running.
They cover provider lookup, the booking confirmation gate, identity handoff, and
the manual fallback when the API is unavailable.
