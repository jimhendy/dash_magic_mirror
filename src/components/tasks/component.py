from __future__ import annotations

import time

from dash import ALL, Dash, Input, Output, State, ctx, dcc, no_update
from dash.exceptions import PreventUpdate

from components.base import BaseComponent
from utils.dates import local_today
from utils.styles import COLORS

from .constants import TASKS_REFRESH_INTERVAL_MS
from .data import TaskRecurrence, TaskStore
from .full_screen import (
    people_options,
    render_feedback,
    render_task_list,
    render_tasks_panel,
)
from .summary import render_tasks_badge, render_tasks_summary


class Tasks(BaseComponent):
    """Household chores: people, one-off and recurring tasks.

    Not repository-backed: the data is local (a JSON file), so it's read
    straight from `TaskStore` on render and on every action.
    """

    title = "Tasks"
    icon = "mdi:checkbox-marked-circle-outline"
    accent = COLORS["violet"]

    def __init__(self, **kwargs):
        super().__init__(name="tasks", **kwargs)
        self.store = TaskStore()

    def _summary_layout(self):
        return render_tasks_summary(self.store.load())

    def _tile_badge(self):
        return render_tasks_badge(self.store.load())

    def _detail_layout(self):
        return render_tasks_panel(self.store.load(), self.component_id)

    def _panel_subtitle(self):
        return "Chores for everyone at home"

    def _hidden_layout(self):
        return [
            dcc.Interval(
                id=f"{self.component_id}-interval",
                interval=TASKS_REFRESH_INTERVAL_MS,
                n_intervals=0,
            ),
            # Which task (if any) has its "Remove" armed and is waiting on a
            # confirm tap - carried through background refreshes.
            dcc.Store(id=f"{self.component_id}-pending-delete", data=None),
        ]

    def _views(self, snapshot, pending_delete_id):
        return (
            render_tasks_summary(snapshot),
            render_tasks_badge(snapshot),
            render_task_list(snapshot, self.component_id, pending_delete_id),
            people_options(snapshot),
        )

    def _add_callbacks(self, app: Dash) -> None:
        cid = self.component_id
        view_outputs = [
            Output(f"{cid}-summary", "children", allow_duplicate=True),
            Output(f"{cid}-badge", "children", allow_duplicate=True),
            Output(f"{cid}-list", "children", allow_duplicate=True),
            Output(f"{cid}-task-person", "data", allow_duplicate=True),
        ]

        @app.callback(
            *view_outputs,
            Input(f"{cid}-interval", "n_intervals"),
            State(f"{cid}-pending-delete", "data"),
            prevent_initial_call=True,
        )
        def refresh_task_views(_interval, pending_delete_id):
            # Picks up edits made from another device / tab.
            return self._views(self.store.load(), pending_delete_id)

        @app.callback(
            *view_outputs,
            Output(f"{cid}-feedback", "children"),
            Output(f"{cid}-pending-delete", "data"),
            Output(f"{cid}-person-name", "value"),
            Output(f"{cid}-task-title", "value"),
            Output(f"{cid}-task-person", "value"),
            Output(f"{cid}-task-due-on", "value"),
            Output(f"{cid}-task-recurrence", "value"),
            Input(f"{cid}-add-person", "n_clicks"),
            Input(f"{cid}-add-task", "n_clicks"),
            Input({"type": f"{cid}-act", "action": ALL, "task_id": ALL}, "n_clicks"),
            State(f"{cid}-person-name", "value"),
            State(f"{cid}-task-title", "value"),
            State(f"{cid}-task-person", "value"),
            State(f"{cid}-task-due-on", "value"),
            State(f"{cid}-task-recurrence", "value"),
            State(f"{cid}-pending-delete", "data"),
            prevent_initial_call=True,
        )
        def handle_task_actions(
            _add_person_clicks,
            _add_task_clicks,
            _action_clicks,
            person_name,
            task_title,
            task_person,
            task_due_on,
            task_recurrence,
            pending_delete_id,
        ):
            # Every row's buttons are re-rendered after each action, and Dash
            # fires pattern-matching callbacks when matching components
            # (re)appear - with n_clicks still 0. Only a real click counts.
            triggered = ctx.triggered_id
            if triggered is None or not (
                ctx.triggered and ctx.triggered[0].get("value")
            ):
                raise PreventUpdate

            feedback = None
            pending = pending_delete_id
            next_person_name = no_update
            next_task_title = no_update
            next_task_person = no_update
            next_due_on = no_update
            next_recurrence = no_update

            try:
                if triggered == f"{cid}-add-person":
                    added_name = " ".join((person_name or "").split())
                    snapshot = self.store.add_person(added_name)
                    new_person = next(
                        (
                            p
                            for p in snapshot.people
                            if p.name.casefold() == added_name.casefold()
                        ),
                        None,
                    )
                    feedback = {"tone": "success", "message": f"Added {added_name}."}
                    next_person_name = ""
                    if new_person is not None:
                        next_task_person = new_person.id
                elif triggered == f"{cid}-add-task":
                    snapshot = self.store.add_task(
                        title=task_title or "",
                        person_id=task_person or "",
                        due_on=(task_due_on or "")[:10],
                        recurrence=task_recurrence or TaskRecurrence.ONCE.value,
                    )
                    feedback = {"tone": "success", "message": "Task added."}
                    next_task_title = ""
                    next_due_on = local_today().isoformat()
                    next_recurrence = TaskRecurrence.ONCE.value
                    pending = None
                else:
                    action = triggered.get("action")
                    task_id = str(triggered.get("task_id", ""))
                    if action == "complete":
                        snapshot = self.store.complete_task(task_id)
                        feedback = {"tone": "success", "message": "Nice – task done."}
                        pending = None
                    elif action == "arm":
                        snapshot = self.store.load()
                        pending = task_id
                    elif action == "confirm":
                        snapshot = self.store.delete_task(task_id)
                        feedback = {"tone": "success", "message": "Task removed."}
                        pending = None
                    else:  # cancel
                        snapshot = self.store.load()
                        pending = None
            except ValueError as exc:
                snapshot = self.store.load()
                feedback = {"tone": "error", "message": str(exc)}

            return (
                *self._views(snapshot, pending),
                render_feedback(feedback, key=str(time.time())),
                pending,
                next_person_name,
                next_task_title,
                next_task_person,
                next_due_on,
                next_recurrence,
            )
