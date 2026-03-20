"""
Tests for dictionary.py — 100 tests covering apply(), add_word(),
remove_word(), get_dictionary(), and import_dictionary().
"""
import pytest
from unittest.mock import patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dictionary

# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply(mappings: dict, text: str) -> str:
    with patch("dictionary._read", return_value=mappings):
        return dictionary.apply(text)

def _add(store: dict, frm: str, to: str) -> dict:
    with patch("dictionary._read", return_value=dict(store)), \
         patch("dictionary._write") as w:
        dictionary.add_word(frm, to)
        return w.call_args[0][0]

def _remove(store: dict, frm: str) -> dict:
    with patch("dictionary._read", return_value=dict(store)), \
         patch("dictionary._write") as w:
        dictionary.remove_word(frm)
        return w.call_args[0][0]

def _import(store: dict, entries: dict) -> dict:
    with patch("dictionary._read", return_value=dict(store)), \
         patch("dictionary._write") as w:
        dictionary.import_dictionary(entries)
        return w.call_args[0][0]

# ── apply() — basic replacements (1–20) ──────────────────────────────────────

class TestApplyBasic:
    def test_01_single_word_replaced(self):
        assert _apply({"hello": "hi"}, "hello world") == "hi world"

    def test_02_multiple_occurrences_all_replaced(self):
        assert _apply({"cat": "dog"}, "cat and cat") == "dog and dog"

    def test_03_no_match_unchanged(self):
        assert _apply({"cat": "dog"}, "I love fish") == "I love fish"

    def test_04_empty_text_returns_empty(self):
        assert _apply({"cat": "dog"}, "") == ""

    def test_05_empty_dict_unchanged(self):
        assert _apply({}, "hello world") == "hello world"

    def test_06_both_empty(self):
        assert _apply({}, "") == ""

    def test_07_case_insensitive_uppercase_input(self):
        assert _apply({"hello": "hi"}, "HELLO world") == "hi world"

    def test_08_case_insensitive_mixed_case(self):
        assert _apply({"hello": "hi"}, "Hello World") == "hi World"

    def test_09_replace_with_longer_word(self):
        assert _apply({"hi": "hello there"}, "say hi now") == "say hello there now"

    def test_10_replace_with_shorter_word(self):
        assert _apply({"hello": "hi"}, "say hello now") == "say hi now"

    def test_11_multiple_mappings_applied(self):
        result = _apply({"cat": "dog", "fish": "bird"}, "cat and fish")
        assert "dog" in result and "bird" in result

    def test_12_replacement_at_start_of_text(self):
        assert _apply({"hello": "hi"}, "hello world").startswith("hi")

    def test_13_replacement_at_end_of_text(self):
        assert _apply({"world": "earth"}, "hello world").endswith("earth")

    def test_14_replacement_in_middle(self):
        assert _apply({"big": "large"}, "a big dog") == "a large dog"

    def test_15_multi_word_key(self):
        assert _apply({"new york": "NYC"}, "I love new york") == "I love NYC"

    def test_16_number_key_replaced(self):
        assert _apply({"1": "one"}, "I have 1 cat") == "I have one cat"

    def test_17_replacement_adjacent_to_punctuation(self):
        assert "hi," in _apply({"hello": "hi"}, "hello, world")

    def test_18_entire_text_is_the_key(self):
        assert _apply({"hello": "goodbye"}, "hello") == "goodbye"

    def test_19_empty_value_removes_word(self):
        result = _apply({"um": ""}, "um hello um")
        assert "um" not in result

    def test_20_key_and_value_identical(self):
        assert _apply({"hello": "hello"}, "hello world") == "hello world"

# ── apply() — case sensitivity (21–35) ───────────────────────────────────────

