from collections import deque
from dataclasses import dataclass
from typing import Iterable


@dataclass
class FrameDetection:
    """PPE detected in one camera frame."""

    helmet: bool = False
    vest: bool = False
    boots: bool = False
    gloves: bool = False
    goggles: bool = False

    no_helmet: bool = False
    no_vest: bool = False
    no_boots: bool = False
    no_gloves: bool = False
    no_goggles: bool = False


@dataclass
class AccessDecision:
    status: str
    helmet_frames: int
    vest_frames: int
    frames_checked: int
    reason: str


class DecisionEngine:
    """Makes stable PPE decisions using several recent video frames."""

    def __init__(
        self,
        history_size: int = 15,
        grant_threshold: int = 10,
        deny_threshold: int = 10,
        helmet_required: bool = True,
    ):
        self.history = deque(maxlen=history_size)
        self.history_size = history_size
        self.grant_threshold = grant_threshold
        self.deny_threshold = deny_threshold
        self.helmet_required = helmet_required

    def update(self, detected_classes: Iterable[str]) -> AccessDecision:
        detection = self._convert_classes(detected_classes)
        self.history.append(detection)

        return self.make_decision()

    def _convert_classes(
        self,
        detected_classes: Iterable[str],
    ) -> FrameDetection:
        classes = {name.lower() for name in detected_classes}

        return FrameDetection(
            helmet="helmet" in classes,
            vest="vest" in classes,
            boots="boots" in classes,
            gloves="gloves" in classes,
            goggles="goggles" in classes,
            no_helmet="no_helmet" in classes,
            no_vest="no_vest" in classes,
            no_boots="no_boots" in classes,
            no_gloves="no_gloves" in classes,
            no_goggles=(
                "no_goggle" in classes
                or "no_goggles" in classes
            ),
        )

    def make_decision(self) -> AccessDecision:
        frames_checked = len(self.history)

        if frames_checked < self.history_size:
            return AccessDecision(
                status="SCANNING",
                helmet_frames=0,
                vest_frames=0,
                frames_checked=frames_checked,
                reason="Collecting frames for a stable decision.",
            )

        helmet_frames = sum(frame.helmet for frame in self.history)
        vest_frames = sum(frame.vest for frame in self.history)

        no_helmet_frames = sum(
            frame.no_helmet for frame in self.history
        )

        no_vest_frames = sum(
            frame.no_vest for frame in self.history
        )

        # Approved helmet-exemption route.
        # Helmet detection is not required, but vest remains compulsory.
        if not self.helmet_required:
            if (
                vest_frames >= self.grant_threshold
                and no_vest_frames < self.deny_threshold
            ):
                return AccessDecision(
                    status="ACCESS GRANTED",
                    helmet_frames=helmet_frames,
                    vest_frames=vest_frames,
                    frames_checked=frames_checked,
                    reason=(
                        "Approved helmet exemption verified; "
                        "required hi-vis vest detected."
                    ),
                )

            if no_vest_frames >= self.deny_threshold:
                return AccessDecision(
                    status="ACCESS DENIED",
                    helmet_frames=helmet_frames,
                    vest_frames=vest_frames,
                    frames_checked=frames_checked,
                    reason=(
                        "Helmet exemption verified, but required "
                        "hi-vis vest is missing."
                    ),
                )

            return AccessDecision(
                status="MANAGER REVIEW",
                helmet_frames=helmet_frames,
                vest_frames=vest_frames,
                frames_checked=frames_checked,
                reason=(
                    "Helmet exemption verified, but vest detection "
                    "is unclear."
                ),
            )

        # Standard PPE route.
        if (
            helmet_frames >= self.grant_threshold
            and vest_frames >= self.grant_threshold
            and no_helmet_frames < self.deny_threshold
            and no_vest_frames < self.deny_threshold
        ):
            return AccessDecision(
                status="ACCESS GRANTED",
                helmet_frames=helmet_frames,
                vest_frames=vest_frames,
                frames_checked=frames_checked,
                reason="Helmet and vest detected consistently.",
            )

        if (
            no_helmet_frames >= self.deny_threshold
            or no_vest_frames >= self.deny_threshold
        ):
            missing_items = []

            if no_helmet_frames >= self.deny_threshold:
                missing_items.append("helmet")

            if no_vest_frames >= self.deny_threshold:
                missing_items.append("vest")

            return AccessDecision(
                status="ACCESS DENIED",
                helmet_frames=helmet_frames,
                vest_frames=vest_frames,
                frames_checked=frames_checked,
                reason=(
                    "Required PPE missing: "
                    + ", ".join(missing_items)
                    + "."
                ),
            )

        return AccessDecision(
            status="MANAGER REVIEW",
            helmet_frames=helmet_frames,
            vest_frames=vest_frames,
            frames_checked=frames_checked,
            reason="PPE detections are unclear or inconsistent.",
        )

    def reset(self) -> None:
        self.history.clear()