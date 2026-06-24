"""Pruebas de la lógica de negocio (§6.10)."""
from server.logic import delta, format_value, resolve_variant, to_num


def test_to_num_basic():
    assert to_num("reps", "12") == 12.0
    assert to_num("cm", "45,5") == 45.5
    assert to_num("seg", "  30 ") == 30.0


def test_to_num_empty_and_invalid():
    assert to_num("reps", "") is None
    assert to_num("reps", None) is None
    assert to_num("reps", "abc") is None


def test_to_num_mmss():
    assert to_num("mm:ss", "3:05") == 185.0
    assert to_num("mm:ss", "2:30") == 150.0
    assert to_num("mm:ss", "90") == 90.0  # segundos sueltos


def test_delta_high_improvement():
    d = delta("high", "reps", "15", "12")
    assert d == {"value": 3.0, "improved": True}


def test_delta_low_improvement_is_decrease():
    # En 'low' (tiempo), bajar es mejora.
    d = delta("low", "mm:ss", "3:00", "3:10")
    assert d["value"] == -10.0
    assert d["improved"] is True


def test_delta_low_worse_when_increase():
    d = delta("low", "mm:ss", "3:20", "3:10")
    assert d["improved"] is False


def test_delta_zero_and_none():
    assert delta("high", "reps", "10", "10") == {"value": 0, "improved": None}
    assert delta("high", "reps", "", "10") is None


def test_resolve_variant():
    variants = {
        "A": {"text": "A txt", "media": ""},
        "B": {"text": "B txt", "media": ""},
        "C": {"text": "C txt", "media": ""},
    }
    assert resolve_variant(variants, "A") == "A txt"
    assert resolve_variant(variants, "C") == "C txt"
    assert resolve_variant(variants, "Z") == ""  # nivel sin variante → vacío


def test_format_value():
    assert format_value("reps", "12") == "12"
    assert format_value("cm", "45") == "45 cm"
    assert format_value("mm:ss", "3:05") == "3:05"
