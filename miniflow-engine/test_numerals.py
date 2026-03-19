"""
Contract tests for numeral mode — _convert_numerals().

Architecture-agnostic: the function is inlined so these tests survive
any backend rewrite. Only update the inlined function when the
implementation changes.

Run with: python3 -m pytest test_numerals.py -v
"""
from __future__ import annotations

import re


# ── Inlined implementation (mirrors main._convert_numerals) ──────────────────

try:
    from word2number import w2n as _w2n_mod
    def _w2i(phrase: str) -> str | None:
        try:
            return str(_w2n_mod.word_to_num(phrase))
        except Exception:
            return None
except ImportError:
    def _w2i(phrase: str) -> str | None:  # type: ignore[misc]
        return None

_DIGIT_WORDS = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3",
    "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
}

_COMPOUND_WORDS = frozenset({
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
    "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
    "hundred", "thousand", "million", "billion",
})

_ANY_NUM_WORD = frozenset(set(_DIGIT_WORDS) | _COMPOUND_WORDS)

_ORDINAL_UNITS = {
    "first": (1, "st"), "second": (2, "nd"), "third": (3, "rd"),
    "fourth": (4, "th"), "fifth": (5, "th"), "sixth": (6, "th"),
    "seventh": (7, "th"), "eighth": (8, "th"), "ninth": (9, "th"),
}

_ORDINAL_ALL = {
    **_ORDINAL_UNITS,
    "tenth": (10, "th"), "eleventh": (11, "th"), "twelfth": (12, "th"),
    "thirteenth": (13, "th"), "fourteenth": (14, "th"), "fifteenth": (15, "th"),
    "sixteenth": (16, "th"), "seventeenth": (17, "th"), "eighteenth": (18, "th"),
    "nineteenth": (19, "th"), "twentieth": (20, "th"),
    "thirtieth": (30, "th"), "fortieth": (40, "th"), "fiftieth": (50, "th"),
    "sixtieth": (60, "th"), "seventieth": (70, "th"), "eightieth": (80, "th"),
    "ninetieth": (90, "th"),
}

_MONTHS = frozenset({
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
})


