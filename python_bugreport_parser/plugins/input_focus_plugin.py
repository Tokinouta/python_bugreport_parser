import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from python_bugreport_parser.bugreport import BugreportTxt, LogcatSection
from python_bugreport_parser.plugins import (
    BasePlugin,
    BugreportAnalysisContext,
    PluginResult,
)

# Regex patterns for input focus events
INPUT_FOCUS_REQUEST = re.compile(r"\[Focus request ([\w /\.]+),reason=(\w+)\]")
INPUT_FOCUS_RECEIVE = re.compile(r"\[Focus receive :([\w /\.]+),.*\]")
INPUT_FOCUS_ENTERING = re.compile(r"\[Focus entering ([\w /\.]+)( \(server\))?,.*\]")
INPUT_FOCUS_LEAVING = re.compile(r"\[Focus leaving ([\w /\.]+)( \(server\))?,.*\]")


@dataclass
class FocusEvent:
    event_type: str  # 'request', 'receive', 'entering', 'leaving'
    focus_id: str
    component: str
    reason: str
    server: bool
    timestamp: datetime

    @staticmethod
    def parse_log_line(line: str, timestamp: datetime) -> Optional["FocusEvent"]:
        """Parse a log line to extract focus event details."""
        pattern = re.compile(
            r"^\[Focus (\w+)\s*:?\s*([^ ]+)(?: (.*?))?(?: \((server)\))?,reason=(.*?)\]$"
        )
        match = pattern.match(line.strip())
        if not match:
            return None

        event_type, focus_id, component, server_flag, reason = match.groups()
        server = server_flag == "server"

        # Clean up special focus IDs
        focus_id = focus_id.replace(":", "")  # Handle cases like ":<null>"
        component = component or focus_id  # Handle case where component is missing
        if component == "(server)":
            component = focus_id
        component.replace(" (server)", "").strip()

        return FocusEvent(
            event_type=event_type.lower(),
            focus_id=focus_id,
            component=component,
            reason=reason,
            server=server,
            timestamp=timestamp,
        )

    def __str__(self) -> str:
        return f"{self.timestamp} - {self.event_type} - {self.focus_id} - {self.component} - {self.reason} - {self.server}"


@dataclass
class InputFocusTuple:
    focus_id: str = ""
    component: str = ""
    request: Optional[FocusEvent] = None
    receive: Optional[FocusEvent] = None
    entering: Optional[FocusEvent] = None
    leaving: Optional[FocusEvent] = None
    latest_timestamp: datetime = field(default=datetime.min)
    event_count: int = field(default=0)

    def can_accept(self, event: FocusEvent) -> bool:
        """Check if event can be added to this tuple"""
        if getattr(self, event.event_type) is not None:
            return False
        return event.timestamp >= self.latest_timestamp

    def add_event(self, event: FocusEvent):
        setattr(self, event.event_type, event)
        if event.timestamp > self.latest_timestamp:
            self.latest_timestamp = event.timestamp
        if not self.focus_id and not self.component:
            self.focus_id = event.focus_id
            self.component = event.component
        self.event_count += 1

    def __str__(self):
        return (
            f"InputFocusTuple(\n"
            f"request={self.request}\n"
            f"receive={self.receive}\n"
            f"entering={self.entering}\n"
            f"leaving={self.leaving})"
        )


class InputFocusPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="InputFocusPlugin", dependencies=None)
        self.records: List[InputFocusTuple] = []
        self.result: str = ""

    def version(self) -> str:
        return "1.0.0"

    def analyze(self, analysis_context: BugreportAnalysisContext) -> None:
        """Main analysis entry point"""
        bugreport: BugreportTxt = analysis_context.bugreport.bugreport_txt
        event_log = next((s for s in bugreport.sections if s.name == "EVENT LOG"), None)
        if not event_log:
            raise ValueError("EVENT LOG section not found")
        else:
            event_log: LogcatSection = event_log.content
        focus_logs = event_log.search_by_tag("input_focus") or []

        events = []
        for line in [line for line in focus_logs if line.message.startswith("[Focus")]:
            event = FocusEvent.parse_log_line(line.message, line.timestamp)
            if event:
                events.append(event)

        # Group events into focus tuples
        self.records = InputFocusPlugin._group_focus_events(events)
        analysis_context.set_result(
            self.name,
            PluginResult(self.records, metadata={"description": "InputFocusTuples"}),
        )

    def report(self) -> str:
        return "\n".join(str(record) for record in self.records)

    @staticmethod
    def _group_focus_events(events: List[FocusEvent]) -> List[InputFocusTuple]:
        focus_map: Dict[str, List[InputFocusTuple]] = defaultdict(list)
        all_tuples: List[InputFocusTuple] = []

        for event in events:
            if event.focus_id.lower() == "<null>":
                ft = InputFocusTuple()
                ft.add_event(event)
                all_tuples.append(ft)
                continue

            candidates = []
            for ft in reversed(focus_map.get(event.focus_id, [])):
                if ft.can_accept(event):
                    candidates.append(ft)

            if candidates:
                # Select best candidate: most complete, then most recent
                best = max(
                    candidates, key=lambda x: (x.event_count, x.latest_timestamp)
                )
                best.add_event(event)
            else:
                # Create new tuple
                new_ft = InputFocusTuple()
                new_ft.add_event(event)
                focus_map[event.focus_id].append(new_ft)
                all_tuples.append(new_ft)

        sorted_completed = sorted(
            all_tuples,
            key=lambda x: x.request.timestamp if x.request else datetime.min,
        )

        return sorted_completed
