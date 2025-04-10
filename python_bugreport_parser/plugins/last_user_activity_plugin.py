import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

from python_bugreport_parser.bugreport import BugreportTxt
from python_bugreport_parser.bugreport.section import LogcatLine, LogcatSection
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

    def __str__(self):
        return (
            f"InteractionLog(interaction_id={self.interaction_id}, "
            f"component={self.component}, "
            f"attributes={self.attributes}, "
        )


class LastUserActivityPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="LastUserActivityPlugin", dependencies=None)
        self.timestamp = datetime.now()
        self.input_interactions: List[LogcatSection] = []

    def version(self) -> str:
        return "1.0.0"

    def analyze(self, analysis_context: BugreportAnalysisContext) -> PluginResult:
        """Extract timestamp from bugreport metadata"""
        bugreport: BugreportTxt = analysis_context.bugreport.bugreport_txt
        event_log = next((s for s in bugreport.sections if s.name == "EVENT LOG"), None)
        if not event_log:
            # call the parent class analyze method
            return

        content: LogcatSection = event_log.content
        input_interactions = content.search_by_tag("input_interaction") or []
        print(
            f"Found {len(input_interactions)} input interactions, {input_interactions[0]}"
        )
        self.input_interactions = LastUserActivityPlugin._parse_log(input_interactions)
        return PluginResult(
            self.input_interactions, metadata={"description": "Interaction Log"}
        )

    def report(self) -> str:
        # Bugreport timestamp: 2024-08-16T10:02:11
        result = "\n".join([str(action) for action in self.input_interactions])
        return result

    @staticmethod
    def _split_components(s: str):
        components = []
        current = []
        brace_level = 0
        for c in s:
            if c == "{":
                brace_level += 1
            elif c == "}":
                brace_level -= 1
            if c == "," and brace_level == 0:
                components.append("".join(current).strip())
                current = []
            else:
                current.append(c)
        if current:
            components.append("".join(current).strip())
        return components

    @staticmethod
    def _parse_entity(comp: str):
        entity = {"id": None, "name": None, "server": False, "attributes": None}
        tokens = comp.split()
        if not tokens:
            return None
        if re.match(r"^[0-9a-fA-F]+$", tokens[0]):
            entity["id"] = tokens[0]
            rest = tokens[1:]
        else:
            rest = tokens.copy()
        if rest and rest[-1] == "(server)":
            entity["server"] = True
            rest = rest[:-1]
        entity["name"] = " ".join(rest)
        return entity

    @staticmethod
    def _parse_attributes(comp: str):
        s = comp[1:-1].strip()
        attributes = {}
        parts = s.split(", ")
        for part in parts:
            key_value = part.split("=", 1)
            if len(key_value) == 2:
                key, value = key_value
                attributes[key] = value
        return attributes

    @staticmethod
    def _parse_log(lines: List[LogcatLine]):
        parsed_logs = []
        for line in lines:
            message = line.message.split("Interaction with: ", 1)[1]
            components = LastUserActivityPlugin._split_components(message)
            interactions = []
            for comp in components:
                if comp.startswith("{") and comp.endswith("}"):
                    if interactions:
                        interactions[-1]["attributes"] = (
                            LastUserActivityPlugin._parse_attributes(comp)
                        )
                else:
                    entity = LastUserActivityPlugin._parse_entity(comp)
                    if entity:
                        interactions.append(entity)
            interaction = interactions[0]
            result = InteractionLog(
                interaction_id=interaction["id"],
                component=interaction["name"],
                attributes=interaction["attributes"],
            )
            parsed_logs.append(result)
        return parsed_logs

    @staticmethod
    def _parse_touchable_region(region_str: str) -> List[Tuple[int, int]]:
        return [
            tuple(map(int, coord.strip("[]").split(",")))
            for coord in region_str.split("][")
        ]