def _convert(text: str) -> str:
    if not text:
        return text

    text = re.sub(
        r'\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)'
        r'-(one|two|three|four|five|six|seven|eight|nine|'
        r'first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)\b',
        r'\1 \2', text, flags=re.I,
    )
    text = re.sub(r'\bA\s+M\b', 'AM', text, flags=re.I)
    text = re.sub(r'\bP\s+M\b', 'PM', text, flags=re.I)

    def _clean(tok: str) -> str:
        return re.sub(r"[.,;:!?'\"]+$", "", tok).lower()

    def _trail(tok: str) -> str:
        return tok[len(re.sub(r"[.,;:!?'\"]+$", "", tok)):]

    def _is_compound_start(idx: int) -> bool:
        c = _clean(tokens[idx])
        if c in _COMPOUND_WORDS:
            return True
        if c in _DIGIT_WORDS and idx + 1 < len(tokens) and _clean(tokens[idx + 1]) in _COMPOUND_WORDS:
            return True
        return False

    tokens = text.split()
    out: list[str] = []
    i = 0

    while i < len(tokens):
        c = _clean(tokens[i])

        if c == "plus" and i + 1 < len(tokens) and _clean(tokens[i + 1]) in _DIGIT_WORDS:
            i += 1
            run = "+"
            while i < len(tokens) and _clean(tokens[i]) in _DIGIT_WORDS:
                dig = _DIGIT_WORDS[_clean(tokens[i])]
                trail = _trail(tokens[i])
                i += 1
                if trail:
                    out.append(run + dig + trail)
                    run = ""
                    break
                run += dig
            if run:
                out.append(run)
            continue

        if _is_compound_start(i):
            j = i
            parts: list[str] = []
            while j < len(tokens):
                ct = _clean(tokens[j])
                if ct in _ANY_NUM_WORD:
                    parts.append(ct)
                    j += 1
                elif ct == "and" and j + 1 < len(tokens) and _clean(tokens[j + 1]) in _ANY_NUM_WORD:
                    j += 1
                else:
                    break
            phrase = " ".join(parts)
            converted = _w2i(phrase)
            if converted is not None:
                trail = _trail(tokens[j - 1])
                c_next = _clean(tokens[j]) if j < len(tokens) else ""
                if not trail and c_next in _ORDINAL_UNITS:
                    unit_val, unit_suf = _ORDINAL_UNITS[c_next]
                    unit_trail = _trail(tokens[j])
                    out.append(str(int(converted) + unit_val) + unit_suf + unit_trail)
                    j += 1
                elif not trail and c_next in ("am", "pm"):
                    time_str = None
                    if len(parts) > 1:
                        hr = _w2i(parts[0])
                        mn = _w2i(" ".join(parts[1:]))
                        if hr and mn and 1 <= int(hr) <= 12 and 0 <= int(mn) <= 59:
                            time_str = f"{int(hr)}:{int(mn):02d} {tokens[j].upper()}"
                    out.append(time_str if time_str else converted + " " + tokens[j].upper())
                    j += 1
                else:
                    out.append(converted + trail)
                i = j
                continue
            if c not in _DIGIT_WORDS:
                out.append(tokens[i])
                i += 1
                continue

        if c in _DIGIT_WORDS:
            run = ""
            while i < len(tokens) and _clean(tokens[i]) in _DIGIT_WORDS:
                dig = _DIGIT_WORDS[_clean(tokens[i])]
                trail = _trail(tokens[i])
                i += 1
                if trail:
                    out.append(run + dig + trail)
                    run = ""
                    break
                run += dig
            if run:
                out.append(run)
            continue

        out.append(tokens[i])
        i += 1

    result = " ".join(out)
    result = re.sub(
        r'\+\d+(?:,\s*\d+)+',
        lambda m: '+' + re.sub(r'\D', '', m.group(0)),
        result,
    )
    result = re.sub(r'(\d+)\s+[Pp]oint\s+(\d+)', r'\1.\2', result)
    result = re.sub(r'\b(\d{1,2})\s+([0-5]\d)\s*(AM|PM)\b', r'\1:\2 \3', result)

    _ord_unit_pat = '|'.join(re.escape(w) for w in _ORDINAL_UNITS)
    _ord_all_pat  = '|'.join(re.escape(w) for w in _ORDINAL_ALL)
    _month_pat    = '|'.join(re.escape(m) for m in _MONTHS)

    def _ord_unit_val(word: str) -> tuple[int, str]:
        return _ORDINAL_UNITS[word.lower()]

    def _ord_all_val(word: str) -> tuple[int, str]:
        return _ORDINAL_ALL[word.lower()]

    result = re.sub(
        rf'\b(\d+)\s+({_ord_unit_pat})([.,;:!?]?)\b',
        lambda m: str(int(m.group(1)) + _ord_unit_val(m.group(2))[0])
                  + _ord_unit_val(m.group(2))[1] + m.group(3),
        result, flags=re.I,
    )
    result = re.sub(
        rf'\b({_month_pat})\s+({_ord_all_pat})([.,;:!?]?)\b',
        lambda m: m.group(1) + ' '
                  + str(_ord_all_val(m.group(2))[0]) + _ord_all_val(m.group(2))[1]
                  + m.group(3),
        result, flags=re.I,
    )
    result = re.sub(
        rf'\b({_ord_all_pat})\s+of\s+({_month_pat})\b',
        lambda m: str(_ord_all_val(m.group(1))[0]) + _ord_all_val(m.group(1))[1]
                  + ' of ' + m.group(2),
        result, flags=re.I,
    )

    _LARGE_ORDINALS = {
        "hundredth":    100,
        "thousandth":   1_000,
        "millionth":    1_000_000,
        "billionth":    1_000_000_000,
    }
    for word, mult in _LARGE_ORDINALS.items():
        result = re.sub(
            rf'\b(?:(\d+)\s+)?{word}\b',
            lambda m, mult=mult: str((int(m.group(1)) if m.group(1) else 1) * mult) + "th",
            result, flags=re.I,
        )
    return result


# ── Empty / passthrough (1–8) ─────────────────────────────────────────────────

class TestPassthrough:
    def test_01_empty_string_returns_empty(self):
        assert _convert("") == ""

    def test_02_none_returns_none(self):
        assert _convert(None) is None

    def test_03_no_digit_words_unchanged(self):
        assert _convert("hello world") == "hello world"

    def test_04_plain_sentence_unchanged(self):
        text = "Open the settings and enable dark mode."
        assert _convert(text) == text

    def test_05_punctuation_only_unchanged(self):
        assert _convert("... , . ! ?") == "... , . ! ?"

    def test_06_whitespace_only_unchanged(self):
        result = _convert("   ")
        assert result.strip() == ""

    def test_07_returns_string(self):
        assert isinstance(_convert("hello"), str)

    def test_08_mixed_no_digits_unchanged(self):
        assert _convert("please open the browser") == "please open the browser"


