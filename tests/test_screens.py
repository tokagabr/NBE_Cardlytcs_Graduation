"""
End-to-end screen test.

Runs the real Streamlit app headlessly with AppTest and visits every screen
under the combinations that matter for the demo:

    a) reference dataset          b) new merchant scenario
    c) V1                         d) V2
    e) normal filters             f) narrow and empty filter cases

The assertion on every run is simply that the script finished without an
uncaught exception, plus targeted checks that the things that must appear
actually appear (new-merchant badges, the insufficient-merchants warning, the
empty-filter warning).

This is the test that would have caught a KeyError on stage, so it runs the
app for real rather than importing its functions.

Run: python tests/test_screens.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(ROOT / "app.py")
TIMEOUT = 240
failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {label}{(' — ' + detail) if detail else ''}")
    if not condition:
        failures.append(label)


def exception_text(at: AppTest) -> str:
    return " | ".join(e.value for e in at.exception)


def load(dataset: str) -> AppTest:
    """Start the app and load one of the two demo datasets."""
    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    if at.exception:
        raise AssertionError(f"app failed on first render: {exception_text(at)}")
    # Demo picker is the only radio on the Load screen besides navigation.
    demo_radio = [r for r in at.radio if "Demo dataset" in (r.label or "")]
    if dataset == "new" and demo_radio:
        demo_radio[0].set_value("New merchant scenario").run()
    at.button[0].click().run()
    if at.exception:
        raise AssertionError(f"loading {dataset} failed: {exception_text(at)}")
    return at


def goto(at: AppTest, screen_prefix: str) -> AppTest:
    nav = at.radio(key="nav")
    target = next(o for o in nav.options if o.startswith(screen_prefix))
    nav.set_value(target).run()
    return at


def set_version(at: AppTest, version: str) -> AppTest:
    selector = [r for r in at.radio if r.key == "methodology_label"]
    if selector:
        selector[0].set_value("V1 Baseline" if version == "v1" else "V2 Enhanced").run()
    return at


SCREENS = ["1", "2", "3", "4", "5", "6", "7"]


def walk_all_screens(dataset: str, version: str) -> None:
    print(f"\n--- dataset={dataset}  version={version} ---")
    at = load(dataset)
    for prefix in SCREENS:
        at = goto(at, prefix)
        if prefix in ("5", "6", "7"):
            at = set_version(at, version)
        label = next(o for o in at.radio(key="nav").options if o.startswith(prefix))
        check(f"{dataset}/{version} · {label.strip()}", not at.exception,
              exception_text(at))


def new_merchant_surfacing() -> None:
    print("\n--- new merchants surface on every screen that should show them ---")
    at = load("new")

    at = goto(at, "2")
    body = " ".join(m.value for m in at.markdown)
    check("Data Quality names the new merchants",
          all(name in body for name in ("NOOR ELECTRONICS", "SHIFA PHARMACY",
                                        "BARAKA TRADING")))
    check("Unknown category shown honestly, not hidden", "Unknown" in body)

    at = goto(at, "5")
    body = " ".join(m.value for m in at.markdown)
    check("Clustering shows the new badge", "badge-new" in body)
    check("Clustering lists new merchants", "NOOR ELECTRONICS" in body)

    at = goto(at, "6")
    check("Rankings render with new merchants present", not at.exception,
          exception_text(at))


def filter_cases() -> None:
    print("\n--- filter cases ---")
    at = load("reference")
    at = goto(at, "3")

    # e) a normal filter
    category = next(m for m in at.multiselect if m.label == "Category")
    options = list(category.options)
    category.set_value(options[:2]).run()
    check("normal filter: Executive survives", not at.exception, exception_text(at))

    at = goto(at, "5")
    check("normal filter: Clustering survives", not at.exception, exception_text(at))

    # f) narrow filter: fewer merchants than clusters
    category.set_value([]).run()
    merchant = next(m for m in at.multiselect if m.label == "Merchant")
    merchant.set_value(list(merchant.options)[:2]).run()
    at = goto(at, "5")
    warnings = " ".join(w.value for w in at.warning)
    check("narrow filter: clustering warns instead of crashing",
          not at.exception and "merchant(s) in the current filter view" in warnings,
          exception_text(at) or warnings[:90])

    at = goto(at, "6")
    warnings = " ".join(w.value for w in at.warning)
    check("narrow filter: rankings warn instead of crashing",
          not at.exception and "merchant" in warnings.lower(),
          exception_text(at) or warnings[:90])

    # f) empty filter: a combination that genuinely matches no rows.
    # Each merchant carries exactly one category, so pairing a merchant with a
    # different merchant's category is guaranteed to select nothing.
    merchant = next(m for m in at.multiselect if m.label == "Merchant")
    merchant.set_value([]).run()
    at = goto(at, "3")

    clean_df = at.session_state["clean_df"]
    pairs = clean_df[["merchant", "category"]].drop_duplicates()
    first = pairs.iloc[0]
    other = pairs[pairs["category"] != first["category"]].iloc[0]

    merchant = next(m for m in at.multiselect if m.label == "Merchant")
    merchant.set_value([first["merchant"]]).run()
    category = next(m for m in at.multiselect if m.label == "Category")
    category.set_value([other["category"]]).run()

    warnings = " ".join(w.value for w in at.warning)
    check("empty filter: app warns and stops cleanly",
          not at.exception and "No transactions match" in warnings,
          exception_text(at) or warnings[:90])


def unloaded_screens() -> None:
    print("\n--- screens opened before any dataset is loaded ---")
    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    for prefix in SCREENS[1:]:
        at = goto(at, prefix)
        label = next(o for o in at.radio(key="nav").options if o.startswith(prefix))
        info = " ".join(i.value for i in at.info)
        check(f"unloaded · {label.strip()} guards cleanly",
              not at.exception and "Load a dataset" in info,
              exception_text(at))


if __name__ == "__main__":
    unloaded_screens()
    for dataset in ("reference", "new"):
        for version in ("v1", "v2"):
            walk_all_screens(dataset, version)
    new_merchant_surfacing()
    filter_cases()

    print("\n" + "=" * 68)
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED:")
        for item in failures:
            print(f"  - {item}")
        sys.exit(1)
    print("ALL SCREEN CHECKS PASSED")
