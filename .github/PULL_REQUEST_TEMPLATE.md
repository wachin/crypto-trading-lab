# Pull request

## What this changes

<!-- One or two sentences. What behaviour changes, and why. -->

## Which requirement does it implement?

<!-- A ROADMAP chapter/item, a bug, or a documentation gap. -->

- Chapter / item: `ROADMAP.md` §
- Related issue: #

## Type of change

- [ ] Feature (implements a ROADMAP requirement)
- [ ] Bug fix
- [ ] Documentation
- [ ] Tests only
- [ ] Translation (i18n)
- [ ] Refactor (no behaviour change)

## Verification (required — paste the real output)

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q
# paste the last lines here, verbatim
```

Before this change: `___ passed, ___ skipped`
After this change: `___ passed, ___ skipped`

If the count differs from the documented baseline
(**522 passed, 2 skipped**), explain why.

## Checklist

- [ ] The change is small and focused on one requirement.
- [ ] New behaviour has a test that fails without this change.
- [ ] Documentation was updated in this same change.
- [ ] Visible UI strings are wrapped in `self.tr()`.
- [ ] I did **not** install any dependency (`apt`, `pip`, `venv`).
- [ ] Real trading is still disabled and no strategy bypasses the risk
      manager.
- [ ] I only claim what I actually ran; output above is real.
- [ ] If this completes a ROADMAP item, I ticked it `[x]`.

## Honest notes / known limitations

<!-- Anything that is approximate, untested, or deliberately left out. -->