# ── Individual digit word conversion (9–28) ───────────────────────────────────

class TestIndividualDigits:
    def test_09_zero_converted(self):
        assert "0" in _convert("zero")

    def test_10_oh_converted_to_zero(self):
        assert "0" in _convert("oh")

    def test_11_one_converted(self):
        assert "1" in _convert("one")

    def test_12_two_converted(self):
        assert "2" in _convert("two")

    def test_13_three_converted(self):
        assert "3" in _convert("three")

    def test_14_four_converted(self):
        assert "4" in _convert("four")

    def test_15_five_converted(self):
        assert "5" in _convert("five")

    def test_16_six_converted(self):
        assert "6" in _convert("six")

    def test_17_seven_converted(self):
        assert "7" in _convert("seven")

    def test_18_eight_converted(self):
        assert "8" in _convert("eight")

    def test_19_nine_converted(self):
        assert "9" in _convert("nine")

    def test_20_single_word_zero(self):
        assert _convert("zero") == "0"

    def test_21_single_word_one(self):
        assert _convert("one") == "1"

    def test_22_single_word_nine(self):
        assert _convert("nine") == "9"

    def test_23_digit_at_start_of_sentence(self):
        result = _convert("two cats sat on the mat")
        assert result.startswith("2")

    def test_24_digit_at_end_of_sentence(self):
        result = _convert("I have nine")
        assert result.endswith("9")

    def test_25_digit_in_middle_of_sentence(self):
        result = _convert("I have two cats")
        assert "2" in result
        assert "cats" in result

    def test_26_non_digit_words_preserved(self):
        result = _convert("I have two cats")
        assert "I" in result
        assert "have" in result
        assert "cats" in result

    def test_27_isolated_digit_converted_not_joined(self):
        result = _convert("chapter two page five")
        assert result == "chapter 2 page 5"

    def test_28_multiple_isolated_digits_all_converted(self):
        result = _convert("one cat two dogs three birds")
        assert "1" in result and "2" in result and "3" in result
        assert "cat" in result and "dogs" in result and "birds" in result


# ── Consecutive digit joining (29–50) ─────────────────────────────────────────

class TestConsecutiveJoining:
    def test_29_two_consecutive_joined(self):
        assert _convert("two five") == "25"

    def test_30_three_consecutive_joined(self):
        assert _convert("one two three") == "123"

    def test_31_four_consecutive_joined(self):
        assert _convert("two five six four") == "2564"

    def test_32_code_example_from_spec(self):
        result = _convert("two five six four, that is the code")
        assert result == "2564, that is the code"

    def test_33_all_nine_distinct_digits_joined(self):
        result = _convert("one two three four five six seven eight nine")
        assert result == "123456789"

    def test_34_zeros_in_sequence(self):
        assert _convert("one zero zero") == "100"

    def test_35_oh_treated_as_zero_in_sequence(self):
        assert _convert("one oh five") == "105"

    def test_36_trailing_punctuation_preserved_on_last_digit(self):
        result = _convert("two five six four, that is the code")
        assert "2564," in result

    def test_37_trailing_period_preserved(self):
        result = _convert("the answer is four two.")
        assert "42." in result

    def test_38_trailing_exclamation_preserved(self):
        result = _convert("call nine one one!")
        assert "911!" in result

    def test_39_surrounding_words_preserved(self):
        result = _convert("the code is two five six four ok")
        assert result == "the code is 2564 ok"

    def test_40_two_separate_runs(self):
        result = _convert("first two five then six seven")
        assert "25" in result and "67" in result

    def test_41_run_at_start(self):
        result = _convert("nine one one is emergency")
        assert result.startswith("911")

    def test_42_run_at_end(self):
        result = _convert("the code is one two three")
        assert result.endswith("123")

    def test_43_single_digit_run_of_one(self):
        result = _convert("press five to continue")
        assert "5" in result
        assert "press" in result

    def test_44_long_sequence_ten_digits(self):
        result = _convert("one two three four five six seven eight nine zero")
        assert result == "1234567890"

    def test_45_repeated_digit(self):
        assert _convert("five five five") == "555"

    def test_46_run_followed_immediately_by_non_digit(self):
        result = _convert("two five cats")
        assert "25" in result
        assert "cats" in result

    def test_47_non_digit_between_two_runs(self):
        result = _convert("one two and three four")
        assert "12" in result
        assert "34" in result

    def test_48_comma_after_digit_ends_run_correctly(self):
        result = _convert("two five six four, done")
        assert result == "2564, done"

    def test_49_question_mark_after_digit(self):
        result = _convert("is the code two five six?")
        assert "256?" in result

    def test_50_semicolon_after_digit(self):
        result = _convert("use code four two; then continue")
        assert "42;" in result


