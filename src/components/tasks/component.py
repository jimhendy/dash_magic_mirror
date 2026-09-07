from __future__ import annotations

from typing import Any, cast

from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate

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
                # Which task (if any) has its "Remove" armed and is waiting
                # on a Confirm tap. Lives in the always-mounted base layout,
                # not the modal content, so a background refresh tick can
                # carry it through instead of silently disarming mid-tap.
                dcc.Store(id=f"{self.component_id}-pending-delete", data=None),
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
        # Kept separate from `handle_task_actions` below: its Inputs (the
        # add-person/add-task buttons and per-task complete buttons) only
        # exist in the DOM once the full-screen modal has been opened at
        # least once - they're rendered into a dcc.Store and copied into the
        # modal on click, not mounted in the base layout. A single callback
        # with prevent_initial_call=False depending on those ids crashes the
        # Dash renderer on page load (before the modal ever opens) because
        # it can't resolve their initial value. The periodic refresh here
        # only ever depends on the always-mounted Interval, so it's safe to
        # fire immediately and on every tick regardless of modal state.
        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Output(self.fullscreen_title_store_id(), "data"),
            Output(self.fullscreen_content_store_id(), "data"),
            Input(f"{self.component_id}-interval", "n_intervals"),
            State(f"{self.component_id}-feedback", "data"),
            State(f"{self.component_id}-pending-delete", "data"),
            prevent_initial_call=False,
        )
        def refresh_task_views(_interval, current_feedback, pending_delete_id):
            snapshot = self.store.load()
            title, content = self._full_screen_parts(
                snapshot,
                current_feedback,
                pending_delete_id,
            )
            return render_tasks_summary(snapshot), title, content

        @app.callback(
            Output(f"{self.component_id}-content", "children", allow_duplicate=True),
            Output(self.fullscreen_title_store_id(), "data", allow_duplicate=True),
            Output(self.fullscreen_content_store_id(), "data", allow_duplicate=True),
            Output(f"{self.component_id}-feedback", "data"),
            Output(f"{self.component_id}-pending-delete", "data"),
            Output(f"{self.component_id}-person-name", "value"),
            Output(f"{self.component_id}-task-title", "value"),
            Output(f"{self.component_id}-task-person", "value"),
            Output(f"{self.component_id}-task-due-on", "value"),
            Output(f"{self.component_id}-task-recurrence", "value"),
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
            prevent_initial_call=True,
        )
        def handle_task_actions(
            add_person_clicks,
            add_task_clicks,
            complete_clicks,
            person_name,
            task_title,
            task_person,
            task_due_on,
            task_recurrence,
        ):
            # The add-person/add-task/complete-task elements only exist
            # once the modal has actually mounted them, and Dash always
            # fires a callback once "for free" the first time each of its
            # Inputs newly appears in the DOM - regardless of
            # prevent_initial_call - using their construction-time default
            # n_clicks (0). Left unguarded, that phantom firing resolves
            # `ctx.triggered_id` to whichever Input is listed first
            # (add-person) and gets misread as a real click on an empty
            # form, throwing a bogus "Enter a name first." error the
            # moment the Tasks modal is opened. Only proceed when the
            # trigger's own n_clicks actually shows a real click (>0).
            #
            # The Remove/Confirm/Cancel controls are deliberately NOT
            # wired here: a pattern-matching Input that matches zero live
            # components on a render (which the confirm/cancel buttons do
            # whenever no row is armed, and all four would with an empty
            # task list) desynchronises this callback's argument list and
            # makes Dash raise an IndexError building the call. They get
            # their own callback (`handle_task_delete`) which simply never
            # fires while none of its inputs are on the page.
            triggered = ctx.triggered_id
            real_add_person = (
                triggered == f"{self.component_id}-add-person"
                and (add_person_clicks or 0) > 0
            )
            real_add_task = (
                triggered == f"{self.component_id}-add-task"
                and (add_task_clicks or 0) > 0
            )
            real_complete = (
                isinstance(triggered, dict)
                and triggered.get("type") == f"{self.component_id}-complete-task"
                and any(complete_clicks or [])
            )
            if not (real_add_person or real_add_task or real_complete):
                raise PreventUpdate

            feedback = None
            next_person_name = no_update
            next_task_title = no_update
            next_task_person = no_update
            next_due_on = no_update
            next_recurrence = no_update

            try:
                if triggered == f"{self.component_id}-add-person":
                    added_name = " ".join((person_name or "").split())
                    snapshot = self.store.add_person(added_name)
                    new_person = next(
                        (
                            person
                            for person in snapshot.people
                            if person.name.casefold() == added_name.casefold()
                        ),
                        None,
                    )
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
                else:
                    snapshot = self.store.complete_task(
                        str(triggered.get("task_id", "")),
                    )
                    feedback = {"tone": "success", "message": "Task completed."}
            except ValueError as exc:
                snapshot = self.store.load()
                feedback = {"tone": "error", "message": str(exc)}

            # Any add/complete also clears a half-finished "Remove"
            # confirmation on some other row.
            title, content = self._full_screen_parts(snapshot, feedback, None)
            return (
                render_tasks_summary(snapshot),
                title,
                content,
                feedback,
                None,
                next_person_name,
                next_task_title,
                next_task_person,
                next_due_on,
                next_recurrence,
            )

        @app.callback(
            Output(f"{self.component_id}-content", "children", allow_duplicate=True),
            Output(self.fullscreen_title_store_id(), "data", allow_duplicate=True),
            Output(self.fullscreen_content_store_id(), "data", allow_duplicate=True),
            Output(f"{self.component_id}-feedback", "data", allow_duplicate=True),
            Output(f"{self.component_id}-pending-delete", "data", allow_duplicate=True),
            Input(
                {"type": f"{self.component_id}-delete-task", "task_id": ALL},
                "n_clicks",
            ),
            Input(
                {"type": f"{self.component_id}-confirm-delete", "task_id": ALL},
                "n_clicks",
            ),
            Input(
                {"type": f"{self.component_id}-cancel-delete", "task_id": ALL},
                "n_clicks",
            ),
            prevent_initial_call=True,
        )
        def handle_task_delete(arm_clicks, confirm_clicks, cancel_clicks):
            triggered = ctx.triggered_id
            if not isinstance(triggered, dict):
                raise PreventUpdate
            kind = triggered.get("type")
            task_id = str(triggered.get("task_id", ""))

            arm = kind == f"{self.component_id}-delete-task" and any(arm_clicks or [])
            confirm = kind == f"{self.component_id}-confirm-delete" and any(
                confirm_clicks or [],
            )
            cancel = kind == f"{self.component_id}-cancel-delete" and any(
                cancel_clicks or [],
            )
            if not (arm or confirm or cancel):
                raise PreventUpdate

            feedback = None
            pending = None
            try:
                if arm:
                    snapshot = self.store.load()
                    pending = task_id or None
                elif confirm:
                    snapshot = self.store.delete_task(task_id)
                    feedback = {"tone": "success", "message": "Task removed."}
                else:
                    snapshot = self.store.load()
            except ValueError as exc:
                snapshot = self.store.load()
                feedback = {"tone": "error", "message": str(exc)}

            title, content = self._full_screen_parts(snapshot, feedback, pending)
            return (
                render_tasks_summary(snapshot),
                title,
                content,
                feedback,
                pending,
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

    def _full_screen_parts(self, snapshot, feedback=None, pending_delete_id=None):
        title = html.Div(
            "Tasks",
            className="text-m",
            **cast("Any", {"data-component-name": self.name}),
        )
        content = render_tasks_fullscreen(
            snapshot,
            self.component_id,
            feedback=feedback,
            pending_delete_id=pending_delete_id,
        )
        return title, content

    def _modal_is_showing_tasks(self, current_modal_title) -> bool:
        if not isinstance(current_modal_title, dict):
            return False
        return (
            current_modal_title.get("props", {}).get("data-component-name") == self.name
        )
