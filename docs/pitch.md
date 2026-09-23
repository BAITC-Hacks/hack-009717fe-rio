# Rio Defense Script — Three Minutes

The customer already has a catalog and needs help deciding whom to choose. Rio narrows the selection to three profiles and explains why each one qualifies.

We first check city and category, then availability, budget, event format, language and duration. An unavailable vendor cannot enter the recommendations. Venues follow exactly the same pipeline.

Let us demonstrate a corporate event on October 4. Four candidates pass the constraints, and we display three. Preferences affect their order through transparent lexical matching. Cards contain specific facts and quotations from the profiles. This is an explainable baseline, without generated claims.

Now we change only the date to October 1. The previous three vendors are unavailable. The interface explicitly explains this and shows different candidates. Repeating the request preserves the order.

For florists, we show two options and explain why there are fewer than three. With an insufficient budget, we show rejection reasons. A category missing from a city is a separate outcome.

The service starts with one command and requires no keys or third-party Python packages. All 66 source profiles are preserved, and 12 additional team-created synthetic profiles are explicitly labeled. Future development could add embeddings and live calendars while retaining strict filters and verifiable explanations.

## Questions from Judges

- **Where is the AI?** Development used the Codex AI agent. The running service uses a lexical baseline, not an LLM. We do not claim semantic understanding. A possible next step is embeddings with measured quality.
- **Why not rank only by price?** When preferences are supplied, weighted text overlap comes first and price second. Specific evidence on each card is more important than the order alone.
- **Why are there so few December options?** The source calendars reflect seasonal demand. We do not invent available candidates.
- **Why not search a neighboring city?** The challenge is to select within the chosen catalog, not expand it automatically.
- **What does a starting price mean?** It is a minimum advertised price, not a confirmed final quote.
- **How can we reproduce the result?** Run `python app.py` and use the six numbered scenario buttons. Run checks with `python -m unittest discover -s tests -v`.

## Suggested Speaking Order

1. Participant 1 demonstrates the Russian-language website and the user journey.
2. Participant 2 explains validation, filtering, ranking and deterministic tie-breaking.
3. Participant 3 demonstrates tests, rare and empty outcomes, source integrity and limitations.
