import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from parliament.cli import build_parser, main
from parliament.session import ParliamentSession


class TestCLIParser:
    def test_init_parses(self):
        parser = build_parser()
        args = parser.parse_args(["init", "./chamber"])
        assert args.command == "init"
        assert args.dir == "./chamber"

    def test_motion_create_parses(self):
        parser = build_parser()
        args = parser.parse_args(["--chamber", ".parl", "motion", "create", "--agent", "bot", "--action", "deploy"])
        assert args.command == "motion"
        assert args.motion_cmd == "create"
        assert args.agent == "bot"

    def test_motion_second_parses(self):
        parser = build_parser()
        args = parser.parse_args(["motion", "second", "MP-1", "--agent", "bot2"])
        assert args.command == "motion"
        assert args.motion_cmd == "second"
        assert args.motion_id == "MP-1"

    def test_amend_parses(self):
        parser = build_parser()
        args = parser.parse_args(["amend", "MP-1", "--agent", "bot", "--action", "rollback"])
        assert args.command == "amend"

    def test_session_call_parses(self):
        parser = build_parser()
        args = parser.parse_args(["session", "call-to-order", "MP-1", "--agents", "a1,a2"])
        assert args.command == "session"
        assert args.session_cmd == "call-to-order"
        assert args.agents == "a1,a2"

    def test_vote_open_parses(self):
        parser = build_parser()
        args = parser.parse_args(["vote", "open", "MP-1", "--method", "supermajority"])
        assert args.command == "vote"
        assert args.vote_cmd == "open"
        assert args.method == "supermajority"

    def test_vote_cast_parses(self):
        parser = build_parser()
        args = parser.parse_args(["vote", "cast", "MP-1", "--agent", "bot", "--nay"])
        assert args.aye is False

    def test_poo_parses(self):
        parser = build_parser()
        args = parser.parse_args(["point-of-order", "MP-1", "--agent", "bot", "--violation", "quorum_deficit"])
        assert args.command == "point-of-order"
        assert args.violation == "quorum_deficit"

    def test_appeal_parses(self):
        parser = build_parser()
        args = parser.parse_args(["appeal", "POO-1", "--agents", "a1,a2"])
        assert args.command == "appeal"
        assert args.agents == "a1,a2"

    def test_journal_verify_parses(self):
        parser = build_parser()
        args = parser.parse_args(["journal", "verify"])
        assert args.command == "journal"
        assert args.journal_cmd == "verify"

    def test_rules_parses(self):
        parser = build_parser()
        args = parser.parse_args(["rules"])
        assert args.command == "rules"


