"""Tests for petrichor.cli module."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ussy_petrichor.cli import build_parser, main


class TestCLIParser:
    def test_build_parser(self):
        parser = build_parser()
        assert parser is not None

    def test_parser_init(self):
        parser = build_parser()
        args = parser.parse_args(["init", "/etc/nginx/"])
        assert args.command == "init"
        assert args.path == "/etc/nginx/"

    def test_parser_init_with_desired(self):
        parser = build_parser()
        args = parser.parse_args(["init", "/etc/nginx/", "--desired-state", "git://..."])
        assert args.desired_state == "git://..."

    def test_parser_snapshot(self):
        parser = build_parser()
        args = parser.parse_args(["snapshot", "/etc/nginx/"])
        assert args.command == "snapshot"
        assert args.path == "/etc/nginx/"

    def test_parser_snapshot_with_actor(self):
        parser = build_parser()
        args = parser.parse_args(["snapshot", "/etc/nginx/", "--actor", "root"])
        assert args.actor == "root"

    def test_parser_drift(self):
        parser = build_parser()
        args = parser.parse_args(["drift", "/etc/nginx/nginx.conf"])
        assert args.command == "drift"
        assert args.path == "/etc/nginx/nginx.conf"

    def test_parser_gauge(self):
        parser = build_parser()
        args = parser.parse_args(["gauge", "--days", "14"])
        assert args.command == "gauge"
        assert args.days == 14

    def test_parser_groundwater(self):
        parser = build_parser()
        args = parser.parse_args(["groundwater"])
        assert args.command == "groundwater"

    def test_parser_scent(self):
        parser = build_parser()
        args = parser.parse_args(["scent", "--days", "7"])
        assert args.command == "scent"
        assert args.days == 7

    def test_parser_profile(self):
        parser = build_parser()
        args = parser.parse_args(["profile", "/etc/nginx/nginx.conf", "--depth", "5"])
        assert args.command == "profile"
        assert args.depth == 5

    def test_parser_export(self):
        parser = build_parser()
        args = parser.parse_args(["export", "--format", "json", "--days", "30"])
        assert args.command == "export"
        assert args.format == "json"
        assert args.days == 30

    def test_parser_desired(self):
        parser = build_parser()
        args = parser.parse_args(["desired", "/etc/test.conf", "--hash", "abc123"])
        assert args.command == "desired"
        assert args.hash == "abc123"

    def test_parser_root(self):
        parser = build_parser()
        args = parser.parse_args(["--root", "/tmp/test", "gauge"])
        assert args.root == "/tmp/test"


class TestCLICommands:
    def test_init_command(self, tmp_dir, capsys):
        root = os.path.join(tmp_dir, "project")
        os.makedirs(root)
        parser = build_parser()
        args = parser.parse_args(["--root", root, "init", root])
        args.func(args)
        captured = capsys.readouterr()
        assert "Petrichor initialized" in captured.out

    def test_snapshot_command(self, tmp_dir, capsys):
        root = os.path.join(tmp_dir, "project")
        os.makedirs(root)
        # Create a file to snapshot
        test_file = os.path.join(root, "test.conf")
        Path(test_file).write_text("key=val\n")

        # Init first
        parser = build_parser()
        args = parser.parse_args(["--root", root, "init", root])
        args.func(args)

        # Snapshot
        args = parser.parse_args(["--root", root, "snapshot", test_file])
        result = args.func(args)
        captured = capsys.readouterr()
        assert "OK" in captured.out or "DRIFT" in captured.out

    def test_gauge_command(self, tmp_dir, capsys):
        root = os.path.join(tmp_dir, "project")
        os.makedirs(root)
        parser = build_parser()
        args = parser.parse_args(["--root", root, "gauge", "--days", "30"])
        args.func(args)
        captured = capsys.readouterr()
        assert "Rain Gauge" in captured.out

    def test_scent_command(self, tmp_dir, capsys):
        root = os.path.join(tmp_dir, "project")
        os.makedirs(root)
        parser = build_parser()
        args = parser.parse_args(["--root", root, "scent", "--days", "7"])
        args.func(args)
        captured = capsys.readouterr()
        assert "Petrichor Scent" in captured.out

    def test_export_command_json(self, tmp_dir, capsys):
        root = os.path.join(tmp_dir, "project")
        os.makedirs(root)
        parser = build_parser()
        args = parser.parse_args(["--root", root, "export", "--format", "json"])
        args.func(args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "layers" in data

    def test_export_command_text(self, tmp_dir, capsys):
        root = os.path.join(tmp_dir, "project")
        os.makedirs(root)
        parser = build_parser()
        args = parser.parse_args(["--root", root, "export", "--format", "text"])
        args.func(args)
        captured = capsys.readouterr()
        assert "Petrichor Export" in captured.out

    def test_desired_command_hash(self, tmp_dir, capsys):
        root = os.path.join(tmp_dir, "project")
        os.makedirs(root)
        parser = build_parser()
        args = parser.parse_args(["--root", root, "desired", "/etc/test.conf", "--hash", "abc123"])
        args.func(args)
        captured = capsys.readouterr()
        assert "Desired state set" in captured.out

    def test_desired_command_from_file(self, tmp_dir, capsys):
        root = os.path.join(tmp_dir, "project")
        os.makedirs(root)
        desired_file = os.path.join(root, "desired.conf")
        Path(desired_file).write_text("key=val\n")
        parser = build_parser()
        args = parser.parse_args(["--root", root, "desired", "/etc/test.conf", "--from-file", desired_file])
        args.func(args)
        captured = capsys.readouterr()
        assert "Desired state set" in captured.out

    def test_desired_command_no_args(self, tmp_dir, capsys):
        root = os.path.join(tmp_dir, "project")
        os.makedirs(root)
        parser = build_parser()
        args = parser.parse_args(["--root", root, "desired", "/etc/test.conf"])
        result = args.func(args)
        assert result == 1
