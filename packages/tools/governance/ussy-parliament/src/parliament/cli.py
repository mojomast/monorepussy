"""CLI interface for Parliament using argparse."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from parliament.models import MotionStatus, ViolationType, VoteMethod
from parliament.session import ParliamentSession


def get_default_chamber() -> str:
    return os.environ.get("PARLIAMENT_CHAMBER", ".parliament")


def cmd_init(args):
    chamber_dir = Path(args.dir)
    session = ParliamentSession(chamber_dir)
    session.init_chamber()
    print(f"Initialized parliament chamber at {chamber_dir.resolve()}")


def cmd_agent_register(args):
    session = ParliamentSession(args.chamber)
    session.register_agent(
        agent_id=args.agent_id,
        agent_type=args.agent_type,
        base_weight=getattr(args, "weight", 1.0),
        public_key=getattr(args, "pubkey", None),
    )
    print(f"Registered agent {args.agent_id} ({args.agent_type})")


def cmd_agent_list(args):
    session = ParliamentSession(args.chamber)
    agents = session.store.list_agents()
    if not agents:
        print("No agents registered.")
        return
    for a in agents:
        status = "active" if a.active else "inactive"
        print(f"{a.agent_id} ({a.agent_type}) weight={a.weight:.2f} [{status}]")


def cmd_motion_create(args):
    session = ParliamentSession(args.chamber)
    scope = set(args.scope.split(",")) if getattr(args, "scope", None) else set()
    criticality = {}
    if getattr(args, "criticality", None):
        for item in args.criticality.split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                criticality[k] = float(v)
    method_str = getattr(args, "method", "majority")
    method = VoteMethod(method_str)
    motion = session.create_motion(
        agent_id=args.agent,
        action=args.action,
        scope=scope,
        criticality_map=criticality,
        vote_method=method,
    )
    print(f"Motion #{motion.motion_id} introduced by {args.agent}")
    print(f"  Scope: {', '.join(motion.scope) if motion.scope else '(none)'}")
    print(f"  Impact score: {motion.impact_score:.1f}")
    print(f"  Required seconds: {motion.required_seconds}")
    print(f"  Status: {motion.status.value.upper()}")
    print(f"  Current seconds: {len(motion.seconders)}/{motion.required_seconds}")


def cmd_motion_second(args):
    session = ParliamentSession(args.chamber)
    motion = session.second_motion(args.motion_id, args.agent)
    print(f"Motion #{args.motion_id} seconded by {args.agent}")
    print(f"  Current seconds: {len(motion.seconders)}/{motion.required_seconds}")
    if motion.status == MotionStatus.FLOOR:
        print(f"  Status: FLOOR (graduated)")


def cmd_motion_status(args):
    session = ParliamentSession(args.chamber)
    motion = session.motion_engine.get_motion(args.motion_id)
    if not motion:
        print(f"Motion {args.motion_id} not found")
        sys.exit(1)
    print(f"Motion #{motion.motion_id}")
    print(f"  Agent: {motion.agent_id}")
    print(f"  Action: {motion.action}")
    print(f"  Status: {motion.status.value.upper()}")
    print(f"  Scope: {', '.join(motion.scope) if motion.scope else '(none)'}")
    print(f"  Impact: {motion.impact_score:.1f}")
    print(f"  Seconds: {len(motion.seconders)}/{motion.required_seconds}")
    print(f"  Seconders: {', '.join(motion.seconders) if motion.seconders else '(none)'}")
    print(f"  Vote method: {motion.vote_method.value}")
    print(f"  Criticality tier: {motion.criticality_tier}")


def cmd_motion_list(args):
    session = ParliamentSession(args.chamber)
    motions = session.motion_engine.list_motions()
    if not motions:
        print("No motions.")
        return
    for m in motions:
        print(f"{m.motion_id} [{m.status.value:12}] {m.action} ({len(m.seconders)}/{m.required_seconds} seconds)")


def cmd_amend(args):
    session = ParliamentSession(args.chamber)
    scope = set(args.scope.split(",")) if getattr(args, "scope", None) else set()
    criticality = {}
    if getattr(args, "criticality", None):
        for item in args.criticality.split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                criticality[k] = float(v)
    amendment = session.propose_amendment(
        original_motion_id=args.motion_id,
        agent_id=args.agent,
        action=args.action,
        scope=scope,
        criticality_map=criticality,
    )
    print(f"Amendment #{amendment.motion_id} proposed to Motion #{args.motion_id}")
    print(f"  Action: {amendment.action}")
    print(f"  Status: {amendment.status.value.upper()}")


def cmd_amend_second(args):
    session = ParliamentSession(args.chamber)
    motion = session.second_amendment(args.amendment_id, args.agent)
    print(f"Amendment #{args.amendment_id} seconded by {args.agent}")
    if motion.status == MotionStatus.FLOOR:
        print(f"  Status: FLOOR (graduated)")


def cmd_tree(args):
    session = ParliamentSession(args.chamber)
    tree = session.amendment_engine.get_amendment_tree(args.motion_id)
    print(f"Motion #{tree['motion_id']} Amendment Tree")
    print(f"├── Original: \"{tree['action']}\" [{tree['status']}]")
    for child in tree["children"]:
        print(f"└── {child['motion_id']}: \"{child['action']}\" [{child['status']}] (depth {child['depth']})")


def cmd_session_call(args):
    session = ParliamentSession(args.chamber)
    agents_present = set(args.agents.split(",")) if getattr(args, "agents", None) else set()
    sess = session.call_to_order(args.motion_id, agents_present)
    print(f"Call to Order for Motion #{args.motion_id}")
    print(f"  Required quorum: {sess.quorum_required}")
    print(f"  Present: {len(sess.agents_present)}")
    print(f"  Quorum verified: {'YES' if sess.quorum_verified else 'NO'}")


def cmd_session_join(args):
    session = ParliamentSession(args.chamber)
    sess = session.quorum_engine.join_session(args.session_id, args.agent)
    print(f"Agent {args.agent} joined session {args.session_id}")
    print(f"  Present: {len(sess.agents_present)}/{sess.quorum_required}")
    print(f"  Quorum: {'YES' if sess.quorum_verified else 'NO'}")


def cmd_vote_open(args):
    session = ParliamentSession(args.chamber)
    method_str = getattr(args, "method", None)
    method = VoteMethod(method_str) if method_str else None
    motion = session.open_voting(args.motion_id, method)
    print(f"Voting opened for Motion #{args.motion_id}")
    print(f"  Method: {motion.vote_method.value}")


def cmd_vote_cast(args):
    session = ParliamentSession(args.chamber)
    session.cast_vote(args.motion_id, args.agent, args.aye)
    print(f"Vote cast by {args.agent} on Motion #{args.motion_id}: {'AYE' if args.aye else 'NAY'}")


def cmd_vote_close(args):
    session = ParliamentSession(args.chamber)
    result = session.close_voting(args.motion_id)
    print(f"Voting closed for Motion #{args.motion_id}")
    print(f"  Tally: {result.tally*100:.1f}% AYE")
    print(f"  Threshold: {result.method.value}")
    print(f"  Result: {'CARRIED' if result.passes else 'FAILED'}")


def cmd_poo(args):
    session = ParliamentSession(args.chamber)
    evidence = {}
    if getattr(args, "evidence", None):
        evidence = json.loads(args.evidence)
    poo = session.raise_point_of_order(
        motion_id=args.motion_id,
        violation_type=ViolationType(args.violation),
        claimant=args.agent,
        evidence=evidence,
    )
    print(f"Point of Order raised: {poo.poo_id}")
    print(f"  Violation: {poo.violation_type.value}")
    print(f"  Claimant: {poo.claimant}")


def cmd_rule(args):
    session = ParliamentSession(args.chamber)
    poo = session.rule_on_point(args.poo_id)
    print(f"Ruling on {args.poo_id}")
    print(f"  Sustained: {'YES' if poo.sustained else 'NO'}")
    if poo.remedy:
        print(f"  Remedy: {poo.remedy}")


def cmd_appeal(args):
    session = ParliamentSession(args.chamber)
    appeal = session.file_appeal(args.poo_id, args.agents.split(","))
    print(f"Appeal filed: {appeal.appeal_id}")
    print(f"  Appealers: {', '.join(appeal.appealers)}")


def cmd_appeal_vote(args):
    session = ParliamentSession(args.chamber)
    from parliament.models import Vote
    votes = []
    for spec in args.votes:
        # format: agent_id:aye|nay
        agent_id, vote_str = spec.split(":")
        aye = vote_str.lower() in ("aye", "yes", "true", "1")
        votes.append(Vote(agent_id=agent_id, aye=aye))
    appeal = session.vote_appeal(args.appeal_id, votes)
    print(f"Appeal {args.appeal_id} outcome: {appeal.outcome.value if appeal.outcome else 'PENDING'}")


def cmd_journal_view(args):
    session = ParliamentSession(args.chamber)
    entries = session.journal_engine.view_session(args.session_id)
    if not entries:
        print("No entries.")
        return
    for entry in entries:
        print(f"[{entry.hash.hex()[:12]}] {entry.timestamp.isoformat()}  {entry.entry_type.value.upper()}")
        try:
            data = json.loads(entry.data.decode("utf-8"))
            for k, v in data.items():
                print(f"  {k}: {v}")
        except Exception:
            pass


def cmd_journal_verify(args):
    session = ParliamentSession(args.chamber)
    ok = session.journal_engine.verify()
    length = session.journal_engine.chain_length()
    head = session.journal_engine.last_entry()
    print(f"Journal integrity check: {'PASS' if ok else 'FAIL'}")
    print(f"  Chain length: {length}")
    if head:
        print(f"  Head hash: {head.hash.hex()[:16]}")
    if ok:
        print("  All hashes valid ✓")
        print("  No gaps detected ✓")
    else:
        print("  Chain broken!")
        sys.exit(1)


def cmd_minutes(args):
    session = ParliamentSession(args.chamber)
    minutes = session.generate_minutes(args.session_id)
    print(minutes)


def cmd_rules(args):
    rules = [
        "quorum_required_before_vote",
        "germaneness_required_for_amendment",
        "seconding_required_for_motion",
        "voting_method_matches_criticality",
        "no_double_voting",
    ]
    print("Active Procedural Rules")
    print("-" * 40)
    for r in rules:
        print(f"  • {r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="parliament", description="Parliamentary Procedure for Agent Self-Governance")
    parser.add_argument("--chamber", default=get_default_chamber(), help="Chamber directory")
    subparsers = parser.add_subparsers(dest="command")

    # init
    p_init = subparsers.add_parser("init", help="Initialize a parliament chamber")
    p_init.add_argument("dir", nargs="?", default=".parliament", help="Chamber directory")

    # agent
    p_agent = subparsers.add_parser("agent", help="Agent management")
    agent_sub = p_agent.add_subparsers(dest="agent_cmd")
    p_agent_reg = agent_sub.add_parser("register", help="Register an agent")
    p_agent_reg.add_argument("agent_id")
    p_agent_reg.add_argument("agent_type")
    p_agent_reg.add_argument("--weight", type=float, default=1.0)
    p_agent_reg.add_argument("--pubkey", default=None)
    p_agent_list = agent_sub.add_parser("list", help="List agents")

    # motion
    p_motion = subparsers.add_parser("motion", help="Motion management")
    motion_sub = p_motion.add_subparsers(dest="motion_cmd")
    p_mcreate = motion_sub.add_parser("create", help="Create a motion")
    p_mcreate.add_argument("--agent", required=True)
    p_mcreate.add_argument("--action", required=True)
    p_mcreate.add_argument("--scope", default=None)
    p_mcreate.add_argument("--criticality", default=None)
    p_mcreate.add_argument("--method", default="majority", choices=["majority", "supermajority", "consensus"])
    p_msecond = motion_sub.add_parser("second", help="Second a motion")
    p_msecond.add_argument("motion_id")
    p_msecond.add_argument("--agent", required=True)
    p_mstatus = motion_sub.add_parser("status", help="Show motion status")
    p_mstatus.add_argument("motion_id")
    p_mlist = motion_sub.add_parser("list", help="List motions")

    # amend
    p_amend = subparsers.add_parser("amend", help="Propose an amendment")
    p_amend.add_argument("motion_id")
    p_amend.add_argument("--agent", required=True)
    p_amend.add_argument("--action", required=True)
    p_amend.add_argument("--scope", default=None)
    p_amend.add_argument("--criticality", default=None)

    p_amend_second = subparsers.add_parser("amend-second", help="Second an amendment")
    p_amend_second.add_argument("amendment_id")
    p_amend_second.add_argument("--agent", required=True)

    # tree
    p_tree = subparsers.add_parser("tree", help="Show amendment tree")
    p_tree.add_argument("motion_id")

    # session
    p_session = subparsers.add_parser("session", help="Session management")
    session_sub = p_session.add_subparsers(dest="session_cmd")
    p_scall = session_sub.add_parser("call-to-order", help="Call to order")
    p_scall.add_argument("motion_id")
    p_scall.add_argument("--agents", default=None)
    p_sjoin = session_sub.add_parser("join", help="Join session")
    p_sjoin.add_argument("session_id")
    p_sjoin.add_argument("--agent", required=True)

    # vote
    p_vote = subparsers.add_parser("vote", help="Voting")
    vote_sub = p_vote.add_subparsers(dest="vote_cmd")
    p_vopen = vote_sub.add_parser("open", help="Open voting")
    p_vopen.add_argument("motion_id")
    p_vopen.add_argument("--method", choices=["majority", "supermajority", "consensus"], default=None)
    p_vcast = vote_sub.add_parser("cast", help="Cast a vote")
    p_vcast.add_argument("motion_id")
    p_vcast.add_argument("--agent", required=True)
    p_vcast.add_argument("--aye", action="store_true", default=True)
    p_vcast.add_argument("--nay", dest="aye", action="store_false")
    p_vclose = vote_sub.add_parser("close", help="Close voting")
    p_vclose.add_argument("motion_id")

    # point of order
    p_poo = subparsers.add_parser("point-of-order", help="Raise a point of order")
    p_poo.add_argument("motion_id")
    p_poo.add_argument("--agent", required=True)
    p_poo.add_argument("--violation", required=True)
    p_poo.add_argument("--evidence", default=None)

    # rule
    p_rule = subparsers.add_parser("rule", help="Rule on a point of order")
    p_rule.add_argument("poo_id")

    # appeal
    p_appeal = subparsers.add_parser("appeal", help="File an appeal")
    p_appeal.add_argument("poo_id")
    p_appeal.add_argument("--agents", required=True)

    p_appeal_vote = subparsers.add_parser("appeal-vote", help="Vote on an appeal")
    p_appeal_vote.add_argument("appeal_id")
    p_appeal_vote.add_argument("--votes", nargs="+", required=True)

    # journal
    p_journal = subparsers.add_parser("journal", help="Journal management")
    journal_sub = p_journal.add_subparsers(dest="journal_cmd")
    p_jview = journal_sub.add_parser("view", help="View journal entries")
    p_jview.add_argument("session_id")
    p_jverify = journal_sub.add_parser("verify", help="Verify journal integrity")

    # minutes
    p_minutes = subparsers.add_parser("minutes", help="Generate minutes")
    p_minutes.add_argument("session_id")

    # rules
    p_rules = subparsers.add_parser("rules", help="Show active procedural rules")

    return parser


def main(argv: Optional[list] = None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        cmd_init(args)
    elif args.command == "agent":
        cmd = getattr(args, "agent_cmd", None)
        if cmd == "register":
            cmd_agent_register(args)
        elif cmd == "list":
            cmd_agent_list(args)
        else:
            parser.parse_args(["agent", "--help"])
    elif args.command == "motion":
        cmd = getattr(args, "motion_cmd", None)
        if cmd == "create":
            cmd_motion_create(args)
        elif cmd == "second":
            cmd_motion_second(args)
        elif cmd == "status":
            cmd_motion_status(args)
        elif cmd == "list":
            cmd_motion_list(args)
        else:
            parser.parse_args(["motion", "--help"])
    elif args.command == "amend":
        cmd_amend(args)
    elif args.command == "amend-second":
        cmd_amend_second(args)
    elif args.command == "tree":
        cmd_tree(args)
    elif args.command == "session":
        cmd = getattr(args, "session_cmd", None)
        if cmd == "call-to-order":
            cmd_session_call(args)
        elif cmd == "join":
            cmd_session_join(args)
        else:
            parser.parse_args(["session", "--help"])
    elif args.command == "vote":
        cmd = getattr(args, "vote_cmd", None)
        if cmd == "open":
            cmd_vote_open(args)
        elif cmd == "cast":
            cmd_vote_cast(args)
        elif cmd == "close":
            cmd_vote_close(args)
        else:
            parser.parse_args(["vote", "--help"])
    elif args.command == "point-of-order":
        cmd_poo(args)
    elif args.command == "rule":
        cmd_rule(args)
    elif args.command == "appeal":
        cmd_appeal(args)
    elif args.command == "appeal-vote":
        cmd_appeal_vote(args)
    elif args.command == "journal":
        cmd = getattr(args, "journal_cmd", None)
        if cmd == "view":
            cmd_journal_view(args)
        elif cmd == "verify":
            cmd_journal_verify(args)
        else:
            parser.parse_args(["journal", "--help"])
    elif args.command == "minutes":
        cmd_minutes(args)
    elif args.command == "rules":
        cmd_rules(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
