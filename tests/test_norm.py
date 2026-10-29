import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import _norm


def test_norm_basic():
    assert _norm("Hello") == "hello"
    assert _norm(None) == ""
    assert _norm("") == ""


def test_norm_diacritics():
    assert _norm("Ștefan") == "stefan"
    assert _norm("Țara") == "tara"
    assert _norm("Cătălin") == "catalin"


def test_norm_case_and_spaces():
    assert _norm("  Foo  Bar ") == "  foo  bar "
    assert "artrita" in _norm("Artrită reumatoidă")
