from __future__ import annotations

from typing import Any, cast

from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update

from components.base import BaseComponent, PreloadedFullScreenMixin
from utils.dates import local_today
from utils.styles import COLORS

from .constants import TASKS_REFRESH_INTERVAL_MS
from .data import TaskRecurrence, TaskStore
from .full_screen import render_tasks_fullscreen
from .summary import render_tasks_summary


class Tasks(PreloadedFullScreenMixin, BaseComponent):
    def __init__(self, **kwargs):
        super().__init__(name="tasks", **kwargs)
        self.store = TaskStore()

    def _summary_layout(self):
        snapshot = self.store.load()
        title, content = self._full_screen_parts(snapshot)
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval",
                    interval=TASKS_REFRESH_INTERVAL_MS,
                    n_intervals=0,
                ),
                dcc.Store(id=f"{self.component_id}-feedback", data=None),
                *self.preload_fullscreen_stores(title=title, content=content),
                html.Div(
                    id=f"{self.component_id}-content",
                    children=render_tasks_summary(snapshot),
                    className="mm-fade-in",
                    style={"width": "100%", "color": COLORS["text"]},
                ),
            ],
        )

    def _add_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Output(self.fullscreen_title_store_id(), "data"),
            Output(self.fullscreen_content_store_id(), "data"),
            Output(f"{self.component_id}-feedback", "data"),
            Output(f"{self.component_id}-person-name", "value"),
            Output(f"{self.component_id}-task-title", "value"),
            Output(f"{self.component_id}-task-person", "value"),
            Output(f"{self.component_id}-task-due-on", "value"),
            Output(f"{self.component_id}-task-recurrence", "value"),
            Input(f"{self.component_id}-interval", "n_intervals"),
            Input(f"{self.component_id}-add-person", "n_clicks"),
            Input(f"{self.component_id}-add-task", "n_clicks"),
            Input(
                {"type": f"{self.component_id}-complete-task", "task_id": ALL},
                "n_clicks",
            ),
            State(f"{self.component_id}-person-name", "value"),
            State(f"{self.component_id}-task-title", "value"),
            State(f"{self.component_id}-task-person", "value"),
            State(f"{self.component_id}-task-due-on", "value"),
            State(f"{self.component_id}-task-recurrence", "value"),
            State(f"{self.component_id}-feedback", "data"),
            prevent_initial_call=False,
        )
        def sync_task_views(
            _interval,
            _add_person_clicks,
            _add_task_clicks,
            _complete_clicks,
            person_name,
            task_title,
            task_person,
            task_due_on,
            task_recurrence,
            current_feedback,
        ):
            feedback = current_feedback
            next_person_name = no_update
            next_task_title = no_update
            next_task_person = no_update
            next_due_on = no_update
            next_recurrence = no_update

            try:
                triggered = ctx.triggered_id
                if triggered == f"{self.component_id}-add-person":
                    snapshot = self.store.add_person(person_name or "")
                    new_person = snapshot.people[-1] if snapshot.people else None
                    feedback = (
                        {"tone": "success", "message": f"Added {new_person.name}."}
                        if new_person
                        else None
                    )
                    next_person_name = ""
                    if new_person is not None:
                        next_task_person = new_person.id
                elif triggered == f"{self.component_id}-add-task":
                    snapshot = self.store.add_task(
                        title=task_title or "",
                        person_id=task_person or "",
                        due_on=task_due_on or "",
                        recurrence=task_recurrence or TaskRecurrence.ONCE.value,
                    )
                    feedback = {"tone": "success", "message": "Task added."}
                    next_task_title = ""
                    next_due_on = local_today().isoformat()
                    next_recurrence = TaskRecurrence.ONCE.value
                elif (
                    isinstance(triggered, dict)
                    and triggered.get("type") == f"{self.component_id}-complete-task"
                ):
                    snapshot = self.store.complete_task(
                        str(triggered.get("task_id", ""))
                    )
                    feedback = {"tone": "success", "message": "Task completed."}
                else:
                    snapshot = self.store.load()
            except ValueError as exc:
                snapshot = self.store.load()
                feedback = {"tone": "error", "message": str(exc)}

            title, content = self._full_screen_parts(snapshot, feedback)
            return (
                render_tasks_summary(snapshot),
                title,
                content,
                feedback,
                next_person_name,
                next_task_title,
                next_task_person,
                next_due_on,
                next_recurrence,
            )

        @app.callback(
            Output("full-screen-modal-content", "children", allow_duplicate=True),
            Input(self.fullscreen_content_store_id(), "data"),
            State("full-screen-modal-title", "children"),
            prevent_initial_call=True,
        )
        def sync_open_modal(content, current_modal_title):
            if self._modal_is_showing_tasks(current_modal_title):
                return content
            return no_update

    def _full_screen_parts(self, snapshot, feedback=None):
        title = html.Div(
            "Tasks",
            className="text-m",
            **cast(Any, {"data-component-name": self.name}),
        )
        content = render_tasks_fullscreen(
            snapshot, self.component_id, feedback=feedback
        )
        return title, content

    def _modal_is_showing_tasks(self, current_modal_title) -> bool:
        if not isinstance(current_modal_title, dict):
            return False
        return (
            current_modal_title.get("props", {}).get("data-component-name") == self.name
        )
