import pytest
from datetime import datetime, timezone

from parliament.journal import JournalEngine
from parliament.models import EntryType, JournalEntry
from parliament.storage import JournalStore


class TestJournalEngine:
    def test_append_and_view(self, tmp_chamber):
        store = JournalStore(tmp_chamber / "journal.log")
        engine = JournalEngine(store)
        entry = engine.append(EntryType.MOTION_INTRODUCED, {"motion_id": "MP-1"}, session_id="MP-1")
        assert entry.entry_type == EntryType.MOTION_INTRODUCED
        entries = engine.view_session("MP-1")
        assert len(entries) == 1
        assert entries[0].entry_id == entry.entry_id

    def test_chain_integrity(self, tmp_chamber):
        store = JournalStore(tmp_chamber / "journal.log")
        engine = JournalEngine(store)
        engine.append(EntryType.MOTION_INTRODUCED, {"motion_id": "MP-1"}, session_id="MP-1")
        engine.append(EntryType.SECONDED, {"motion_id": "MP-1", "agent": "a1"}, session_id="MP-1")
        assert engine.verify() is True

    def test_chain_broken_by_tampering(self, tmp_chamber):
        store = JournalStore(tmp_chamber / "journal.log")
        engine = JournalEngine(store)
        engine.append(EntryType.MOTION_INTRODUCED, {"motion_id": "MP-1"}, session_id="MP-1")
        # Tamper with the file
        path = tmp_chamber / "journal.log"
        content = path.read_text()
        tampered = content.replace("MP-1", "MP-TAMPERED")
        path.write_text(tampered)
        assert engine.verify() is False

    def test_generate_minutes(self, tmp_chamber):
        store = JournalStore(tmp_chamber / "journal.log")
        engine = JournalEngine(store)
        engine.append(EntryType.MOTION_INTRODUCED, {"motion_id": "MP-1"}, session_id="MP-1")
        minutes = engine.generate_minutes("MP-1")
        assert "Minutes for Session MP-1" in minutes
        assert "motion_introduced" in minutes.lower()

    def test_last_entry(self, tmp_chamber):
        store = JournalStore(tmp_chamber / "journal.log")
        engine = JournalEngine(store)
        assert engine.last_entry() is None
        engine.append(EntryType.MOTION_INTRODUCED, {"motion_id": "MP-1"})
        last = engine.last_entry()
        assert last is not None
        assert last.entry_type == EntryType.MOTION_INTRODUCED

    def test_chain_length(self, tmp_chamber):
        store = JournalStore(tmp_chamber / "journal.log")
        engine = JournalEngine(store)
        assert engine.chain_length() == 0
        engine.append(EntryType.MOTION_INTRODUCED, {"motion_id": "MP-1"})
        engine.append(EntryType.SECONDED, {"motion_id": "MP-1"})
        assert engine.chain_length() == 2

    def test_previous_hash_linking(self, tmp_chamber):
        store = JournalStore(tmp_chamber / "journal.log")
        engine = JournalEngine(store)
        e1 = engine.append(EntryType.MOTION_INTRODUCED, {"motion_id": "MP-1"})
        e2 = engine.append(EntryType.SECONDED, {"motion_id": "MP-1"})
        assert e2.previous_hash == e1.hash

    def test_cross_session_isolation(self, tmp_chamber):
        store = JournalStore(tmp_chamber / "journal.log")
        engine = JournalEngine(store)
        engine.append(EntryType.MOTION_INTRODUCED, {"motion_id": "MP-1"}, session_id="S1")
        engine.append(EntryType.MOTION_INTRODUCED, {"motion_id": "MP-2"}, session_id="S2")
        s1_entries = engine.view_session("S1")
        s2_entries = engine.view_session("S2")
        assert len(s1_entries) == 1
        assert len(s2_entries) == 1
        assert s1_entries[0].data != s2_entries[0].data
