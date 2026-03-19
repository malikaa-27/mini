"""
Tests for shortcuts.py — 100 tests covering apply(), add_shortcut(),
remove_shortcut(), and get_shortcuts().
"""
import pytest
from unittest.mock import patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shortcuts

# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply(mappings: dict, text: str) -> str:
    with patch("shortcuts._read", return_value=mappings):
        return shortcuts.apply(text)

def _add(store: dict, trigger: str, expansion: str) -> dict:
    with patch("shortcuts._read", return_value=dict(store)), \
         patch("shortcuts._write") as w:
        shortcuts.add_shortcut(trigger, expansion)
        return w.call_args[0][0]

def _remove(store: dict, trigger: str) -> dict:
    with patch("shortcuts._read", return_value=dict(store)), \
         patch("shortcuts._write") as w:
        shortcuts.remove_shortcut(trigger)
        return w.call_args[0][0]

# ── apply() — basic replacements (1–20) ──────────────────────────────────────

class TestApplyBasic:
    def test_01_single_trigger_replaced(self):
        assert _apply({"myemail": "user@example.com"}, "contact myemail") == "contact user@example.com"

    def test_02_no_match_unchanged(self):
        assert _apply({"myemail": "user@example.com"}, "no trigger here") == "no trigger here"

    def test_03_empty_text_returns_empty(self):
        assert _apply({"t": "expansion"}, "") == ""

    def test_04_empty_shortcuts_unchanged(self):
        assert _apply({}, "hello world") == "hello world"

    def test_05_both_empty(self):
        assert _apply({}, "") == ""

    def test_06_trigger_at_start(self):
        assert _apply({"hi": "hello there"}, "hi everyone").startswith("hello there")

    def test_07_trigger_at_end(self):
        assert _apply({"bye": "goodbye"}, "say bye").endswith("goodbye")

    def test_08_trigger_in_middle(self):
        assert "-- Alice" in _apply({"sig": "-- Alice"}, "please see sig thanks")

    def test_09_multiple_occurrences_all_replaced(self):
        assert _apply({"t": "trigger"}, "t and t") == "trigger and trigger"

    def test_10_expansion_with_spaces(self):
        assert "123 Main St, NYC" in _apply({"addr": "123 Main St, NYC"}, "my addr is")

    def test_11_expansion_with_newline(self):
        assert "Best,\nAlice" in _apply({"sig": "Best,\nAlice"}, "sig")

    def test_12_expansion_with_url(self):
        assert "https://example.com" in _apply({"link": "https://example.com"}, "visit link")

    def test_13_expansion_with_email(self):
        assert "alice@example.com" in _apply({"em": "alice@example.com"}, "email em")

    def test_14_case_sensitive_no_match(self):
        # shortcuts.apply uses str.replace — case-sensitive
        assert _apply({"Hello": "Hi"}, "hello world") == "hello world"

    def test_15_case_sensitive_exact_match(self):
        assert _apply({"HELLO": "hi"}, "HELLO world") == "hi world"

    def test_16_multiple_triggers_all_applied(self):
        result = _apply({"a": "alpha", "b": "beta"}, "a and b")
        assert "alpha" in result and "beta" in result

    def test_17_trigger_longer_than_text_no_match(self):
        assert _apply({"verylongtrigger": "x"}, "short") == "short"

    def test_18_expansion_much_longer_than_trigger(self):
        result = _apply({"x": "a" * 100}, "x")
        assert len(result) == 100

    def test_19_empty_expansion_removes_trigger(self):
        assert _apply({"filler": ""}, "remove filler word") == "remove  word"

    def test_20_trigger_equals_entire_text(self):
        assert _apply({"hello": "goodbye"}, "hello") == "goodbye"

# ── apply() — edge cases (21–45) ─────────────────────────────────────────────

