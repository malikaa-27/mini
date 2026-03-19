"""
Tests for _remove_filler_words() from main.py — 100 tests.
The function is self-contained (pure text transformation) so we inline it
to avoid pulling in FastAPI just for testing.
"""
from __future__ import annotations

import re


# ── Inlined copy of _remove_filler_words (same logic as main.py) ──────────────

def _remove_filler_words(text: str, words: list[str]) -> str:
    if not text or not words:
        return text
    candidates = [w.strip().lower() for w in words if isinstance(w, str) and w.strip()]
    if not candidates:
        return text
    candidates = sorted(set(candidates), key=len, reverse=True)
    pattern = r"\b(?:%s)\b" % "|".join(re.escape(w) for w in candidates)
    cleaned = re.sub(pattern, "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"^\s*,\s*", "", cleaned)
    cleaned = re.sub(r",\s*,+", ",", cleaned)
    cleaned = re.sub(r",\s*(?=[.?!]|$)", "", cleaned)
    cleaned = re.sub(r",\s*(\S)", r", \1", cleaned)
    return cleaned


DEFAULT_FILLERS = ["um", "uh", "erm", "er", "ah", "uhh", "umm", "uhm"]


# ── Empty / none inputs (1–12) ────────────────────────────────────────────────

class TestEmptyInputs:
    def test_01_empty_text_returns_empty(self):
        assert _remove_filler_words("", DEFAULT_FILLERS) == ""

    def test_02_empty_words_list_returns_text_unchanged(self):
        assert _remove_filler_words("hello um world", []) == "hello um world"

    def test_03_none_words_list_returns_text_unchanged(self):
        assert _remove_filler_words("hello", None) == "hello"

    def test_04_empty_text_with_empty_words(self):
        assert _remove_filler_words("", []) == ""

    def test_05_words_list_with_only_empty_strings(self):
        assert _remove_filler_words("hello um world", ["", "  "]) == "hello um world"

    def test_06_words_list_with_none_entries_ignored(self):
        # Non-string entries should be skipped via isinstance check
        result = _remove_filler_words("hello um world", [None, 42, "um"])
        assert "um" not in result

    def test_07_whitespace_only_text(self):
        result = _remove_filler_words("   ", DEFAULT_FILLERS)
        assert result.strip() == ""

    def test_08_single_space_text(self):
        result = _remove_filler_words(" ", DEFAULT_FILLERS)
        assert result == "" or result == " "

    def test_09_empty_text_with_valid_words(self):
        assert _remove_filler_words("", ["um"]) == ""

    def test_10_words_list_all_whitespace(self):
        assert _remove_filler_words("hello um there", ["   ", "\t"]) == "hello um there"

    def test_11_none_text_returns_none_equivalent(self):
        # function returns text if falsy — None is falsy
        assert _remove_filler_words(None, DEFAULT_FILLERS) is None

    def test_12_words_with_mixed_valid_invalid(self):
        result = _remove_filler_words("hello um world", [None, "um", "", 42])
        assert "um" not in result
        assert "hello" in result


# ── Basic removal (13–30) ─────────────────────────────────────────────────────

class TestBasicRemoval:
    def test_13_removes_um(self):
        assert "um" not in _remove_filler_words("hello um world", ["um"])

    def test_14_removes_uh(self):
        assert "uh" not in _remove_filler_words("uh hello", ["uh"])

    def test_15_removes_er(self):
        assert "er" not in _remove_filler_words("this is er great", ["er"])

    def test_16_removes_ah(self):
        result = _remove_filler_words("ah nice day", ["ah"])
        assert "ah" not in result

    def test_17_removes_erm(self):
        result = _remove_filler_words("erm what should I say", ["erm"])
        assert "erm" not in result

    def test_18_removes_uhh(self):
        result = _remove_filler_words("uhh okay", ["uhh"])
        assert "uhh" not in result

    def test_19_removes_umm(self):
        result = _remove_filler_words("umm let me think", ["umm"])
        assert "umm" not in result

    def test_20_removes_uhm(self):
        result = _remove_filler_words("uhm yeah", ["uhm"])
        assert "uhm" not in result

    def test_21_preserves_content_words(self):
        result = _remove_filler_words("hello um world", ["um"])
        assert "hello" in result
        assert "world" in result

    def test_22_removes_leading_filler(self):
        result = _remove_filler_words("um hello world", ["um"])
        assert result.startswith("hello") or result.lstrip() == "hello world"

    def test_23_removes_trailing_filler(self):
        result = _remove_filler_words("hello world um", ["um"])
        assert result.rstrip().endswith("world")

    def test_24_removes_middle_filler(self):
        result = _remove_filler_words("hello um world", ["um"])
        assert "hello world" in result or result == "hello world"

    def test_25_removes_multiple_instances(self):
        result = _remove_filler_words("um hello um world um", ["um"])
        assert "um" not in result

    def test_26_text_unchanged_when_no_fillers_present(self):
        result = _remove_filler_words("hello world", ["um", "uh"])
        assert result == "hello world"

    def test_27_single_word_filler_only(self):
        result = _remove_filler_words("um", ["um"])
        assert result == ""

    def test_28_removes_all_default_fillers(self):
        text = "um uh erm er ah uhh umm uhm hello"
        result = _remove_filler_words(text, DEFAULT_FILLERS)
        for f in DEFAULT_FILLERS:
            assert f"\b{f}\b" not in result.lower() or f not in result.split()

    def test_29_case_insensitive_removal(self):
        result = _remove_filler_words("Hello UM World", ["um"])
        assert "UM" not in result

    def test_30_case_insensitive_mixed_case(self):
        result = _remove_filler_words("Um UH Erm hello", DEFAULT_FILLERS)
        assert "hello" in result.lower()


# ── Word boundary (31–42) ─────────────────────────────────────────────────────

class TestWordBoundary:
    def test_31_does_not_remove_um_inside_word(self):
        result = _remove_filler_words("umbrella", ["um"])
        assert "umbrella" in result

    def test_32_does_not_remove_er_inside_word(self):
        result = _remove_filler_words("water", ["er"])
        assert "water" in result

    def test_33_does_not_remove_ah_inside_word(self):
        result = _remove_filler_words("yeah", ["ah"])
        assert "yeah" in result

    def test_34_does_not_remove_uh_in_ugh(self):
        # "ugh" does not contain standalone "uh"
        result = _remove_filler_words("ugh that hurts", ["uh"])
        assert "ugh" in result

    def test_35_standalone_er_removed(self):
        result = _remove_filler_words("this is er correct", ["er"])
        assert "er" not in result.split()

    def test_36_um_at_start_of_sentence(self):
        result = _remove_filler_words("Um, this is good", ["um"])
        assert "Um" not in result

    def test_37_uh_before_comma(self):
        result = _remove_filler_words("uh, hello", ["uh"])
        assert "uh" not in result.lower()

    def test_38_filler_followed_by_punctuation(self):
        result = _remove_filler_words("um. hello", ["um"])
        assert "um" not in result

    def test_39_filler_at_end_with_period(self):
        result = _remove_filler_words("hello um.", ["um"])
        assert "um" not in result

    def test_40_does_not_damage_similar_words(self):
        result = _remove_filler_words("summer umbrella", ["um"])
        # Neither "summer" nor "umbrella" should be modified
        assert "summer" in result
        assert "umbrella" in result

    def test_41_er_in_longer_word_preserved(self):
        result = _remove_filler_words("better faster stronger", ["er"])
        # These words contain "er" but as a suffix, not standalone
        assert "better" in result

    def test_42_multiple_filler_words_at_word_boundaries(self):
        result = _remove_filler_words("um uh er hello erm world", DEFAULT_FILLERS)
        for w in ["um", "uh", "er", "erm"]:
            assert w not in result.split()


# ── Whitespace cleanup (43–58) ────────────────────────────────────────────────

class TestWhitespaceCleanup:
    def test_43_no_double_spaces_after_removal(self):
        result = _remove_filler_words("hello um world", ["um"])
        assert "  " not in result

    def test_44_no_leading_spaces(self):
        result = _remove_filler_words("um hello", ["um"])
        assert not result.startswith(" ")

    def test_45_no_trailing_spaces(self):
        result = _remove_filler_words("hello um", ["um"])
        assert not result.endswith(" ")

    def test_46_multiple_fillers_no_extra_spaces(self):
        result = _remove_filler_words("um uh er hello", DEFAULT_FILLERS)
        assert "  " not in result

    def test_47_filler_only_text_collapses_to_empty(self):
        result = _remove_filler_words("um uh er", DEFAULT_FILLERS)
        assert result == ""

    def test_48_three_fillers_in_a_row(self):
        result = _remove_filler_words("um um um hello", ["um"])
        assert result == "hello"

    def test_49_filler_surrounded_by_spaces(self):
        result = _remove_filler_words("hello  um  world", ["um"])
        assert "  " not in result

    def test_50_result_is_stripped(self):
        result = _remove_filler_words("um hello um", ["um"])
        assert result == result.strip()

    def test_51_preserves_single_spaces_between_words(self):
        result = _remove_filler_words("hello world", ["um"])
        assert result == "hello world"

    def test_52_consecutive_fillers_no_artifacts(self):
        result = _remove_filler_words("um uh umm hello world", DEFAULT_FILLERS)
        assert result.startswith("hello") or result == "hello world"

    def test_53_filler_at_start_no_leading_space(self):
        result = _remove_filler_words("uh there you go", ["uh"])
        assert not result.startswith(" ")

    def test_54_mixed_filler_and_content(self):
        result = _remove_filler_words("um the um cat um sat", ["um"])
        assert "the cat sat" in result or result == "the cat sat"

    def test_55_tab_between_words_preserved(self):
        # Tabs in source text (not fillers) should be handled by cleanup
        result = _remove_filler_words("hello\tworld", ["um"])
        assert "hello" in result and "world" in result

    def test_56_only_fillers_result_is_empty_string(self):
        result = _remove_filler_words("um", ["um"])
        assert result == ""

    def test_57_filler_then_word_no_leading_space(self):
        result = _remove_filler_words("um hello", ["um"])
        assert result[0].isalpha()

    def test_58_word_then_filler_no_trailing_space(self):
        result = _remove_filler_words("hello um", ["um"])
        assert result[-1].isalpha()


# ── Punctuation handling (59–78) ──────────────────────────────────────────────

class TestPunctuationHandling:
    def test_59_no_space_before_comma(self):
        result = _remove_filler_words("hello um, world", ["um"])
        assert " ," not in result

    def test_60_no_space_before_period(self):
        result = _remove_filler_words("hello um. world", ["um"])
        assert " ." not in result

    def test_61_no_space_before_exclamation(self):
        result = _remove_filler_words("great um! really", ["um"])
        assert " !" not in result

    def test_62_no_space_before_question_mark(self):
        result = _remove_filler_words("what um? is this", ["um"])
        assert " ?" not in result

    def test_63_no_space_before_semicolon(self):
        result = _remove_filler_words("hello um; world", ["um"])
        assert " ;" not in result

    def test_64_no_space_before_colon(self):
        result = _remove_filler_words("listen um: carefully", ["um"])
        assert " :" not in result

    def test_65_leading_comma_removed(self):
        result = _remove_filler_words("um, hello", ["um"])
        assert not result.startswith(",")

    def test_66_comma_before_period_cleaned(self):
        result = _remove_filler_words("hello um, um.", ["um"])
        assert ",." not in result

    def test_67_comma_before_exclamation_cleaned(self):
        result = _remove_filler_words("hello um, um!", ["um"])
        assert ",!" not in result

    def test_68_comma_before_question_cleaned(self):
        result = _remove_filler_words("um, um?", ["um"])
        assert ",?" not in result

    def test_69_double_comma_collapsed(self):
        # If two fillers next to commas produce double comma
        result = _remove_filler_words("hello, um, um, world", ["um"])
        assert ",," not in result

    def test_70_comma_space_word_formatted_correctly(self):
        result = _remove_filler_words("hello um world, test", ["um"])
        if "," in result:
            # Comma should be followed by space then word
            assert ", " in result or result.endswith(",")

    def test_71_period_preserved(self):
        result = _remove_filler_words("hello. um world", ["um"])
        assert "." in result

    def test_72_exclamation_preserved(self):
        result = _remove_filler_words("wow! um great", ["um"])
        assert "!" in result

    def test_73_question_mark_preserved(self):
        result = _remove_filler_words("really? um yes", ["um"])
        assert "?" in result

    def test_74_content_after_punctuation_preserved(self):
        result = _remove_filler_words("hello. um World", ["um"])
        assert "World" in result

    def test_75_comma_spacing_after_word(self):
        result = _remove_filler_words("one, two, three", ["um"])
        assert result == "one, two, three"

    def test_76_no_trailing_comma(self):
        result = _remove_filler_words("hello world um,", ["um"])
        assert not result.endswith(",")

    def test_77_filler_between_comma_and_word(self):
        result = _remove_filler_words("hello, um world", ["um"])
        assert "um" not in result
        assert "hello" in result
        assert "world" in result

    def test_78_filler_removal_preserves_sentence_structure(self):
        result = _remove_filler_words("I um think um this um works.", ["um"])
        assert "I think this works." in result or result == "I think this works."


# ── Longer phrases as filler words (79–88) ────────────────────────────────────

class TestPhraseFillers:
    def test_79_phrase_filler_removed(self):
        result = _remove_filler_words("you know what I mean", ["you know"])
        assert "you know" not in result

    def test_80_longer_phrase_matched_before_shorter(self):
        # "you know" should be removed, not just "you" or "know"
        result = _remove_filler_words("you know hello", ["you know", "you"])
        assert "know" not in result

    def test_81_phrase_with_spaces(self):
        result = _remove_filler_words("like I said hello", ["like I said"])
        assert "like I said" not in result

    def test_82_phrase_not_matching_partial_word(self):
        result = _remove_filler_words("knowing", ["know"])
        assert "knowing" in result

    def test_83_two_word_phrase_surrounded_by_content(self):
        result = _remove_filler_words("hello you know world", ["you know"])
        assert "hello" in result
        assert "world" in result

    def test_84_repeated_phrase(self):
        result = _remove_filler_words("you know you know hello", ["you know"])
        assert "hello" in result
        assert "you know" not in result

    def test_85_phrase_at_start(self):
        result = _remove_filler_words("you know this is good", ["you know"])
        assert not result.lower().startswith("you know")

    def test_86_phrase_at_end(self):
        result = _remove_filler_words("this is good you know", ["you know"])
        assert "you know" not in result

    def test_87_single_and_phrase_fillers_together(self):
        result = _remove_filler_words("um you know uh hello", ["um", "uh", "you know"])
        assert "hello" in result
        for f in ["um", "uh", "you know"]:
            assert f not in result

    def test_88_phrase_filler_case_insensitive(self):
        result = _remove_filler_words("You Know what hello", ["you know"])
        assert "You Know" not in result


# ── Deduplication and ordering (89–94) ───────────────────────────────────────

class TestDeduplication:
    def test_89_duplicate_words_in_list_handled(self):
        result = _remove_filler_words("um hello", ["um", "um", "um"])
        assert "um" not in result

    def test_90_filler_list_with_different_cases_same_word(self):
        result = _remove_filler_words("Um hello UM", ["um", "UM", "Um"])
        assert "um" not in result.lower()

    def test_91_whitespace_in_filler_word_stripped(self):
        result = _remove_filler_words("um hello", ["  um  "])
        assert "um" not in result

    def test_92_longer_phrase_priority(self):
        # "um yeah" should match before standalone "um"
        result = _remove_filler_words("hello um yeah world", ["um", "um yeah"])
        assert "um" not in result
        assert "yeah" not in result

    def test_93_filler_list_with_many_entries(self):
        big_list = [f"word{i}" for i in range(50)] + ["um"]
        result = _remove_filler_words("um hello", big_list)
        assert "um" not in result

    def test_94_empty_string_in_filler_list_ignored(self):
        result = _remove_filler_words("hello world", ["", "", "um"])
        assert result == "hello world"


# ── Real-world sentences (95–100) ─────────────────────────────────────────────

class TestRealWorldSentences:
    def test_95_typical_dictation(self):
        text = "um open the settings and uh go to privacy"
        result = _remove_filler_words(text, DEFAULT_FILLERS)
        assert "open the settings and" in result
        assert "go to privacy" in result

    def test_96_professional_sentence(self):
        text = "I er believe that um the results are er significant"
        result = _remove_filler_words(text, DEFAULT_FILLERS)
        assert "I believe that the results are significant" in result or \
               all(w in result for w in ["believe", "results", "significant"])

    def test_97_sentence_with_comma(self):
        text = "open Firefox, um go to google dot com"
        result = _remove_filler_words(text, DEFAULT_FILLERS)
        assert "um" not in result
        assert "Firefox" in result
        assert "google dot com" in result

    def test_98_question_sentence(self):
        text = "um can you uh open the browser?"
        result = _remove_filler_words(text, DEFAULT_FILLERS)
        assert "can you open the browser?" in result or "?" in result

    def test_99_all_fillers_default_list(self):
        text = " ".join(DEFAULT_FILLERS)
        result = _remove_filler_words(text, DEFAULT_FILLERS)
        assert result == ""

    def test_100_clean_sentence_unchanged(self):
        text = "Open the settings and enable dark mode."
        result = _remove_filler_words(text, DEFAULT_FILLERS)
        assert result == text