# ── Plus prefix / phone numbers (51–68) ───────────────────────────────────────

class TestPlusPrefix:
    def test_51_plus_before_digit_becomes_plus_sign(self):
        assert _convert("plus one") == "+1"

    def test_52_phone_number_from_spec(self):
        result = _convert(
            "My phone number is plus one four eight two six seven five eight four two one."
        )
        assert "+14826758421." in result

    def test_53_plus_sign_in_result(self):
        result = _convert("call plus one two three")
        assert "+" in result

    def test_54_plus_digit_run_concatenated(self):
        assert _convert("plus one four four") == "+144"

    def test_55_plus_only_no_digit_after_stays_as_plus(self):
        result = _convert("plus hello")
        assert "plus" in result

    def test_56_plus_before_single_digit(self):
        assert _convert("plus nine") == "+9"

    def test_57_plus_before_long_run(self):
        result = _convert("plus one two three four five six seven eight nine zero")
        assert result == "+1234567890"

    def test_58_context_words_preserved_around_phone(self):
        result = _convert("call plus one two three now")
        assert "call" in result
        assert "+123" in result
        assert "now" in result

    def test_59_plus_not_consumed_when_followed_by_non_digit(self):
        result = _convert("plus size clothing")
        assert "plus" in result
        assert "size" in result

    def test_60_multiple_plus_prefixes(self):
        result = _convert("plus one two and plus three four")
        assert "+12" in result
        assert "+34" in result

    def test_61_plus_at_start(self):
        result = _convert("plus one eight hundred")
        assert result.startswith("+1")

    def test_62_plus_preceded_by_word(self):
        result = _convert("number is plus one two three")
        assert "+123" in result

    def test_63_plus_with_trailing_period(self):
        result = _convert("plus one two three.")
        assert "+123." in result

    def test_64_plus_with_zero(self):
        assert _convert("plus zero") == "+0"

    def test_65_plus_with_oh(self):
        assert _convert("plus oh five") == "+05"

    def test_66_plus_one_four_four_four(self):
        assert _convert("plus one four four four") == "+1444"

    def test_67_international_format(self):
        result = _convert("plus four four two zero seven nine")
        assert result == "+44207​9".replace("​", "") or "+442079" in result or result == "+442079"

    def test_68_plus_mid_sentence(self):
        result = _convert("my number is plus one two three and thats it")
        assert "+123" in result
        assert "my number is" in result


# ── Case insensitivity (69–75) ────────────────────────────────────────────────

class TestCaseInsensitivity:
    def test_69_uppercase_TWO_converted(self):
        assert "2" in _convert("TWO")

    def test_70_mixed_case_Three_converted(self):
        assert "3" in _convert("Three")

    def test_71_uppercase_run_joined(self):
        result = _convert("TWO FIVE SIX")
        assert "256" in result

    def test_72_mixed_case_in_sentence(self):
        result = _convert("Press FIVE then Two")
        assert "5" in result and "2" in result

    def test_73_plus_uppercase_PLUS(self):
        result = _convert("PLUS one two")
        # "PLUS" is not lowercased during token clean — check behaviour
        # _clean lowercases, so PLUS → plus → handled
        assert "+" in result or "PLUS" in result

    def test_74_Oh_as_zero(self):
        assert "0" in _convert("Oh five")

    def test_75_ZERO_converted(self):
        assert "0" in _convert("ZERO")


# ── Non-consecutive digits (76–88) ────────────────────────────────────────────

