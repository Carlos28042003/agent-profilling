from agentic_profiling.metrics import f1_score, grade, last_number, normalize_answer


def test_normalize_answer():
    assert normalize_answer("The  United Kingdom.") == "united kingdom"


def test_hotpotqa_exact_match_and_f1():
    r = grade("the United Kingdom", ["United Kingdom"], "hotpotqa")
    assert r == {"correct": True, "em": 1.0, "f1": 1.0}

    r = grade("London, United Kingdom", ["United Kingdom"], "hotpotqa")
    assert not r["correct"] and r["em"] == 0.0 and 0.7 < r["f1"] < 0.9


def test_hotpotqa_yes_no_must_match_exactly():
    assert f1_score("yes they are", "yes") == 0.0
    assert grade("Yes", ["yes"], "hotpotqa")["correct"]


def test_numeric():
    assert grade("She makes $18 every day.", ["18"], "numeric")["correct"]
    assert grade("1,234", ["1234"], "numeric")["correct"]
    assert not grade("about 17", ["18"], "numeric")["correct"]
    assert last_number("no numbers") is None


def test_missing_answer():
    assert grade(None, ["x"], "hotpotqa") == {"correct": False, "em": 0.0, "f1": 0.0}
    assert not grade(None, ["1"], "numeric")["correct"]


def test_contains_is_the_default():
    assert grade("It was 1889.", ["1889"])["correct"]
