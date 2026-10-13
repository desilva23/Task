import json

PLUGIN = ["-p", "tests.guards.trace_plugin"]


def run(pytester, source, *args):
    pytester.makepyfile(test_sample=source)
    return pytester.runpytest_inprocess(*PLUGIN, "--collect-only", "-q", *args)


class TestTracePlugin:
    """CONST-III — every test cites a defined ID, or collection fails."""

    def test_an_untraced_test_fails_collection(self, pytester):
        result = run(pytester, "def test_nothing_cited():\n    pass\n")
        assert result.ret != 0
        result.stderr.fnmatch_lines(["*Untraced test: test_sample.py::test_nothing_cited*"])

    def test_the_withdrawn_id_fails_collection(self, pytester):
        result = run(pytester, 'def test_barcode():\n    """FR-03 — barcode."""\n')
        assert result.ret != 0
        result.stderr.fnmatch_lines(["*Unknown ID FR-03 cited by test_sample.py::test_barcode*"])

    def test_an_id_that_was_never_defined_fails_collection(self, pytester):
        result = run(pytester, "def test_ac_99_nothing():\n    pass\n")
        assert result.ret != 0
        result.stderr.fnmatch_lines(["*Unknown ID AC-99*"])

    def test_a_docstring_citation_passes(self, pytester):
        assert run(pytester, 'def test_x():\n    """AC-01, FR-01."""\n').ret == 0

    def test_a_snake_name_citation_passes(self, pytester):
        assert run(pytester, "def test_ac_01_and_const_iv_x():\n    pass\n").ret == 0

    def test_a_class_docstring_covers_its_tests(self, pytester):
        source = 'class TestX:\n    """EC-38."""\n    def test_y(self):\n        pass\n'
        assert run(pytester, source).ret == 0

    def test_a_module_docstring_covers_its_tests(self, pytester):
        source = '"""C-04 — module level."""\n\ndef test_y():\n    pass\n'
        assert run(pytester, source).ret == 0

    def test_the_report_lists_each_function_once_with_its_ids(self, pytester, tmp_path):
        report = tmp_path / "report.json"
        source = (
            "import pytest\n"
            "@pytest.mark.parametrize('n', [1, 2, 3])\n"
            'def test_v_01_rows(n):\n    """W-02 too."""\n'
        )
        assert run(pytester, source, f"--trace-report={report}").ret == 0
        assert json.loads(report.read_text()) == {
            "test_sample.py::test_v_01_rows": ["V-01", "W-02"]
        }
