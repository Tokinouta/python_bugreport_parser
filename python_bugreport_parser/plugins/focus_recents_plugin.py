from datetime import datetime
from typing import List
from python_bugreport_parser.bugreport import BugreportTxt
from python_bugreport_parser.plugins import (
    BasePlugin,
    BugreportAnalysisContext,
    PluginResult,
)
from python_bugreport_parser.plugins.input_focus_plugin import InputFocusTuple


class FocusRecentsPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="FocusRecentsPlugin", dependencies=["InputFocusPlugin"])
        self.possibly_stucked: bool = False

    def version(self) -> str:
        return "1.0.0"

    def analyze(self, analysis_context: BugreportAnalysisContext) -> None:
        """Extract timestamp from bugreport metadata"""
        bugreport: BugreportTxt = analysis_context.bugreport.bugreport_txt
        error_timestamp = bugreport.error_timestamp

        focus_records: List[InputFocusTuple] = None
        if not analysis_context.get_result("InputFocusPlugin"):
            print("Result from InputFocusPlugin not found")
            return
        else:
            focus_records = analysis_context.get_result("InputFocusPlugin").data

        for record in focus_records:
            if (
                record.focus_id != "recents_animation_input_consumer"
                or not record.request
                or abs(record.request.timestamp < error_timestamp).total_seconds() > 3
            ):
                continue

            stay_too_long = False
            not_leaving = False
            if record.entering and record.leaving:
                stay_too_long = (
                    record.leaving.timestamp - record.entering.timestamp
                ).total_seconds() >= 3
            elif record.entering:
                not_leaving = True

            self.possibly_stucked = stay_too_long or not_leaving

        analysis_context.set_result(
            self.name,
            PluginResult(
                "Possibly stuck in recents_animation_input_consumer",
                metadata={"description": "Bugreport timestamp"},
            ),
        )
        # print(f"Analyzed timestamps: {self.timestamp}")

    def report(self) -> str:
        if self.possibly_stucked:
            return f"FocusRecentsPlugin: staying at recents_animation_input_consumer too long or not leaving"
        else:
            return f"FocusRecentsPlugin: no issues found"
