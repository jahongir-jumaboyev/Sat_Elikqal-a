import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "Rus tili" / "main.py"
spec = importlib.util.spec_from_file_location("rus_tili_main", MODULE_PATH)
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)


def test_score_summary() -> None:
    assert main.get_score_summary({"correct": 20, "total": 30}) == "📊 Hisob: 20/30"
    assert main.get_score_summary({"correct": 0, "total": 0}) == "📊 Hisob: 0/0"


def test_record_answer() -> None:
    state = {}
    assert main.record_answer(state, True) == {"correct": 1, "total": 1}
    assert main.record_answer(state, False) == {"correct": 1, "total": 2}
