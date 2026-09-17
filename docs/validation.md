# Validation record

Validated on 17 September 2026 using Python 3.9.6 and Node.js 24.18.0.

- Python evaluation: 28/28 deterministic fixture cases passed.
- Python unittest suite: 17/17 tests passed, including localhost HTTP integration.
- All four cases were executed through the browser and returned their expected decisions. No browser console errors or warnings were observed in that run.
- Desktop layout and a 390px iframe layout were visually checked. The 390px document had no horizontal overflow. This is a responsive-layout check, not a physical-device test.
- Offline JavaScript unit verification checked all four decisions, 12 exports, four exported Python regression files executed against the engine, exact agreement between the embedded data and data/demo.json, and HTML escaping of hostile metadata. This uses a DOM stub; it is not a file-protocol browser test.
- The self-contained HTML has no external script or stylesheet dependencies. The in-app browser disallowed direct file-protocol navigation, so direct opening from disk was not browser-tested in this environment.
- The one-page PDF was rendered and visually inspected after its final wording changes.

Reproduce the automated checks from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 -m repairdesk evaluate
node scripts/verify_web.mjs
```

Node is needed only for the optional web verification script. Python alone runs the application. The checks establish behavior on the included fixtures; they do not estimate production accuracy or throughput.

## Register redesign

The revised interface embeds its four open-source font faces and the redesigned PDF brief. The offline verification script passed again after the visual revision. Vercel serves the checked-in `web/` directory with no dependency installation or build step.