class TestApplyCaseSensitivity:
    def test_21_all_uppercase_input_matched(self):
        assert _apply({"hello": "hi"}, "HELLO") == "hi"

    def test_22_titlecase_input_matched(self):
        assert _apply({"world": "earth"}, "World") == "earth"

    def test_23_replacement_value_case_preserved(self):
        assert _apply({"hi": "HELLO"}, "say hi") == "say HELLO"

    def test_24_repeated_word_all_cases_replaced(self):
        result = _apply({"cat": "dog"}, "CAT cat Cat")
        assert result.count("dog") == 3

    def test_25_mixed_case_key_matches_lowercase(self):
        assert _apply({"CaT": "dog"}, "cat is here") == "dog is here"

    def test_26_single_char_key_case_insensitive(self):
        assert _apply({"a": "x"}, "A B C") == "x B C"

    def test_27_newline_in_text_preserved(self):
        assert _apply({"hello": "hi"}, "hello\nworld") == "hi\nworld"

    def test_28_tab_in_text_preserved(self):
        assert _apply({"hello": "hi"}, "hello\tworld") == "hi\tworld"

    def test_29_multiple_spaces_preserved(self):
        assert _apply({"hello": "hi"}, "hello  world") == "hi  world"

    def test_30_unicode_key_case(self):
        result = _apply({"café": "coffee"}, "CAFÉ time")
        assert isinstance(result, str)

    def test_31_numbers_unaffected_by_case(self):
        assert _apply({"123": "NUM"}, "value is 123") == "value is NUM"

    def test_32_non_matched_text_unchanged(self):
        result = _apply({"cat": "dog"}, "The Cat sat")
        assert "The" in result and "sat" in result

    def test_33_key_uppercase_matches_lowercase_input(self):
        assert _apply({"Hello": "Hi"}, "hello there") == "Hi there"

    def test_34_replacement_does_not_affect_unrelated_words(self):
        result = _apply({"the": "a"}, "the cat sat on the mat")
        assert "cat" in result and "sat" in result and "on" in result

    def test_35_mixed_case_both_key_and_value(self):
        result = _apply({"FooBar": "bazQux"}, "foobar")
        assert "bazQux" in result

# ── apply() — special characters (36–50) ─────────────────────────────────────

class TestApplySpecialChars:
    def test_36_dot_in_key_escaped(self):
        assert "for example" in _apply({"e.g.": "for example"}, "e.g. this works")

    def test_37_parentheses_in_key(self):
        assert "okay" in _apply({"(ok)": "okay"}, "reply (ok) now")

    def test_38_plus_in_key(self):
        assert "cpp" in _apply({"c++": "cpp"}, "I code in c++")

    def test_39_asterisk_in_key(self):
        assert "AB" in _apply({"a*b": "AB"}, "result a*b done")

    def test_40_question_mark_in_key(self):
        assert "huh" in _apply({"what?": "huh"}, "say what? now")

    def test_41_square_brackets_in_key(self):
        assert "TEST" in _apply({"[test]": "TEST"}, "run [test] case")

    def test_42_curly_braces_in_key(self):
        assert "Alice" in _apply({"{name}": "Alice"}, "hello {name}")

    def test_43_pipe_in_key(self):
        assert "or" in _apply({"a|b": "or"}, "choose a|b")

    def test_44_backslash_in_key(self):
        result = _apply({"path\\file": "file"}, "open path\\file now")
        assert "file" in result

    def test_45_replacement_contains_special_chars(self):
        assert "hello (there)" in _apply({"hi": "hello (there)"}, "say hi")

    def test_46_very_long_key(self):
        key = "a" * 100
        assert "replaced" in _apply({key: "replaced"}, f"start {key} end")

    def test_47_very_long_value(self):
        val = "b" * 200
        assert val in _apply({"x": val}, "say x now")

    def test_48_emoji_in_text_preserved(self):
        assert _apply({"hello": "hi"}, "hello 😊") == "hi 😊"

    def test_49_emoji_as_key(self):
        assert "smile" in _apply({"😊": "smile"}, "I am 😊")

    def test_50_only_whitespace_text(self):
        assert _apply({"a": "b"}, "   ") == "   "

# ── apply() — multiple mappings (51–60) ──────────────────────────────────────

