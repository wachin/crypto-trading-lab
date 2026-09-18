# ADR-0007: Beginner Documentation

## Status
Accepted

## Context
The application must teach beginners how to:
* Understand cryptocurrency basics
* Use the application safely
* Avoid common mistakes

## Decision
Documentation lives alongside code in `docs/en/beginners/`. It includes:
* `00-start-here.md` - Entry point
* Glossary of terms
* Feature explanations
* Learning Center in-app content

## Consequences

### Positive
* Documentation versioned with code
* Beginner explanations evolve with features
* Learning Center accessible in app

### Negative
* Requires ongoing maintenance
* More content to translate

### Alternatives Considered
* **External website**: Not integrated with app context
* **In-app only**: Harder to update without app update
