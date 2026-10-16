# SAT-V&V v1.0.3 — Comparison chart visual hotfix

This is a presentation-only correction to the existing v1.0.3 release.

- Early warnings appear as **amber point-in-time markers**, not misleading amber time-spanning bars.
- Warning status labels are drawn in a separate right-hand column, so they cannot overwrite the timeline.
- Verified requirement failures retain mint duration-to-detection bars.
- Unobserved outcomes use neutral “No event” text.
- A shared time axis and compact/narrow-width text fitting improve legibility.
- Canvas includes an accessible description.

No physics, seeded scenarios, scheduling algorithms, diagnosis logic, or benchmark outcomes were changed.

Run: `python -m unittest discover -s tests -v` and `python -m satvv serve`.