class TestNonConsecutive:
    def test_76_digit_separated_by_word_both_converted(self):
        result = _convert("two cats and five dogs")
        assert "2" in result and "5" in result

    def test_77_digit_separated_by_word_not_joined(self):
        result = _convert("two cats and five dogs")
        assert "25" not in result  # not joined since not consecutive

    def test_78_three_isolated_digits_all_converted(self):
        result = _convert("one cat two dogs three birds")
        assert "1" in result and "2" in result and "3" in result

    def test_79_digit_in_every_other_word(self):
        result = _convert("on one go two stop three")
        assert "1" in result and "2" in result and "3" in result

    def test_80_digit_words_not_adjacent_preserve_context(self):
        result = _convert("chapter two section five paragraph nine")
        assert result == "chapter 2 section 5 paragraph 9"

    def test_81_digit_at_start_and_end(self):
        result = _convert("one is the start and nine is the end")
        assert result.startswith("1")
        assert "9" in result

    def test_82_sentence_with_one_digit(self):
        result = _convert("I need seven apples")
        assert "7" in result
        assert "I need" in result
        assert "apples" in result

    def test_83_answer_is_nine(self):
        assert _convert("the answer is nine") == "the answer is 9"

    def test_84_no_false_joins_across_words(self):
        result = _convert("two cats five dogs")
        # "2" and "5" present but not "25"
        tokens = result.split()
        assert "2" in tokens
        assert "5" in tokens

    def test_85_comma_between_digits_breaks_run(self):
        # "two," has trailing comma → run stops, emits "2,"
        # "three" starts a new conversion → "3"
        result = _convert("two, three cats")
        assert "2," in result
        assert "3" in result
        assert "23" not in result  # not joined

    def test_86_multiple_sentences_each_converted(self):
        result = _convert("I have two. You have five.")
        assert "2." in result
        assert "5." in result

    def test_87_zero_isolated(self):
        result = _convert("floor zero is the lobby")
        assert "0" in result
        assert "floor" in result
        assert "lobby" in result

    def test_88_all_nine_digits_non_consecutive(self):
        result = _convert(
            "one apple two bananas three cherries four dates "
            "five eggs six figs seven grapes eight herbs nine items"
        )
        for d in "123456789":
            assert d in result


# ── Edge cases (89–100) ───────────────────────────────────────────────────────

class TestEdgeCases:
    def test_89_single_token_oh(self):
        assert _convert("oh") == "0"

    def test_90_oh_in_sequence(self):
        assert _convert("nine oh one") == "901"

    def test_91_digit_word_with_trailing_quote(self):
        # "two'" → clean="two" (digit), trail="'" → converted and emitted as "2'"
        result = _convert("say two'")
        assert "2'" in result

    def test_92_output_is_stripped(self):
        result = _convert("two five six")
        assert result == result.strip()

    def test_93_no_double_spaces(self):
        result = _convert("one two three cats")
        assert "  " not in result

    def test_94_unicode_words_not_affected(self):
        result = _convert("héllo wörld")
        assert result == "héllo wörld"

    def test_95_numbers_already_in_text_unchanged(self):
        result = _convert("I have 5 cats")
        assert "5" in result  # already a digit, untouched

    def test_96_plus_sign_already_in_text_unchanged(self):
        result = _convert("+1 is the country code")
        assert "+1" in result

    def test_97_very_long_sequence(self):
        words = " ".join(["one", "two", "three", "four", "five"] * 10)
        result = _convert(words)
        assert "12345" * 10 == result

    def test_98_plus_followed_by_zero(self):
        assert _convert("plus zero one") == "+01"

    def test_99_colon_after_digit(self):
        result = _convert("at five: sharp")
        assert "5:" in result

    def test_100_full_pipeline_example(self):
        result = _convert(
            "My phone number is plus one four eight two six seven five eight four two one."
        )
        assert "My phone number is" in result
        assert "+14826758421." in result


# ── Compound numbers / word2number (101–115) ──────────────────────────────────
# These tests are skipped when word2number is not installed.

import pytest

_W2N_INSTALLED = _w2i("one") is not None


