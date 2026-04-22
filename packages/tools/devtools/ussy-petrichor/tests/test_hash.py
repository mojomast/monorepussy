"""Tests for petrichor.hash module."""

import hashlib

from petrichor.hash import content_hash, file_hash, string_hash


class TestContentHash:
    def test_basic_hash(self):
        result = content_hash(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert result == expected

    def test_empty_content(self):
        result = content_hash(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected

    def test_different_content_different_hash(self):
        h1 = content_hash(b"foo")
        h2 = content_hash(b"bar")
        assert h1 != h2

    def test_same_content_same_hash(self):
        h1 = content_hash(b"same")
        h2 = content_hash(b"same")
        assert h1 == h2

    def test_hash_length(self):
        result = content_hash(b"test")
        assert len(result) == 64  # SHA-256 hex digest length


class TestFileHash:
    def test_file_hash(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt") if 'os' in dir() else ""
        import os
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "wb") as f:
            f.write(b"file content")
        result = file_hash(path)
        expected = hashlib.sha256(b"file content").hexdigest()
        assert result == expected

    def test_file_not_found(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            file_hash("/nonexistent/path/file.txt")

    def test_binary_file_hash(self, tmp_dir):
        import os
        path = os.path.join(tmp_dir, "binary.bin")
        with open(path, "wb") as f:
            f.write(bytes(range(256)))
        result = file_hash(path)
        assert len(result) == 64


class TestStringHash:
    def test_string_hash(self):
        result = string_hash("hello world")
        expected = hashlib.sha256("hello world".encode("utf-8")).hexdigest()
        assert result == expected

    def test_empty_string(self):
        result = string_hash("")
        assert len(result) == 64

    def test_unicode_string(self):
        result = string_hash("héllo wörld")
        assert len(result) == 64

    def test_consistent_with_content_hash(self):
        text = "test string"
        h1 = string_hash(text)
        h2 = content_hash(text.encode("utf-8"))
        assert h1 == h2
