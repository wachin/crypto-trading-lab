---
name: Bug report
about: Something behaves incorrectly. A reproducible command is worth a thousand words.
title: "[bug] "
labels: ["bug"]
---

## What happened

<!-- One or two sentences. -->

## Exact command and real output

```bash
# the command you ran
```

```text
# the real output — paste it verbatim, do not summarise
```

## What you expected instead

## Environment

- Debian / Ubuntu version: (`cat /etc/os-release | head -2`)
- Python version: (`python3 --version`)
- Running offscreen? (`echo $QT_QPA_PLATFORM`)
- Test baseline you observe: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q`

## Where you think it lives

<!-- File, module or ROADMAP chapter that owns this behaviour, if you know. -->

## Anything else