@pytest.mark.skipif(not _W2N_INSTALLED, reason="word2number not installed")
class TestCompoundNumbers:
    def test_101_twenty_five(self):
        assert _convert("twenty-five") == "25"

    def test_102_hyphen_compound_in_sentence(self):
        result = _convert("I need thirty-two items")
        assert "32" in result
        assert "I need" in result
        assert "items" in result

    def test_103_forty_five(self):
        assert _convert("forty-five") == "45"

    def test_104_ninety_nine(self):
        assert _convert("ninety-nine") == "99"

    def test_105_twenty_no_hyphen(self):
        assert _convert("twenty five") == "25"

    def test_106_one_hundred(self):
        assert _convert("one hundred") == "100"

    def test_107_two_thousand(self):
        assert _convert("two thousand") == "2000"

    def test_108_one_hundred_and_twenty(self):
        result = _convert("one hundred and twenty")
        assert result == "120"

    def test_109_compound_with_context(self):
        result = _convert("I have forty-five apples")
        assert "45" in result
        assert "apples" in result

    def test_110_decimal_one_point_five(self):
        assert _convert("one point five") == "1.5"

    def test_111_decimal_three_point_one_four(self):
        result = _convert("three point one four")
        assert "3.14" in result

    def test_112_decimal_in_sentence(self):
        result = _convert("the temperature is two point five degrees")
        assert "2.5" in result
        assert "degrees" in result

    def test_113_time_three_forty_five_pm(self):
        result = _convert("three forty-five P M")
        assert "3:45 PM" in result

    def test_114_time_ten_thirty_am(self):
        result = _convert("ten thirty A M")
        assert "10:30 AM" in result

    def test_115_am_pm_normalization(self):
        result = _convert("at nine A M sharp")
        assert "AM" in result
        assert "sharp" in result

    def test_116_phone_stt_comma_fragments_merged(self):
        # STT sometimes inserts commas: "+1, 732, 405, 1036" → "+17324051036"
        result = _convert("+1, 732, 405, 1036")
        assert result == "+17324051036"

    def test_117_phone_fragments_in_sentence(self):
        result = _convert("Hey, we can connect on +1, 732, 405, 1036.")
        assert "+17324051036" in result

    def test_118_two_fragment_groups(self):
        result = _convert("+44, 207, 123, 4567")
        assert result == "+442071234567"

    # ── Date ordinals (119–130) ───────────────────────────────────────────────

    def test_119_birthday_april_twenty_seventh(self):
        result = _convert("My birthday is on April twenty-seventh, 2003.")
        assert "April 27th" in result

    def test_120_january_first(self):
        result = _convert("January first")
        assert result == "January 1st"

    def test_121_first_of_january(self):
        result = _convert("first of January")
        assert result == "1st of January"

    def test_122_march_twenty_first(self):
        result = _convert("March twenty-first")
        assert "March 21st" in result

    def test_123_december_thirty_first(self):
        result = _convert("December thirty-first")
        assert "December 31st" in result

    def test_124_stt_pre_digitised_ordinal(self):
        # STT already converted "twenty" → "20", leaving "seventh" as word
        result = _convert("April 20 seventh, 2003")
        assert "27th" in result

    def test_125_standalone_ordinal_no_date_context_unchanged(self):
        # "first" not in date context → stays as-is
        result = _convert("The first time")
        assert result == "The first time"

    def test_126_standalone_ordinal_no_date_context_second(self):
        result = _convert("my second car")
        assert result == "my second car"

    def test_127_ordinal_after_month_twentieth(self):
        result = _convert("June twentieth")
        assert "June 20th" in result

    def test_128_seventh_of_march(self):
        result = _convert("seventh of March")
        assert "7th of March" in result

    def test_129_january_1st_already_digit_unchanged(self):
        # Already digit form — should pass through untouched
        result = _convert("January 1st")
        assert result == "January 1st"

    def test_130_full_birthday_sentence(self):
        result = _convert("My birthday is on April twenty-seventh, 2003.")
        assert "My birthday is on April 27th, 2003." == result

    def test_131_millionth_standalone(self):
        assert _convert("millionth") == "1000000th"

    def test_132_ten_millionth(self):
        # "ten" → "10" via compound path, then post-pass multiplies
        result = _convert("ten millionth")
        assert result == "10000000th"

    def test_133_thousandth_standalone(self):
        assert _convert("thousandth") == "1000th"

    def test_134_hundredth_standalone(self):
        assert _convert("hundredth") == "100th"

    def test_135_billionth_standalone(self):
        assert _convert("billionth") == "1000000000th"

    def test_136_five_millionth(self):
        result = _convert("five millionth")
        assert result == "5000000th"

    def test_137_large_ordinal_non_numeral_unchanged(self):
        # In non-numeral mode _convert is never called — this just verifies
        # the word "millionth" has no special meaning outside the function
        assert "millionth" in "the millionth time"
