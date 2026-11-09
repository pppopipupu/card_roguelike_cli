from .base import EventOption
from ...data.locale_data import get_locale_text

class LeaveEventOption(EventOption, action="leave_event", text=get_locale_text("i18n_events_c.opt_leave")):
    def __init__(self, text: str = None, action: str = None, event_id: str = "fountain"):
        super().__init__(text, action)
        self.event_id = event_id

    def _run_effect(self, run, engine) -> str:
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_c.result_leave")