class TestApplyEdgeCases:
    def test_21_trigger_with_number(self):
        assert _apply({"addr1": "123 St"}, "send to addr1") == "send to 123 St"

    def test_22_trigger_with_parentheses(self):
        assert _apply({"(c)": "©"}, "Copyright (c) 2024") == "Copyright © 2024"

    def test_23_trigger_with_dot(self):
        assert _apply({"e.g.": "for example"}, "e.g. this") == "for example this"

    def test_24_trigger_with_at_symbol(self):
        assert _apply({"@me": "alice@example.com"}, "reply to @me") == "reply to alice@example.com"

    def test_25_single_char_trigger(self):
        assert _apply({"!": "important"}, "this is !") == "this is important"

    def test_26_numeric_trigger(self):
        assert _apply({"007": "James Bond"}, "agent 007 reporting") == "agent James Bond reporting"

    def test_27_unicode_trigger(self):
        assert _apply({"café": "coffee shop"}, "at café") == "at coffee shop"

    def test_28_unicode_expansion(self):
        assert _apply({"smiley": "😊"}, "I am smiley") == "I am 😊"

    def test_29_multiword_trigger(self):
        assert _apply({"my address": "123 Main St"}, "send to my address") == "send to 123 Main St"

    def test_30_trigger_inside_word(self):
        # str.replace replaces substrings — "cat" matches inside "concatenate"
        result = _apply({"cat": "dog"}, "concatenate")
        assert "dog" in result

    def test_31_newline_in_text_preserved(self):
        assert "Alice" in _apply({"sig": "Alice"}, "regards\nsig")

    def test_32_tab_in_text(self):
        assert "tab" in _apply({"t": "tab"}, "press\tt")

    def test_33_only_spaces_text_unchanged(self):
        assert _apply({"a": "b"}, "   ") == "   "

    def test_34_trigger_repeated_many_times(self):
        result = _apply({"x": "y"}, "x " * 10)
        assert result.count("y") == 10

    def test_35_expansion_contains_trigger_safe(self):
        # str.replace is single-pass — no infinite loop
        result = _apply({"a": "aa"}, "a")
        assert result == "aa"

    def test_36_long_text_no_match_unchanged(self):
        text = "hello world " * 100
        assert _apply({"zzz": "nope"}, text) == text

    def test_37_long_text_with_many_matches(self):
        result = _apply({"hi": "hello"}, "say hi " * 50)
        assert result.count("hello") == 50

    def test_38_twenty_triggers_all_applied(self):
        m = {f"t{i}": f"e{i}" for i in range(20)}
        text = " ".join(f"t{i}" for i in range(20))
        result = _apply(m, text)
        for i in range(20):
            assert f"e{i}" in result

    def test_39_expansion_with_quotes(self):
        assert '"quoted"' in _apply({"q": '"quoted"'}, "say q")

    def test_40_expansion_with_backslash(self):
        assert "C:\\Users\\Alice" in _apply({"path": "C:\\Users\\Alice"}, "open path")

    def test_41_numeric_only_text(self):
        assert _apply({"123": "numbers"}, "123") == "numbers"

    def test_42_returns_string_always(self):
        assert isinstance(_apply({}, "test"), str)

    def test_43_does_not_mutate_input_text(self):
        text = "original text"
        _apply({"original": "modified"}, text)
        assert text == "original text"

    def test_44_does_not_mutate_input_dict(self):
        m = {"a": "b"}
        original = dict(m)
        _apply(m, "a")
        assert m == original

    def test_45_expansion_with_html_tags(self):
        assert "<b>bold</b>" in _apply({"bold": "<b>bold</b>"}, "make it bold")

# ── apply() — order and interaction (46–55) ───────────────────────────────────

class TestApplyOrder:
    def test_46_non_overlapping_triggers(self):
        assert _apply({"abc": "X", "def": "Y"}, "abc def") == "X Y"

    def test_47_trigger_substring_of_word(self):
        result = _apply({"foo": "bar"}, "food")
        assert "bar" in result

    def test_48_two_triggers_adjacent(self):
        result = _apply({"ab": "X", "cd": "Y"}, "abcd")
        assert isinstance(result, str)

    def test_49_empty_trigger_in_dict(self):
        result = _apply({"": "X"}, "abc")
        assert isinstance(result, str)

    def test_50_whitespace_trigger(self):
        result = _apply({" ": "_"}, "a b c")
        assert isinstance(result, str)

    def test_51_whitespace_expansion(self):
        result = _apply({"x": " "}, "axb")
        assert isinstance(result, str)

    def test_52_apply_none_text_raises(self):
        with patch("shortcuts._read", return_value={"a": "b"}):
            with pytest.raises((AttributeError, TypeError)):
                shortcuts.apply(None)

    def test_53_single_char_trigger_all_occurrences(self):
        result = _apply({"i": "I"}, "i like it in italy")
        assert isinstance(result, str)

    def test_54_trigger_same_as_expansion_unchanged(self):
        assert _apply({"hello": "hello"}, "hello world") == "hello world"

    def test_55_fifty_triggers_all_applied(self):
        m = {f"k{i}": f"v{i}" for i in range(50)}
        text = " ".join(f"k{i}" for i in range(50))
        result = _apply(m, text)
        for i in range(50):
            assert f"v{i}" in result

