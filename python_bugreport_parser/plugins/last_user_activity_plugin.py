import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

from python_bugreport_parser.bugreport import BugreportTxt
from python_bugreport_parser.bugreport.section import LogcatSection
from python_bugreport_parser.plugins import (
    BasePlugin,
    BugreportAnalysisContext,
    PluginResult,
)


@dataclass
class Flags:
    not_touchable: bool
    not_focusable: bool
    not_touch_modal: bool

    def __str__(self):
        return (
            f"Flags(not_touchable={self.not_touchable}, "
            f"not_focusable={self.not_focusable}, "
            f"not_touch_modal={self.not_touch_modal})"
        )


@dataclass
class Attributes:
    touchable_region: List[Tuple[int, int]]
    visible: bool
    trusted_overlay: bool
    flags: Flags

    def __str__(self):
        return (
            f"Attributes(touchable_region={self.touchable_region}, "
            f"visible={self.visible}, "
            f"trusted_overlay={self.trusted_overlay}, "
            f"flags={self.flags})"
        )


@dataclass
class InteractionLog:
    interaction_id: str
    component: str
    attributes: Attributes
    gesture_monitor: str
    pointer_dispatcher: str

    def __str__(self):
        return (
            f"InteractionLog(interaction_id={self.interaction_id}, "
            f"component={self.component}, "
            f"attributes={self.attributes}, "
            f"gesture_monitor={self.gesture_monitor}, "
            f"pointer_dispatcher={self.pointer_dispatcher})"
        )


class LastUserActivityPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="LastUserActivityPlugin", dependencies=None)
        self.timestamp = datetime.now()
        self.input_interactions: List[LogcatSection] = []

    def version(self) -> str:
        return "1.0.0"

    def analyze(self, analysis_context: BugreportAnalysisContext) -> None:
        """Extract timestamp from bugreport metadata"""
        bugreport: BugreportTxt = analysis_context.bugreport.bugreport_txt
        event_log = next((s for s in bugreport.sections if s.name == "EVENT LOG"), None)
        if not event_log:
            # call the parent class analyze method
            return

        # super().analyze(bugreport)
        content: LogcatSection = event_log.content
        input_interactions = content.search_by_tag("input_interaction") or []
        print(
            f"Found {len(input_interactions)} input interactions, {input_interactions[0]}"
        )
        for line in input_interactions:
            parsed_line = LastUserActivityPlugin._parse_log_line(line.message)
            if parsed_line:
                self.input_interactions.append(parsed_line)
            else:
                print(f"Failed to parse line: {line.message}")

        # self.input_interactions = input_interactions
        analysis_context.set_result(
            self.name,
            PluginResult(
                self.input_interactions, metadata={"description": "Interaction Log"}
            ),
        )

    def report(self) -> str:
        # Bugreport timestamp: 2024-08-16T10:02:11
        result = "\n".join([str(action) for action in self.input_interactions])
        return result

    @staticmethod
    def _parse_log_line(line: str):
        # Main line pattern to extract components
        line_pattern = re.compile(
            r"^Interaction with: (\S+) (.*?) \(server\),\s*\{(.*?)\},\s*(.*?),\s*(.*?),?$"
        )
        match = line_pattern.match(line.strip())
        if not match:
            return None

        (
            interaction_id,
            component,
            attributes_str,
            gesture_monitor,
            pointer_dispatcher,
        ) = match.groups()

        # Parse attributes section
        attributes = {}
        for part in LastUserActivityPlugin.split_attributes(attributes_str):
            key_match = re.match(r"(\w+)(?:=([^=]+)$|\[([^\]]+)\])", part)
            if key_match:
                key = key_match.group(1)
                value = key_match.group(2) or key_match.group(3)

                if key == "flags":
                    flags = {}
                    for flag in [f.strip() for f in value.split(", ")]:
                        if "=" in flag:
                            k, v = flag.split("=", 1)
                            flags[k] = v
                    attributes[key] = flags
                else:
                    attributes[key] = value

        return InteractionLog(
            interaction_id=interaction_id,
            component=component,
            attributes=Attributes(
                touchable_region=LastUserActivityPlugin._parse_touchable_region(
                    attributes["touchableRegion"]
                ),
                visible=attributes["visible"].lower() == "true",
                trusted_overlay=attributes["trustedOverlay"].lower() == "true",
                flags=Flags(
                    not_touchable=attributes["flags"]["NOT_TOUCHABLE"].lower()
                    == "true",
                    not_focusable=attributes["flags"]["NOT_FOCUSABLE"].lower()
                    == "true",
                    not_touch_modal=attributes["flags"]["NOT_TOUCH_MODAL"].lower()
                    == "true",
                ),
            ),
            gesture_monitor=gesture_monitor,
            pointer_dispatcher=pointer_dispatcher,
        )

    @staticmethod
    def split_attributes(s):
        parts = []
        current = []
        bracket_depth = 0

        for char in s:
            if char == "[":
                bracket_depth += 1
            elif char == "]":
                bracket_depth -= 1

            if char == "," and bracket_depth == 0:
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(char)

        if current:
            parts.append("".join(current).strip())

        return parts

    @staticmethod
    def _parse_touchable_region(region_str: str) -> List[Tuple[int, int]]:
        return [
            tuple(map(int, coord.strip("[]").split(",")))
            for coord in region_str.split("][")
        ]
