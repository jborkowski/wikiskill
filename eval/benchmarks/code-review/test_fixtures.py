"""Verify the seven seeded obligations and the clean control without model scoring."""

from __future__ import annotations

import unittest

from build_fixtures import CASES


def namespace(case: str, revision: str = "after") -> dict:
    source = next(item[revision] for item in CASES if item["name"] == case)
    result = {}
    # Execute only the checked-in, self-contained synthetic fixture strings.
    exec(compile(source, f"{case}/{revision}/app.py", "exec"), result)  # noqa: S102
    return result


class FixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.refund = namespace("spec-and-standards")["refund"]
        self.order = {"owner_id": "owner", "customer_id": "customer", "total": 10}

    def test_missing_authorization(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO

        with redirect_stdout(StringIO()):
            self.assertEqual(self.refund(self.order, "other", 5), 5)

    def test_invalid_bounds(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO

        with redirect_stdout(StringIO()):
            for amount in (0, 11):
                self.assertEqual(self.refund(self.order, "owner", amount), amount)

    def test_sentinel_instead_of_exception(self) -> None:
        self.assertIsNone(self.refund(self.order, "owner", -1))

    def test_customer_disclosure(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO

        output = StringIO()
        with redirect_stdout(output):
            self.refund(self.order, "owner", 5)
        self.assertEqual(output.getvalue(), "customer\n")

    def test_positional_regression(self) -> None:
        before = namespace("context-and-scope", "before")["connect"]
        after = namespace("context-and-scope")["connect"]
        self.assertEqual(before("endpoint", "token")["token"], "token")
        with self.assertRaises(TypeError):
            after("endpoint", "token")

    def test_validation_order(self) -> None:
        context = namespace("context-and-scope")
        calls = []
        context["open_connection"] = lambda *args: calls.append(args)
        with self.assertRaises(ValueError):
            context["connect"]("endpoint", timeout=0, token="token")  # noqa: S106 — dummy
        self.assertEqual(calls, [("endpoint", "token")])

    def test_mean_regression(self) -> None:
        before = namespace("no-spec-correctness", "before")["average"]
        after = namespace("no-spec-correctness")["average"]
        self.assertEqual(before([2, 4]), 3)
        self.assertEqual(after([2, 4]), 6)
        self.assertEqual(before([5]), 5)
        with self.assertRaises(ZeroDivisionError):
            after([5])

    def test_clean_control(self) -> None:
        convert = namespace("clean-with-overrides")["convert"]
        for amount in (0, 3):
            self.assertEqual(convert(amount, "USD"), amount)
            self.assertEqual(convert(amount, "EUR"), amount * 2)
        with self.assertRaises(ValueError):
            convert(1, "GBP")


if __name__ == "__main__":
    unittest.main()
