"""Focused checks for safe decision-to-gate simulator behaviour."""

from gate_controller import GateCommand, GateState, SimulatedGateController


def test_fail_safe_default() -> None:
    controller = SimulatedGateController()

    assert controller.state is GateState.LOCKED
    assert controller.last_command is GateCommand.LOCK
    assert controller.get_status()["reason"]


def test_access_granted_opens_gate() -> None:
    controller = SimulatedGateController()

    assert controller.apply_decision("ACCESS GRANTED") is GateState.OPEN
    assert controller.last_command is GateCommand.OPEN


def test_access_denied_locks_gate() -> None:
    controller = SimulatedGateController()

    assert controller.apply_decision("ACCESS DENIED") is GateState.LOCKED
    assert controller.last_command is GateCommand.LOCK


def test_manager_review_sets_review_state() -> None:
    controller = SimulatedGateController()

    assert controller.apply_decision("MANAGER REVIEW") is GateState.REVIEW
    assert controller.last_command is GateCommand.REVIEW


def test_incomplete_and_unknown_states_fail_safe_to_locked() -> None:
    controller = SimulatedGateController()

    for status in ("SCANNING", None, "CAMERA STOPPED", "ERROR", "UNKNOWN"):
        assert controller.apply_decision(status) is GateState.LOCKED
        assert controller.last_command is GateCommand.LOCK


def main() -> None:
    test_fail_safe_default()
    test_access_granted_opens_gate()
    test_access_denied_locks_gate()
    test_manager_review_sets_review_state()
    test_incomplete_and_unknown_states_fail_safe_to_locked()
    print("All gate-controller tests passed!")


if __name__ == "__main__":
    main()