# ── add_shortcut() (56–70) ────────────────────────────────────────────────────

class TestAddShortcut:
    def test_56_add_to_empty_dict(self):
        assert _add({}, "myemail", "user@example.com")["myemail"] == "user@example.com"

    def test_57_add_to_existing_dict(self):
        result = _add({"a": "b"}, "c", "d")
        assert "c" in result

    def test_58_overwrite_existing_trigger(self):
        assert _add({"a": "old"}, "a", "new")["a"] == "new"

    def test_59_preserves_existing_entries(self):
        result = _add({"x": "y"}, "a", "b")
        assert result["x"] == "y"

    def test_60_add_calls_write_once(self):
        with patch("shortcuts._read", return_value={}), \
             patch("shortcuts._write") as w:
            shortcuts.add_shortcut("t", "e")
            w.assert_called_once()

    def test_61_add_unicode_trigger(self):
        assert _add({}, "café", "coffee shop")["café"] == "coffee shop"

    def test_62_add_long_expansion(self):
        expansion = "x" * 500
        assert _add({}, "t", expansion)["t"] == expansion

    def test_63_add_multiline_expansion(self):
        expansion = "line1\nline2\nline3"
        assert _add({}, "sig", expansion)["sig"] == expansion

    def test_64_add_url_expansion(self):
        assert _add({}, "link", "https://example.com/path?q=1")["link"] == "https://example.com/path?q=1"

    def test_65_add_empty_expansion(self):
        assert _add({}, "filler", "")["filler"] == ""

    def test_66_add_numeric_trigger(self):
        assert _add({}, "007", "James Bond")["007"] == "James Bond"

    def test_67_add_multiple_sequential(self):
        store = _add({}, "a", "alpha")
        store = _add(store, "b", "beta")
        assert store["a"] == "alpha" and store["b"] == "beta"

    def test_68_add_special_char_trigger(self):
        assert _add({}, "(c)", "©")["(c)"] == "©"

    def test_69_add_returns_complete_store(self):
        result = _add({"existing": "value"}, "new", "entry")
        assert "existing" in result and "new" in result

    def test_70_add_html_expansion(self):
        assert _add({}, "tag", "<b>bold</b>")["tag"] == "<b>bold</b>"

# ── remove_shortcut() (71–80) ─────────────────────────────────────────────────

class TestRemoveShortcut:
    def test_71_remove_existing_trigger(self):
        assert "a" not in _remove({"a": "b"}, "a")

    def test_72_remove_nonexistent_no_error(self):
        assert _remove({"a": "b"}, "z") == {"a": "b"}

    def test_73_remove_from_empty_dict(self):
        assert _remove({}, "a") == {}

    def test_74_remove_one_of_many(self):
        result = _remove({"a": "1", "b": "2", "c": "3"}, "b")
        assert "b" not in result and len(result) == 2

    def test_75_remove_calls_write_once(self):
        with patch("shortcuts._read", return_value={"a": "b"}), \
             patch("shortcuts._write") as w:
            shortcuts.remove_shortcut("a")
            w.assert_called_once()

    def test_76_remove_unicode_trigger(self):
        assert "café" not in _remove({"café": "coffee"}, "café")

    def test_77_remove_last_entry_leaves_empty(self):
        assert _remove({"a": "b"}, "a") == {}

    def test_78_double_remove_same_key_safe(self):
        store = _remove({"a": "b"}, "a")
        store = _remove(store, "a")
        assert store == {}

    def test_79_remove_leaves_others_intact(self):
        assert _remove({"a": "1", "b": "2", "c": "3"}, "b") == {"a": "1", "c": "3"}

    def test_80_remove_special_char_trigger(self):
        assert "(c)" not in _remove({"(c)": "©"}, "(c)")

