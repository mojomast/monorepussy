from __future__ import annotations

from reverseoracle.marks import add_mark, load_marks, lookup_mark


def test_marks_round_trip(temp_repo):
    mark = add_mark(temp_repo, "abc123", "Chose Redis", "Memcached", "src/cache")
    marks = load_marks(temp_repo)
    assert marks[0].id == mark.id
    found = lookup_mark(temp_repo, mark_id=mark.id)
    assert found is not None
    assert found.commit == "abc123"
