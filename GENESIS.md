# Initial instruction for Agent AI — Crypto Trading Lab

You are now working on the **Crypto Trading Lab** project.

The repository contains a Markdown specification document that defines the project's architecture, development methodology, dependencies, packaging requirements, internationalization, security requirements, testing strategy, beginner education system, and development phases.

## IMPORTANT: Read the specification first

Before writing or modifying application code, locate and read the Crypto Trading Lab specification Markdown file in this repository.

**Treat that document as the primary project specification.**

Do not replace, simplify, reinterpret, or silently omit its requirements.

If something in the specification is unclear, identify it explicitly instead of guessing.

---

## Your first task: Phase 0 only

Do **NOT** attempt to implement the entire application yet.

Start with **Phase 0 — Research** and the minimum repository inspection required to prepare Phase 1.

Follow the Phase 0 instructions contained in the specification.

### Step 1 — Inspect the repository

First inspect:

* the current directory;
* the Git repository status;
* the existing files;
* existing source code;
* existing Python configuration;
* existing documentation;
* existing tests;
* existing packaging files;
* existing `.gitignore`;
* existing CI configuration;
* the specification Markdown file.

Do not delete or overwrite existing project files unless the specification explicitly requires it.

---

### Step 2 — Inspect the development environment

Determine:

* operating system;
* Debian/MX Linux version;
* Python version;
* available Qt/PyQt6 version;
* available Qt Linguist tools;
* available Debian packages relevant to the project;
* available Python packages;
* available packaging tools;
* available testing tools;
* available Debian packaging tools.

The project is intended primarily for Debian-based systems, so pay particular attention to **Debian 12 compatibility**.

Also consider Debian 13 compatibility where possible.

---

### Step 3 — Research Debian dependencies

Use the specification's dependency list as the starting point.

For every relevant dependency, determine:

1. whether an official Debian package exists;
2. the exact Debian package name;
3. the installed/available version;
4. whether it is available in Debian 12;
5. whether it is available in Debian 13;
6. whether it is a runtime dependency;
7. whether it is a development dependency;
8. whether it is a packaging dependency;
9. whether it is optional;
10. whether Python's standard library or Qt already provides an adequate alternative.

Do **not** install a large collection of packages merely because they appear in the specification.

First research and classify them.

Create the dependency research document required by the specification:

```text
docs/en/developers/debian-dependencies.md
```

---

### Step 4 — Analyze the architecture

Create:

```text
docs/en/developers/architecture-proposal.md
```

Describe the proposed architecture based on the specification.

Pay particular attention to the separation between:

* domain;
* application/use cases;
* market data;
* exchanges;
* strategies;
* backtesting;
* paper trading;
* risk management;
* execution;
* persistence;
* security;
* GUI;
* education;
* documentation;
* internationalization.

The architecture must prevent strategies from directly communicating with exchanges.

---

### Step 5 — Create the required ADRs

Create the Architecture Decision Records requested by the specification:

```text
ADR-0001 — Architecture
ADR-0002 — Charting
ADR-0003 — Qt and asyncio concurrency
ADR-0004 — Credential storage
ADR-0005 — Packaging backend
ADR-0006 — Internationalization
ADR-0007 — Beginner documentation
```

If the repository already has an ADR convention, follow it.

Otherwise create a clear structure such as:

```text
docs/en/developers/adr/
```

Each ADR must explain:

* context;
* problem;
* considered alternatives;
* decision;
* consequences;
* rejected alternatives.

Do not make arbitrary technology choices without explaining them.

---

### Step 6 — Analyze internationalization

The application must be designed as multilingual **from the beginning**.

The language order is:

1. English — source/default language;
2. Spanish — second language.

Use:

* PyQt6;
* `QTranslator`;
* Qt Linguist;
* `.ts`;
* `.qm`;
* `pylupdate6`;
* `lrelease`.

Do not design the application around Spanish strings and translate them afterward.

The source language must be English.

Create the initial translation infrastructure without unnecessarily implementing the entire GUI yet.

---

### Step 7 — Analyze the educational system

The educational system is a core feature.

The application is not only a trading tool.

It must also teach a complete beginner:

* what money is;
* what cryptocurrency is;
* what Bitcoin is;
* what blockchain is;
* what an exchange is;
* what trading pairs are;
* what orders are;
* what fees are;
* what slippage is;
* what volatility is;
* what technical indicators are;
* what strategies are;
* what backtesting is;
* what paper trading is;
* what risk management is;
* why backtests can be misleading;
* why profits are never guaranteed.

The documentation must be written in English first and later translated into Spanish.

The writing style should be similar to a good **"For Dummies"** educational book:

* friendly;
* patient;
* simple;
* practical;
* step-by-step;
* understandable to someone with zero prior knowledge;
* technically accurate without unnecessary jargon.

Do not postpone this documentation until the end of the project.

---

### Step 8 — Create the first beginner documentation

Create:

```text
docs/en/beginners/00-start-here.md
```

and:

```text
docs/en/beginners/glossary.md
```

Follow the exact requirements in the specification.

Do not invent advanced concepts unnecessarily.

---

### Step 9 — Security analysis

Create:

```text
docs/en/developers/threat-model.md
```

Analyze at minimum:

* API-key theft;
* secrets in logs;
* malicious strategy files;
* malformed CSV files;
* compromised dependencies;
* stale market data;
* duplicate orders;
* accidental real trading;
* excessive API permissions;
* misleading backtests;
* users confusing paper trading with real trading.

---

### Step 10 — Initial project structure

Only after the research above is complete, propose the initial project structure.

Do not create hundreds of empty files simply to reproduce the final architecture.

Create only the minimum foundation needed for the first development iteration.

---

# Very important development rules

Follow these rules throughout the project:

### 1. Do not implement everything at once

The specification explicitly divides the project into phases.

Respect those phases.

### 2. Do not enable real trading

Real-money trading must remain disabled.

The first versions must concentrate on:

* education;
* market data;
* charts;
* backtesting;
* paper trading;
* risk management.

### 3. Never claim profitability

Crypto Trading Lab must never claim that a strategy will make money.

### 4. Do not use real credentials

Never ask for or generate real API keys.

Never put credentials in source code.

### 5. Do not use `eval()` or `exec()`

Strategies must eventually use a safe declarative representation.

### 6. Do not over-install dependencies

Prefer official Debian packages when appropriate.

Prefer the Python standard library when sufficient.

Prefer Qt functionality when it is already appropriate.

### 7. Do not write fake tests

Every test reported as passing must actually have been executed.

### 8. Do not claim that something works if it has not been tested

If something cannot be tested in the current environment, clearly state that.

### 9. Documentation is part of development

When a feature is implemented, its documentation must evolve with it.

### 10. English comes first

All source code, primary documentation, UI source strings, ADRs, and developer documentation should initially be written in English.

Spanish follows through Qt Linguist and translated documentation.

---

# Do not proceed automatically to Phase 1

At the end of this first task, STOP.

Do not begin implementing the full GUI, exchange APIs, trading engine, or real-time trading functionality.

Instead, give me a report containing:

1. repository analysis;
2. current project state;
3. specification file found;
4. Debian version;
5. Python version;
6. Qt/PyQt6 information;
7. relevant Debian packages found;
8. dependency classification;
9. architecture proposal;
10. ADRs created;
11. security analysis;
12. internationalization plan;
13. beginner documentation created;
14. proposed initial project tree;
15. problems or ambiguities discovered;
16. recommended next step.

Then wait for my approval before proceeding to Phase 1.

**Do not assume that silence means approval.**

The goal of this first interaction is to establish a solid technical foundation before writing the actual application.
