"""
Contract tests for the history subsystem.

These tests define the required BEHAVIOUR of history storage — not the
implementation. If the backend changes (SQLite, CoreData, cloud, …) only
the HistoryAdapter class below needs updating; every test stays the same.

Run with: python3 -m pytest test_history.py -v
"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from pathlib import Path


# ── Adapter ───────────────────────────────────────────────────────────────────
# Only this class changes when the history backend changes.

class HistoryAdapter:
    """Thin facade over the current history.py implementation."""

    def __init__(self, data_dir: Path):
        import history as _hist
        self._hist = _hist
        self._orig_file = _hist.HISTORY_FILE
        _hist.HISTORY_FILE = data_dir / "history.json"

    def teardown(self):
        self._hist.HISTORY_FILE = self._orig_file

    def get_history(self) -> list:
        return self._hist.get_history()

    def clear_history(self):
        return self._hist.clear_history()

    def append(self, transcript: str, entry_type: str = "dictation",
                actions: list | None = None, success: bool = True):
        return self._hist.append_entry(transcript, entry_type, actions or [], success)


@pytest.fixture
def hist(tmp_path):
    adapter = HistoryAdapter(tmp_path)
    yield adapter
    adapter.teardown()


# ── Initial state contracts (1–5) ─────────────────────────────────────────────

class TestInitialState:
    def test_01_history_starts_empty(self, hist):
        assert hist.get_history() == []

    def test_02_get_history_returns_list(self, hist):
        assert isinstance(hist.get_history(), list)

    def test_03_clear_on_empty_is_safe(self, hist):
        hist.clear_history()
        assert hist.get_history() == []

    def test_04_clear_returns_none(self, hist):
        assert hist.clear_history() is None

    def test_05_multiple_gets_before_any_append_return_empty(self, hist):
        for _ in range(3):
            assert hist.get_history() == []


# ── Entry field contracts (6–22) ──────────────────────────────────────────────

class TestEntryFields:
    def test_06_append_returns_none(self, hist):
        assert hist.append("hello") is None

    def test_07_entry_has_id(self, hist):
        hist.append("hello")
        assert "id" in hist.get_history()[0]

    def test_08_id_is_a_valid_uuid4(self, hist):
        hist.append("hello")
        entry_id = hist.get_history()[0]["id"]
        parsed = uuid.UUID(entry_id)
        assert parsed.version == 4

    def test_09_id_is_a_string(self, hist):
        hist.append("hello")
        assert isinstance(hist.get_history()[0]["id"], str)

    def test_10_entry_has_timestamp(self, hist):
        hist.append("hello")
        assert "timestamp" in hist.get_history()[0]

    def test_11_timestamp_ends_with_z(self, hist):
        hist.append("hello")
        assert hist.get_history()[0]["timestamp"].endswith("Z")

    def test_12_timestamp_is_parseable_iso8601(self, hist):
        hist.append("hello")
        ts = hist.get_history()[0]["timestamp"].rstrip("Z")
        datetime.fromisoformat(ts)  # raises if invalid

    def test_13_entry_has_transcript(self, hist):
        hist.append("hello")
        assert "transcript" in hist.get_history()[0]

    def test_14_transcript_value_matches_input(self, hist):
        hist.append("test sentence")
        assert hist.get_history()[0]["transcript"] == "test sentence"

    def test_15_entry_has_entry_type(self, hist):
        hist.append("hello")
        assert "entry_type" in hist.get_history()[0]

    def test_16_entry_type_matches_input(self, hist):
        hist.append("hello", entry_type="command")
        assert hist.get_history()[0]["entry_type"] == "command"

    def test_17_entry_has_actions(self, hist):
        hist.append("hello")
        assert "actions" in hist.get_history()[0]

    def test_18_actions_value_matches_input(self, hist):
        actions = [{"action": "type_text", "args": {"text": "hi"}}]
        hist.append("hello", actions=actions)
        assert hist.get_history()[0]["actions"] == actions

    def test_19_entry_has_success(self, hist):
        hist.append("hello")
        assert "success" in hist.get_history()[0]

    def test_20_success_true_stored(self, hist):
        hist.append("hello", success=True)
        assert hist.get_history()[0]["success"] is True

    def test_21_success_false_stored(self, hist):
        hist.append("hello", success=False)
        assert hist.get_history()[0]["success"] is False

    def test_22_entry_has_exactly_six_fields(self, hist):
        hist.append("hello")
        assert len(hist.get_history()[0]) == 6


# ── Ordering contracts (23–33) ────────────────────────────────────────────────

class TestOrdering:
    def test_23_single_append_produces_one_entry(self, hist):
        hist.append("hello")
        assert len(hist.get_history()) == 1

    def test_24_newest_entry_is_first(self, hist):
        hist.append("first")
        hist.append("second")
        assert hist.get_history()[0]["transcript"] == "second"

    def test_25_oldest_entry_is_last(self, hist):
        hist.append("first")
        hist.append("second")
        assert hist.get_history()[-1]["transcript"] == "first"

    def test_26_three_entries_correct_order(self, hist):
        for t in ["one", "two", "three"]:
            hist.append(t)
        transcripts = [e["transcript"] for e in hist.get_history()]
        assert transcripts == ["three", "two", "one"]

    def test_27_ten_entries_correct_order(self, hist):
        for i in range(10):
            hist.append(f"entry_{i}")
        entries = hist.get_history()
        assert entries[0]["transcript"] == "entry_9"
        assert entries[-1]["transcript"] == "entry_0"

    def test_28_two_appends_produce_two_entries(self, hist):
        hist.append("a")
        hist.append("b")
        assert len(hist.get_history()) == 2

    def test_29_entries_have_unique_ids(self, hist):
        hist.append("a")
        hist.append("b")
        ids = [e["id"] for e in hist.get_history()]
        assert ids[0] != ids[1]

    def test_30_all_ids_unique_across_ten_entries(self, hist):
        for i in range(10):
            hist.append(f"t{i}")
        ids = [e["id"] for e in hist.get_history()]
        assert len(ids) == len(set(ids))

    def test_31_get_history_twice_same_order(self, hist):
        for t in ["a", "b", "c"]:
            hist.append(t)
        assert hist.get_history() == hist.get_history()

    def test_32_repeated_reads_are_consistent(self, hist):
        hist.append("stable")
        for _ in range(5):
            assert hist.get_history()[0]["transcript"] == "stable"

    def test_33_appended_entry_is_always_first(self, hist):
        for i in range(5):
            hist.append(f"msg_{i}")
            assert hist.get_history()[0]["transcript"] == f"msg_{i}"


# ── Clear contracts (34–43) ───────────────────────────────────────────────────

class TestClearContracts:
    def test_34_clear_empties_history(self, hist):
        hist.append("hello")
        hist.clear_history()
        assert hist.get_history() == []

    def test_35_clear_removes_multiple_entries(self, hist):
        for i in range(10):
            hist.append(f"entry_{i}")
        hist.clear_history()
        assert hist.get_history() == []

    def test_36_append_after_clear_works(self, hist):
        hist.append("before")
        hist.clear_history()
        hist.append("after")
        entries = hist.get_history()
        assert len(entries) == 1
        assert entries[0]["transcript"] == "after"

    def test_37_clear_twice_is_safe(self, hist):
        hist.append("hello")
        hist.clear_history()
        hist.clear_history()
        assert hist.get_history() == []

    def test_38_clear_then_multiple_appends(self, hist):
        hist.append("old")
        hist.clear_history()
        hist.append("new1")
        hist.append("new2")
        assert len(hist.get_history()) == 2

    def test_39_clear_returns_none(self, hist):
        hist.append("hello")
        result = hist.clear_history()
        assert result is None

    def test_40_history_is_empty_after_clear(self, hist):
        hist.append("a")
        hist.append("b")
        hist.clear_history()
        assert len(hist.get_history()) == 0

    def test_41_clear_then_get_returns_empty_list(self, hist):
        hist.append("x")
        hist.clear_history()
        result = hist.get_history()
        assert result == []
        assert isinstance(result, list)

    def test_42_clear_then_append_produces_correct_fields(self, hist):
        hist.clear_history()
        hist.append("fresh", entry_type="dictation", actions=[], success=True)
        entry = hist.get_history()[0]
        assert entry["transcript"] == "fresh"
        assert entry["success"] is True

    def test_43_new_ids_after_clear(self, hist):
        hist.append("before")
        old_id = hist.get_history()[0]["id"]
        hist.clear_history()
        hist.append("after")
        new_id = hist.get_history()[0]["id"]
        assert old_id != new_id


# ── Capacity contracts (44–50) ────────────────────────────────────────────────

class TestCapacityContracts:
    def test_44_history_capped_at_500_entries(self, hist):
        for i in range(501):
            hist.append(f"entry_{i}")
        assert len(hist.get_history()) == 500

    def test_45_newest_entries_kept_when_cap_exceeded(self, hist):
        for i in range(501):
            hist.append(f"entry_{i}")
        entries = hist.get_history()
        assert entries[0]["transcript"] == "entry_500"

    def test_46_oldest_entry_dropped_at_cap(self, hist):
        for i in range(501):
            hist.append(f"entry_{i}")
        transcripts = [e["transcript"] for e in hist.get_history()]
        assert "entry_0" not in transcripts

    def test_47_exactly_500_entries_kept(self, hist):
        for i in range(600):
            hist.append(f"t{i}")
        assert len(hist.get_history()) == 500

    def test_48_cap_applies_cumulatively(self, hist):
        for i in range(499):
            hist.append(f"t{i}")
        assert len(hist.get_history()) == 499
        hist.append("one_more")
        assert len(hist.get_history()) == 500
        hist.append("overflow")
        assert len(hist.get_history()) == 500

    def test_49_under_500_entries_no_data_lost(self, hist):
        for i in range(10):
            hist.append(f"t{i}")
        assert len(hist.get_history()) == 10

    def test_50_cap_resets_after_clear(self, hist):
        for i in range(500):
            hist.append(f"t{i}")
        hist.clear_history()
        for i in range(10):
            hist.append(f"new_{i}")
        assert len(hist.get_history()) == 10


# ── Content fidelity contracts (51–70) ────────────────────────────────────────

class TestContentFidelity:
    def test_51_unicode_transcript_preserved(self, hist):
        hist.append("日本語テスト")
        assert hist.get_history()[0]["transcript"] == "日本語テスト"

    def test_52_emoji_in_transcript_preserved(self, hist):
        hist.append("hello 🎙️ world")
        assert hist.get_history()[0]["transcript"] == "hello 🎙️ world"

    def test_53_transcript_with_newlines_preserved(self, hist):
        hist.append("line1\nline2")
        assert hist.get_history()[0]["transcript"] == "line1\nline2"

    def test_54_transcript_with_quotes_preserved(self, hist):
        hist.append('say "hello"')
        assert hist.get_history()[0]["transcript"] == 'say "hello"'

    def test_55_long_transcript_preserved(self, hist):
        long = "word " * 300
        hist.append(long)
        assert hist.get_history()[0]["transcript"] == long

    def test_56_empty_transcript_stored(self, hist):
        hist.append("")
        assert hist.get_history()[0]["transcript"] == ""

    def test_57_empty_actions_list_preserved(self, hist):
        hist.append("hello", actions=[])
        assert hist.get_history()[0]["actions"] == []

    def test_58_multiple_actions_preserved(self, hist):
        actions = [{"action": f"act_{i}"} for i in range(5)]
        hist.append("hello", actions=actions)
        assert hist.get_history()[0]["actions"] == actions

    def test_59_nested_action_args_preserved(self, hist):
        actions = [{"action": "type_text", "args": {"text": "hi", "speed": 100}}]
        hist.append("hello", actions=actions)
        stored = hist.get_history()[0]["actions"][0]
        assert stored["args"]["text"] == "hi"
        assert stored["args"]["speed"] == 100

    def test_60_custom_entry_type_preserved(self, hist):
        hist.append("hello", entry_type="custom_type_xyz")
        assert hist.get_history()[0]["entry_type"] == "custom_type_xyz"

    def test_61_entry_type_dictation(self, hist):
        hist.append("hello", entry_type="dictation")
        assert hist.get_history()[0]["entry_type"] == "dictation"

    def test_62_entry_type_command(self, hist):
        hist.append("search for cats", entry_type="command")
        assert hist.get_history()[0]["entry_type"] == "command"

    def test_63_success_bool_true_is_not_truthy_int(self, hist):
        hist.append("hello", success=True)
        assert hist.get_history()[0]["success"] is True

    def test_64_success_bool_false_is_not_falsy_int(self, hist):
        hist.append("hello", success=False)
        assert hist.get_history()[0]["success"] is False

    def test_65_transcript_with_special_chars(self, hist):
        hist.append("cmd: ls -la & echo 'done'")
        assert "ls -la" in hist.get_history()[0]["transcript"]

    def test_66_all_five_entries_distinct_after_five_appends(self, hist):
        texts = ["alpha", "beta", "gamma", "delta", "epsilon"]
        for t in texts:
            hist.append(t)
        stored = [e["transcript"] for e in hist.get_history()]
        for t in texts:
            assert t in stored

    def test_67_actions_not_shared_between_entries(self, hist):
        hist.append("first", actions=[{"action": "a"}])
        hist.append("second", actions=[{"action": "b"}])
        entries = hist.get_history()
        assert entries[0]["actions"][0]["action"] == "b"
        assert entries[1]["actions"][0]["action"] == "a"

    def test_68_whitespace_transcript_stored_as_is(self, hist):
        hist.append("  leading and trailing  ")
        assert hist.get_history()[0]["transcript"] == "  leading and trailing  "

    def test_69_numbers_in_transcript(self, hist):
        hist.append("chapter 42 page 100")
        assert hist.get_history()[0]["transcript"] == "chapter 42 page 100"

    def test_70_punctuation_in_transcript(self, hist):
        hist.append("Hello, world! How are you?")
        assert hist.get_history()[0]["transcript"] == "Hello, world! How are you?"


# ── Persistence contracts (71–82) ─────────────────────────────────────────────

class TestPersistenceContracts:
    def test_71_entry_survives_repeated_reads(self, hist):
        hist.append("durable")
        for _ in range(5):
            assert hist.get_history()[0]["transcript"] == "durable"

    def test_72_two_entries_both_survive_reads(self, hist):
        hist.append("first")
        hist.append("second")
        entries = hist.get_history()
        assert len(entries) == 2

    def test_73_append_then_clear_then_check_empty(self, hist):
        hist.append("x")
        hist.clear_history()
        assert hist.get_history() == []

    def test_74_state_not_shared_between_fixtures(self, hist):
        # Each test gets a fresh HistoryAdapter → this must be empty
        assert hist.get_history() == []

    def test_75_append_five_clear_append_one(self, hist):
        for i in range(5):
            hist.append(f"old_{i}")
        hist.clear_history()
        hist.append("new")
        result = hist.get_history()
        assert len(result) == 1
        assert result[0]["transcript"] == "new"

    def test_76_transcript_exact_match_after_read(self, hist):
        text = "exact text no modification"
        hist.append(text)
        assert hist.get_history()[0]["transcript"] == text

    def test_77_id_does_not_change_across_reads(self, hist):
        hist.append("stable")
        id1 = hist.get_history()[0]["id"]
        id2 = hist.get_history()[0]["id"]
        assert id1 == id2

    def test_78_timestamp_does_not_change_across_reads(self, hist):
        hist.append("stable")
        ts1 = hist.get_history()[0]["timestamp"]
        ts2 = hist.get_history()[0]["timestamp"]
        assert ts1 == ts2

    def test_79_all_fields_stable_across_reads(self, hist):
        actions = [{"action": "type"}]
        hist.append("test", entry_type="dictation", actions=actions, success=True)
        e1 = hist.get_history()[0]
        e2 = hist.get_history()[0]
        assert e1 == e2

    def test_80_mutation_of_returned_list_does_not_corrupt_store(self, hist):
        hist.append("original")
        result = hist.get_history()
        result.clear()  # mutate the returned list
        # Store should still have the entry
        assert len(hist.get_history()) == 1

    def test_81_large_batch_all_preserved_under_cap(self, hist):
        for i in range(100):
            hist.append(f"entry_{i}")
        entries = hist.get_history()
        assert len(entries) == 100
        transcripts = {e["transcript"] for e in entries}
        assert len(transcripts) == 100  # all distinct

    def test_82_get_history_is_not_none(self, hist):
        result = hist.get_history()
        assert result is not None


# ── Edge case contracts (83–100) ──────────────────────────────────────────────

class TestEdgeCaseContracts:
    def test_83_append_single_word(self, hist):
        hist.append("hello")
        assert hist.get_history()[0]["transcript"] == "hello"

    def test_84_append_single_char(self, hist):
        hist.append("x")
        assert hist.get_history()[0]["transcript"] == "x"

    def test_85_append_very_long_actions_list(self, hist):
        actions = [{"action": f"step_{i}"} for i in range(100)]
        hist.append("hello", actions=actions)
        assert len(hist.get_history()[0]["actions"]) == 100

    def test_86_success_is_boolean_type(self, hist):
        hist.append("test", success=True)
        val = hist.get_history()[0]["success"]
        assert type(val) is bool

    def test_87_id_field_is_nonempty(self, hist):
        hist.append("hello")
        assert hist.get_history()[0]["id"] != ""

    def test_88_timestamp_field_is_nonempty(self, hist):
        hist.append("hello")
        assert hist.get_history()[0]["timestamp"] != ""

    def test_89_clear_then_100_entries_all_present(self, hist):
        hist.clear_history()
        for i in range(100):
            hist.append(f"t{i}")
        assert len(hist.get_history()) == 100

    def test_90_entry_type_empty_string(self, hist):
        hist.append("hello", entry_type="")
        assert hist.get_history()[0]["entry_type"] == ""

    def test_91_no_extra_fields_injected(self, hist):
        hist.append("hello")
        entry = hist.get_history()[0]
        expected_keys = {"id", "timestamp", "transcript", "entry_type", "actions", "success"}
        assert set(entry.keys()) == expected_keys

    def test_92_two_entries_independent_fields(self, hist):
        hist.append("first", success=True)
        hist.append("second", success=False)
        entries = hist.get_history()
        assert entries[0]["success"] is False   # second (newest)
        assert entries[1]["success"] is True    # first (oldest)

    def test_93_append_then_clear_then_append_new_id(self, hist):
        hist.append("old")
        old_id = hist.get_history()[0]["id"]
        hist.clear_history()
        hist.append("new")
        new_id = hist.get_history()[0]["id"]
        assert old_id != new_id

    def test_94_get_history_result_length_matches_appends(self, hist):
        for n in range(1, 6):
            hist.append(f"entry_{n}")
            assert len(hist.get_history()) == n

    def test_95_all_entries_have_string_ids(self, hist):
        for i in range(5):
            hist.append(f"t{i}")
        for entry in hist.get_history():
            assert isinstance(entry["id"], str)

    def test_96_all_entries_have_string_transcripts(self, hist):
        for i in range(5):
            hist.append(f"t{i}")
        for entry in hist.get_history():
            assert isinstance(entry["transcript"], str)

    def test_97_all_entries_have_list_actions(self, hist):
        for i in range(5):
            hist.append(f"t{i}")
        for entry in hist.get_history():
            assert isinstance(entry["actions"], list)

    def test_98_all_entries_have_bool_success(self, hist):
        for i in range(5):
            hist.append(f"t{i}", success=(i % 2 == 0))
        for entry in hist.get_history():
            assert isinstance(entry["success"], bool)

    def test_99_get_history_after_many_clears(self, hist):
        for _ in range(5):
            hist.append("x")
            hist.clear_history()
        assert hist.get_history() == []

    def test_100_append_actions_does_not_mutate_input_list(self, hist):
        actions = [{"action": "type_text"}]
        original = list(actions)
        hist.append("hello", actions=actions)
        assert actions == original