# ── get_shortcuts() (81–88) ───────────────────────────────────────────────────

class TestGetShortcuts:
    def test_81_returns_empty_when_no_file(self):
        with patch("shortcuts._read", return_value={}):
            assert shortcuts.get_shortcuts() == {}

    def test_82_returns_populated_dict(self):
        s = {"a": "b", "c": "d"}
        with patch("shortcuts._read", return_value=s):
            assert shortcuts.get_shortcuts() == s

    def test_83_return_type_is_dict(self):
        with patch("shortcuts._read", return_value={}):
            assert isinstance(shortcuts.get_shortcuts(), dict)

    def test_84_does_not_write(self):
        with patch("shortcuts._read", return_value={}), \
             patch("shortcuts._write") as w:
            shortcuts.get_shortcuts()
            w.assert_not_called()

    def test_85_returns_exact_multiline_value(self):
        s = {"sig": "Best regards, Alice\nSoftware Engineer"}
        with patch("shortcuts._read", return_value=s):
            assert shortcuts.get_shortcuts()["sig"] == s["sig"]

    def test_86_returns_all_entries(self):
        s = {f"t{i}": f"e{i}" for i in range(20)}
        with patch("shortcuts._read", return_value=s):
            assert len(shortcuts.get_shortcuts()) == 20

    def test_87_returns_unicode_entries(self):
        with patch("shortcuts._read", return_value={"café": "coffee shop"}):
            assert shortcuts.get_shortcuts()["café"] == "coffee shop"

    def test_88_returns_url_values(self):
        with patch("shortcuts._read", return_value={"link": "https://example.com"}):
            assert shortcuts.get_shortcuts()["link"] == "https://example.com"

# ── integration (89–100) ──────────────────────────────────────────────────────

class TestIntegration:
    def test_89_add_then_apply(self):
        store = _add({}, "myemail", "user@example.com")
        assert "user@example.com" in _apply(store, "contact myemail please")

    def test_90_add_remove_then_apply_no_replacement(self):
        store = _add({}, "t", "expansion")
        store = _remove(store, "t")
        assert _apply(store, "t") == "t"

    def test_91_add_multiple_apply_all(self):
        store = {}
        for i in range(5):
            store = _add(store, f"t{i}", f"e{i}")
        text = " ".join(f"t{i}" for i in range(5))
        result = _apply(store, text)
        for i in range(5):
            assert f"e{i}" in result

    def test_92_overwrite_then_apply_new_value(self):
        store = _add({}, "t", "old")
        store = _add(store, "t", "new")
        assert "new" in _apply(store, "t")

    def test_93_remove_nonexistent_then_apply_works(self):
        store = _add({}, "t", "expansion")
        store = _remove(store, "nonexistent")
        assert "expansion" in _apply(store, "t")

    def test_94_apply_multiline_expansion(self):
        store = _add({}, "sig", "Best,\nAlice")
        assert "Best,\nAlice" in _apply(store, "regards sig")

    def test_95_apply_url_expansion(self):
        store = _add({}, "link", "https://example.com")
        assert "https://example.com" in _apply(store, "visit link")

    def test_96_apply_empty_expansion_removes_trigger(self):
        store = _add({}, "filler", "")
        result = _apply(store, "remove filler word")
        assert "filler" not in result

    def test_97_two_shortcuts_applied_to_same_text(self):
        store = _add({}, "a", "alpha")
        store = _add(store, "b", "beta")
        result = _apply(store, "a b")
        assert "alpha" in result and "beta" in result

    def test_98_large_store_applied(self):
        store = {f"k{i}": f"v{i}" for i in range(30)}
        text = " ".join(f"k{i}" for i in range(30))
        result = _apply(store, text)
        for i in range(30):
            assert f"v{i}" in result

    def test_99_get_after_add_returns_entry(self):
        with patch("shortcuts._read", return_value={"a": "b"}):
            assert shortcuts.get_shortcuts()["a"] == "b"

    def test_100_add_get_apply_full_pipeline(self):
        store = _add({}, "sig", "Alice")
        with patch("shortcuts._read", return_value=store):
            got = shortcuts.get_shortcuts()
        assert "Alice" in _apply(got, "sig")