class TestApplyMultipleMappings:
    def test_51_three_mappings_all_applied(self):
        result = _apply({"a": "1", "b": "2", "c": "3"}, "a b c")
        assert "1" in result and "2" in result and "3" in result

    def test_52_ten_mappings(self):
        m = {chr(ord('a') + i): str(i) for i in range(10)}
        text = " ".join(chr(ord('a') + i) for i in range(10))
        result = _apply(m, text)
        for i in range(10):
            assert str(i) in result

    def test_53_same_word_twice_both_replaced(self):
        assert _apply({"go": "run"}, "go and go") == "run and run"

    def test_54_key_not_partial_of_longer_key(self):
        result = _apply({"cats": "dogs"}, "cat sat")
        assert result == "cat sat"

    def test_55_multi_word_key_replaced(self):
        assert "a dog" in _apply({"the cat": "a dog"}, "the cat sat")

    def test_56_empty_value_in_multi_mapping(self):
        result = _apply({"um": "", "uh": ""}, "um hello uh world")
        assert "um" not in result and "uh" not in result

    def test_57_replace_does_not_affect_other_keys(self):
        result = _apply({"cat": "dog", "bat": "ball"}, "cat and bat")
        assert "dog" in result and "ball" in result

    def test_58_replacement_returns_string(self):
        assert isinstance(_apply({"a": "b", "c": "d"}, "a c"), str)

    def test_59_fifty_mappings_all_applied(self):
        m = {f"word{i}": f"rep{i}" for i in range(50)}
        text = " ".join(f"word{i}" for i in range(50))
        result = _apply(m, text)
        for i in range(50):
            assert f"rep{i}" in result

    def test_60_no_mapping_matches_text_unchanged(self):
        text = "completely unrelated text"
        assert _apply({"xyz": "abc"}, text) == text

# ── add_word() (61–70) ────────────────────────────────────────────────────────

class TestAddWord:
    def test_61_add_to_empty_dict(self):
        assert _add({}, "hello", "hi") == {"hello": "hi"}

    def test_62_add_to_existing_dict(self):
        result = _add({"a": "b"}, "c", "d")
        assert result["c"] == "d"

    def test_63_overwrite_existing_key(self):
        assert _add({"a": "old"}, "a", "new")["a"] == "new"

    def test_64_preserves_existing_entries(self):
        result = _add({"x": "y"}, "a", "b")
        assert result["x"] == "y"

    def test_65_add_empty_value(self):
        assert _add({}, "um", "")["um"] == ""

    def test_66_add_unicode_key(self):
        assert _add({}, "café", "coffee")["café"] == "coffee"

    def test_67_add_numeric_key(self):
        assert _add({}, "1", "one")["1"] == "one"

    def test_68_add_long_key(self):
        key = "x" * 50
        assert _add({}, key, "val")[key] == "val"

    def test_69_add_calls_write_once(self):
        with patch("dictionary._read", return_value={}), \
             patch("dictionary._write") as w:
            dictionary.add_word("a", "b")
            w.assert_called_once()

    def test_70_sequential_adds_accumulate(self):
        store = _add({}, "a", "1")
        store = _add(store, "b", "2")
        assert store.get("a") == "1" and store.get("b") == "2"

# ── remove_word() (71–80) ─────────────────────────────────────────────────────

class TestRemoveWord:
    def test_71_remove_existing_key(self):
        assert "a" not in _remove({"a": "b"}, "a")

    def test_72_remove_nonexistent_no_error(self):
        assert _remove({"a": "b"}, "z") == {"a": "b"}

    def test_73_remove_from_empty_dict(self):
        assert _remove({}, "a") == {}

    def test_74_remove_one_of_many(self):
        result = _remove({"a": "1", "b": "2", "c": "3"}, "b")
        assert "b" not in result and "a" in result and "c" in result

    def test_75_remove_calls_write_once(self):
        with patch("dictionary._read", return_value={"a": "b"}), \
             patch("dictionary._write") as w:
            dictionary.remove_word("a")
            w.assert_called_once()

    def test_76_remove_unicode_key(self):
        assert "café" not in _remove({"café": "coffee"}, "café")

    def test_77_remove_leaves_others_intact(self):
        assert _remove({"a": "1", "b": "2"}, "a") == {"b": "2"}

    def test_78_remove_last_entry_leaves_empty(self):
        assert _remove({"a": "b"}, "a") == {}

    def test_79_remove_key_with_special_chars(self):
        assert "c++" not in _remove({"c++": "cpp"}, "c++")

    def test_80_double_remove_same_key_is_safe(self):
        store = _remove({"a": "b"}, "a")
        store = _remove(store, "a")
        assert store == {}