class TestCLIIntegration:
    def test_cli_init(self, tmp_chamber, capsys):
        main(["init", str(tmp_chamber)])
        captured = capsys.readouterr()
        assert "Initialized parliament chamber" in captured.out

    def test_cli_agent_register_and_list(self, tmp_chamber, capsys):
        main(["--chamber", str(tmp_chamber), "init", str(tmp_chamber)])
        main(["--chamber", str(tmp_chamber), "agent", "register", "bot", "orchestration", "--weight", "1.5"])
        main(["--chamber", str(tmp_chamber), "agent", "list"])
        captured = capsys.readouterr()
        assert "bot" in captured.out
        assert "orchestration" in captured.out

    def test_cli_motion_create_and_second(self, tmp_chamber, capsys):
        main(["--chamber", str(tmp_chamber), "init", str(tmp_chamber)])
        main(["--chamber", str(tmp_chamber), "agent", "register", "bot", "test"])
        main(["--chamber", str(tmp_chamber), "motion", "create", "--agent", "bot", "--action", "deploy", "--scope", "prod"])
        captured = capsys.readouterr()
        # Extract motion id from output
        lines = captured.out.splitlines()
        motion_line = [l for l in lines if l.startswith("Motion #")][0]
        motion_id = motion_line.split()[1].lstrip("#")
        main(["--chamber", str(tmp_chamber), "motion", "second", motion_id, "--agent", "bot"])
        captured2 = capsys.readouterr()
        assert "seconded" in captured2.out.lower()

    def test_cli_motion_status(self, tmp_chamber, capsys):
        main(["--chamber", str(tmp_chamber), "init", str(tmp_chamber)])
        main(["--chamber", str(tmp_chamber), "agent", "register", "bot", "test"])
        main(["--chamber", str(tmp_chamber), "motion", "create", "--agent", "bot", "--action", "deploy"])
        captured = capsys.readouterr()
        lines = captured.out.splitlines()
        motion_id = [l for l in lines if l.startswith("Motion #")][0].split()[1].lstrip("#")
        main(["--chamber", str(tmp_chamber), "motion", "status", motion_id])
        captured2 = capsys.readouterr()
        assert "DOCKET" in captured2.out

    def test_cli_rules(self, capsys):
        main(["rules"])
        captured = capsys.readouterr()
        assert "quorum_required_before_vote" in captured.out

    def test_cli_journal_verify(self, tmp_chamber, capsys):
        main(["--chamber", str(tmp_chamber), "init", str(tmp_chamber)])
        main(["--chamber", str(tmp_chamber), "journal", "verify"])
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_cli_aminute_generation(self, tmp_chamber, capsys):
        main(["--chamber", str(tmp_chamber), "init", str(tmp_chamber)])
        main(["--chamber", str(tmp_chamber), "agent", "register", "bot", "test"])
        main(["--chamber", str(tmp_chamber), "motion", "create", "--agent", "bot", "--action", "deploy"])
        captured = capsys.readouterr()
        motion_id = [l for l in captured.out.splitlines() if l.startswith("Motion #")][0].split()[1].lstrip("#")
        main(["--chamber", str(tmp_chamber), "minutes", motion_id])
        captured2 = capsys.readouterr()
        assert "Minutes for Session" in captured2.out

    def test_cli_vote_full_cycle(self, tmp_chamber, capsys):
        main(["--chamber", str(tmp_chamber), "init", str(tmp_chamber)])
        for a in ["bot", "bot2"]:
            main(["--chamber", str(tmp_chamber), "agent", "register", a, "test"])
        main(["--chamber", str(tmp_chamber), "motion", "create", "--agent", "bot", "--action", "deploy", "--scope", "prod"])
        captured = capsys.readouterr()
        motion_id = [l for l in captured.out.splitlines() if l.startswith("Motion #")][0].split()[1].lstrip("#")
        main(["--chamber", str(tmp_chamber), "motion", "second", motion_id, "--agent", "bot2"])
        main(["--chamber", str(tmp_chamber), "vote", "open", motion_id])
        main(["--chamber", str(tmp_chamber), "vote", "cast", motion_id, "--agent", "bot", "--aye"])
        main(["--chamber", str(tmp_chamber), "vote", "cast", motion_id, "--agent", "bot2", "--aye"])
        main(["--chamber", str(tmp_chamber), "vote", "close", motion_id])
        captured2 = capsys.readouterr()
        assert "CARRIED" in captured2.out

    def test_cli_point_of_order(self, tmp_chamber, capsys):
        main(["--chamber", str(tmp_chamber), "init", str(tmp_chamber)])
        main(["--chamber", str(tmp_chamber), "agent", "register", "bot", "test"])
        main(["--chamber", str(tmp_chamber), "motion", "create", "--agent", "bot", "--action", "deploy"])
        captured = capsys.readouterr()
        motion_id = [l for l in captured.out.splitlines() if l.startswith("Motion #")][0].split()[1].lstrip("#")
        main(["--chamber", str(tmp_chamber), "point-of-order", motion_id, "--agent", "bot", "--violation", "quorum_deficit"])
        captured2 = capsys.readouterr()
        assert "Point of Order raised" in captured2.out

    def test_cli_amend(self, tmp_chamber, capsys):
        main(["--chamber", str(tmp_chamber), "init", str(tmp_chamber)])
        main(["--chamber", str(tmp_chamber), "agent", "register", "bot", "test"])
        main(["--chamber", str(tmp_chamber), "motion", "create", "--agent", "bot", "--action", "deploy", "--scope", "prod"])
        captured = capsys.readouterr()
        motion_id = [l for l in captured.out.splitlines() if l.startswith("Motion #")][0].split()[1].lstrip("#")
        main(["--chamber", str(tmp_chamber), "motion", "second", motion_id, "--agent", "bot"])
        main(["--chamber", str(tmp_chamber), "amend", motion_id, "--agent", "bot", "--action", "rollback", "--scope", "prod"])
        captured2 = capsys.readouterr()
        assert "Amendment #" in captured2.out


class TestCLISubprocess:
    def test_python_module_invocation(self, tmp_chamber):
        env = os.environ.copy()
        env["PARLIAMENT_CHAMBER"] = str(tmp_chamber)
        result = subprocess.run(
            [sys.executable, "-m", "parliament", "init", str(tmp_chamber)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            env=env,
        )
        assert result.returncode == 0
        assert "Initialized parliament chamber" in result.stdout
