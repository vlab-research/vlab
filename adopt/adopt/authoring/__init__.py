"""Study authoring: composable primitives for building a study configuration.

Five modules, and they are primitives rather than a pipeline (plan §6.D):

* `strata`   the dashboard's compiler -- variables to strata, and the
             staleness hint. A helper, not the blessed way.
* `extract`  targeting properties off a template Meta ad set.
* `validate` the whole-study check `POST /{org}/studies/{slug}/validate` wraps.
* `sheets`   a workbook tab to a conf, and a census tab to per-level quotas.
* `geo`      radius targeting from latitude/longitude rows.

The last two are salvaged from the notebook era (`adopt/configuration.py`,
superseded) and are the reason the compiler is *a* helper: they build strata
the dashboard's Variables form cannot express at all, and a caller may combine
them, bypass all of them, or hand-write strata -- `validate` checks the result
either way.

WHAT FOLLOWS IS ABOUT `strata` AND `extract` SPECIFICALLY.


Phase 1 of `planning/agent-study-authoring.md` §8. Until this package existed
the only code that could turn `variables` into `strata` — or pull
`facebook_targeting` off a template ad set — was browser TypeScript
(`dashboard/src/pages/StudyConfPage/forms/strata/strata.ts` and
`.../variables/extract.ts`), reachable from a React component and nowhere
else. An agent or a notebook had to reimplement it, and the older Python
ancestor (`adopt/configuration.py`) had already drifted from it.

The modules here are ports, not reimplementations: each TypeScript test is
translated into the matching `test_*.py`, and `test_conformance.py` replays a
fixture set produced by running the real TypeScript
(`dashboard/scripts/authoring-conformance.ts`) and asserts the Python output is
identical. Regenerate the fixtures with `make -C adopt authoring-fixtures`
whenever the TypeScript changes.

Everything works on the JSON wire shape — plain dicts and lists, exactly what
`POST /{org}/studies/{slug}/confs/strata` accepts — rather than on the
pydantic models. The TypeScript is untyped at these boundaries (`any`), and
the conformance suite compares against its literal output; passing the data
through `StratumConf` would coerce (`metadata: Dict[str, str]`) or drop
(`extra="ignore"`, §11.4 of the plan) things the TypeScript passes through
untouched, and the two would stop agreeing. Validation is a separate step,
and stays one: build a `StratumConf` from the result when you want it checked.
"""