# ── get_dictionary() (81–88) ──────────────────────────────────────────────────

class TestGetDictionary:
    def test_81_returns_empty_dict_when_no_file(self):
        with patch("dictionary._read", return_value={}):
            assert dictionary.get_dictionary() == {}

    def test_82_returns_populated_dict(self):
        d = {"a": "b", "c": "d"}
        with patch("dictionary._read", return_value=d):
            assert dictionary.get_dictionary() == d

    def test_83_return_type_is_dict(self):
        with patch("dictionary._read", return_value={}):
            assert isinstance(dictionary.get_dictionary(), dict)

    def test_84_returns_unicode_entries(self):
        with patch("dictionary._read", return_value={"café": "coffee"}):
            assert dictionary.get_dictionary()["café"] == "coffee"

    def test_85_returns_all_entries(self):
        d = {str(i): str(i * 2) for i in range(10)}
        with patch("dictionary._read", return_value=d):
            assert dictionary.get_dictionary() == d

    def test_86_does_not_write(self):
        with patch("dictionary._read", return_value={}), \
             patch("dictionary._write") as w:
            dictionary.get_dictionary()
            w.assert_not_called()

    def test_87_returns_exact_values(self):
        with patch("dictionary._read", return_value={"key": "value with spaces"}):
            assert dictionary.get_dictionary()["key"] == "value with spaces"

    def test_88_large_dictionary_returned(self):
        d = {f"word{i}": f"rep{i}" for i in range(50)}
        with patch("dictionary._read", return_value=d):
            assert len(dictionary.get_dictionary()) == 50

# ── import_dictionary() (89–95) ───────────────────────────────────────────────

class TestImportDictionary:
    def test_89_import_into_empty_dict(self):
        assert _import({}, {"a": "b", "c": "d"}) == {"a": "b", "c": "d"}

    def test_90_import_merges_with_existing(self):
        result = _import({"x": "y"}, {"a": "b"})
        assert result == {"x": "y", "a": "b"}

    def test_91_import_overwrites_existing_key(self):
        assert _import({"a": "old"}, {"a": "new"})["a"] == "new"

    def test_92_import_empty_entries_unchanged(self):
        assert _import({"a": "b"}, {}) == {"a": "b"}

    def test_93_import_calls_write_once(self):
        with patch("dictionary._read", return_value={}), \
             patch("dictionary._write") as w:
            dictionary.import_dictionary({"a": "b"})
            w.assert_called_once()

    def test_94_import_unicode_entries(self):
        result = _import({}, {"café": "coffee", "naïve": "naive"})
        assert result["café"] == "coffee"

    def test_95_import_large_batch(self):
        entries = {f"k{i}": f"v{i}" for i in range(30)}
        assert len(_import({}, entries)) == 30

# ── integration (96–100) ──────────────────────────────────────────────────────

class TestIntegration:
    def test_96_add_then_apply(self):
        store = _add({}, "hello", "hi")
        assert "hi" in _apply(store, "say hello")

    def test_97_add_remove_then_apply_no_replacement(self):
        store = _add({}, "hello", "hi")
        store = _remove(store, "hello")
        assert _apply(store, "say hello") == "say hello"

    def test_98_import_then_apply(self):
        store = _import({}, {"cat": "dog", "fish": "bird"})
        result = _apply(store, "cat and fish")
        assert "dog" in result and "bird" in result

    def test_99_add_multiple_then_apply_all(self):
        store = {}
        for i in range(5):
            store = _add(store, f"word{i}", f"rep{i}")
        text = " ".join(f"word{i}" for i in range(5))
        result = _apply(store, text)
        for i in range(5):
            assert f"rep{i}" in result

    def test_100_empty_replacement_strips_word_from_text(self):
        result = _apply({"um": ""}, "um hello um world")
        assert "um" not in result
        assert "hello" in result and "world" in result
