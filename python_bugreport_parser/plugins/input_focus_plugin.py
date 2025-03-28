import re
from dataclasses import dataclass
from typing import List, Optional
from python_bugreport_parser.bugreport import BugreportTxt, LogcatLine, LogcatSection
from python_bugreport_parser.plugins import BasePlugin

# Regex patterns for input focus events
INPUT_FOCUS_REQUEST = re.compile(r"\[Focus request ([\w /\.]+),reason=(\w+)\]")
INPUT_FOCUS_RECEIVE = re.compile(r"\[Focus receive :([\w /\.]+),.*\]")
INPUT_FOCUS_ENTERING = re.compile(r"\[Focus entering ([\w /\.]+)( \(server\))?,.*\]")
INPUT_FOCUS_LEAVING = re.compile(r"\[Focus leaving ([\w /\.]+)( \(server\))?,.*\]")


@dataclass
class InputFocusTuple:
    request: Optional[LogcatLine] = None
    receive: Optional[LogcatLine] = None
    entering: Optional[LogcatLine] = None
    leaving: Optional[LogcatLine] = None


class InputFocusPlugin(BasePlugin):
    def __init__(self):
        self.records: List[InputFocusTuple] = []
        self.result: str = ""

    def name(self) -> str:
        return "InputFocusPlugin"

    def version(self) -> str:
        return "1.0.0"

    def analyze(self, bugreport: BugreportTxt) -> None:
        """Main analysis entry point"""
        event_log = next((s for s in bugreport.sections if s.name == "EVENT LOG"), None)
        if not event_log:
            raise ValueError("EVENT LOG section not found")

        self._pair_input_focus(event_log.content)

    def report(self) -> str:
        return self.result

    def _pair_input_focus(self, section: LogcatSection) -> None:
        """Process input focus events in section"""
        focus_logs = section.search_by_tag("input_focus") or []

        # Find all focus requests
        requests = [
            (idx, line)
            for idx, line in enumerate(focus_logs)
            if "Focus request" in line.message
        ]

        for req_idx, req_line in requests:
            window = self._extract_window(req_line.message)
            self.result += f"window: {window}\n"

            current_tuple = InputFocusTuple(request=req_line)

            # Search subsequent logs for related events
            for line in focus_logs[req_idx + 1 :]:
                if not current_tuple.receive:
                    current_tuple.receive = self._match_receive(line, window)

                if not current_tuple.entering:
                    current_tuple.entering = self._match_entering(line, window)

                if not current_tuple.leaving:
                    current_tuple.leaving = self._match_leaving(line, window)

                if all(
                    [
                        current_tuple.receive,
                        current_tuple.entering,
                        current_tuple.leaving,
                    ]
                ):
                    break

            self.records.append(current_tuple)

        # print(f"Processed {len(self.records)} input focus records")

    def _extract_window(self, message: str) -> str:
        """Extract window name from focus request"""
        match = INPUT_FOCUS_REQUEST.search(message)
        return match.group(1) if match else ""

    def _match_receive(self, line: LogcatLine, window: str) -> Optional[LogcatLine]:
        match = INPUT_FOCUS_RECEIVE.search(line.message)
        return line if match and match.group(1) == window else None

    def _match_entering(self, line: LogcatLine, window: str) -> Optional[LogcatLine]:
        match = INPUT_FOCUS_ENTERING.search(line.message)
        return line if match and match.group(1) == window else None

    def _match_leaving(self, line: LogcatLine, window: str) -> Optional[LogcatLine]:
        match = INPUT_FOCUS_LEAVING.search(line.message)
        return line if match and match.group(1) == window else None
