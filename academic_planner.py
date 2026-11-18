"""Problem 9: To-Do List with Deadlines.

Run with Python 3.8 or later and Tkinter:
    python3 academic_planner.py

The planner creates academic_tasks.sqlite3 beside this script.
"""

import re
import sqlite3
import tkinter as tk
from contextlib import closing
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk


DATABASE_PATH = Path(__file__).resolve().with_name("academic_tasks.sqlite3")
PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def validate_task(title, due_date, priority):
    """Return normalized form values or raise a user-friendly error."""
    title = title.strip()
    due_date = due_date.strip()
    if not title:
        raise ValueError("Enter a task title.")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", due_date):
        raise ValueError("Enter the due date in YYYY-MM-DD format.")
    try:
        parsed_date = date.fromisoformat(due_date)
    except ValueError:
        raise ValueError("Enter a valid calendar date.") from None
    if priority not in PRIORITY_ORDER:
        raise ValueError("Select High, Medium or Low priority.")
    return title, parsed_date.isoformat(), priority


def sort_tasks(tasks, sort_by):
    """Return a sorted copy. The second key breaks ties."""
    if sort_by == "Priority":
        return sorted(tasks, key=lambda task: (
            PRIORITY_ORDER[task["priority"]], date.fromisoformat(task["due_date"])
        ))
    return sorted(tasks, key=lambda task: (
        date.fromisoformat(task["due_date"]), PRIORITY_ORDER[task["priority"]]
    ))


def task_status(task, today):
    if task["completed"]:
        return "Completed"
    due_date = date.fromisoformat(task["due_date"])
    if due_date < today:
        return "Overdue"
    if due_date == today:
        return "Due today"
    return "Upcoming"


class TaskStore:
    """Store tasks in SQLite and commit every successful change."""

    def __init__(self, path):
        self.path = path
        self.write("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                due_date TEXT NOT NULL,
                priority TEXT NOT NULL CHECK (priority IN ('High', 'Medium', 'Low')),
                completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1))
            )
        """)

    def write(self, statement, values=()):
        # The inner context commits on success and rolls back on error.
        with closing(sqlite3.connect(self.path)) as connection, connection:
            cursor = connection.execute(statement, values)
            return cursor.lastrowid

    def all_tasks(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                "SELECT id, title, due_date, priority, completed FROM tasks ORDER BY id"
            ).fetchall()

    def add(self, title, due_date, priority):
        return self.write(
            "INSERT INTO tasks (title, due_date, priority) VALUES (?, ?, ?)",
            (title, due_date, priority),
        )

    def edit(self, task_id, title, due_date, priority):
        self.write(
            "UPDATE tasks SET title = ?, due_date = ?, priority = ? WHERE id = ?",
            (title, due_date, priority, task_id),
        )

    def complete(self, task_id):
        self.write("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))

    def delete(self, task_id):
        self.write("DELETE FROM tasks WHERE id = ?", (task_id,))


class AcademicPlanner:
    def __init__(self, root, store):
        self.root = root
        self.store = store
        self.today = date.today()
        self.editing_id = None
        self.title = tk.StringVar(root)
        self.due_date = tk.StringVar(root, value=self.today.isoformat())
        self.priority = tk.StringVar(root, value="Medium")
        self.sort_by = tk.StringVar(root, value="Due date")
        self.summary = tk.StringVar(root)
        self.tasks = {}

        root.title("Academic Task Planner")
        root.geometry("820x530")
        root.minsize(710, 450)
        self.build_widgets()
        self.refresh()
        self.title_entry.focus_set()
        root.after(15_000, self.check_date)

    def build_widgets(self):
        style = ttk.Style(self.root)
        style.configure("Treeview", rowheight=28)
        style.configure("Title.TLabel", font=("TkDefaultFont", 20, "bold"))

        main = ttk.Frame(self.root, padding=20)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        ttk.Label(main, text="Academic Task Planner", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 14)
        )

        form = ttk.LabelFrame(main, text="Task details", padding=12)
        form.grid(row=1, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)
        for column, label in enumerate(("Title", "Due date (YYYY-MM-DD)", "Priority")):
            ttk.Label(form, text=label).grid(row=0, column=column, sticky="w")

        self.title_entry = ttk.Entry(form, textvariable=self.title)
        self.title_entry.grid(row=1, column=0, sticky="ew", padx=(0, 12))
        self.date_entry = ttk.Entry(form, textvariable=self.due_date, width=19)
        self.date_entry.grid(row=1, column=1, sticky="w", padx=(0, 12))
        priority_box = ttk.Combobox(
            form, textvariable=self.priority, values=tuple(PRIORITY_ORDER),
            state="readonly", width=9,
        )
        priority_box.grid(row=1, column=2, sticky="w", padx=(0, 12))
        self.save_button = ttk.Button(form, text="Add task", command=self.save_form)
        self.save_button.grid(row=1, column=3, padx=(0, 6))
        self.cancel_button = ttk.Button(
            form, text="Cancel edit", command=self.reset_form, state="disabled"
        )
        self.cancel_button.grid(row=1, column=4)
        for widget in (self.title_entry, self.date_entry, priority_box):
            widget.bind("<Return>", lambda event: self.save_form())

        toolbar = ttk.Frame(main)
        toolbar.grid(row=2, column=0, sticky="ew", pady=(16, 8))
        ttk.Label(toolbar, textvariable=self.summary).pack(side="left")
        sort_box = ttk.Combobox(
            toolbar, textvariable=self.sort_by, values=("Due date", "Priority"),
            state="readonly", width=10,
        )
        sort_box.pack(side="right")
        ttk.Label(toolbar, text="Sort by").pack(side="right", padx=(0, 8))
        sort_box.bind("<<ComboboxSelected>>", lambda event: self.refresh())

        table = ttk.Frame(main)
        table.grid(row=3, column=0, sticky="nsew")
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            table, columns=("title", "due", "priority", "status"),
            show="headings", selectmode="browse",
        )
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        for key, label, width in (
            ("title", "Task", 320), ("due", "Due date", 110),
            ("priority", "Priority", 90), ("status", "Status", 110),
        ):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, stretch=(key == "title"),
                             anchor="w" if key == "title" else "center")
        self.tree.tag_configure("Overdue", background="#FADBD8", foreground="#861C17")
        self.tree.tag_configure("Due today", background="#FFF2CC", foreground="#614900")
        self.tree.tag_configure("Completed", background="#E7F3EC", foreground="#22583C")
        self.tree.bind("<<TreeviewSelect>>", self.update_actions)

        actions = ttk.Frame(main)
        actions.grid(row=4, column=0, sticky="w", pady=(12, 0))
        self.complete_button = ttk.Button(actions, text="Mark complete", command=self.complete_task)
        self.edit_button = ttk.Button(actions, text="Edit task", command=self.edit_task)
        self.delete_button = ttk.Button(actions, text="Delete task", command=self.delete_task)
        for button in (self.complete_button, self.edit_button, self.delete_button):
            button.pack(side="left", padx=(0, 8))

    def refresh(self, selected_id=None):
        try:
            tasks = sort_tasks(self.store.all_tasks(), self.sort_by.get())
        except sqlite3.Error as error:
            messagebox.showerror("Could not load tasks", str(error), parent=self.root)
            return

        if selected_id is None and self.tree.selection():
            selected_id = int(self.tree.selection()[0])
        self.today = date.today()
        self.tasks = {task["id"]: task for task in tasks}
        self.tree.delete(*self.tree.get_children())
        overdue_count = 0
        for task in tasks:
            status = task_status(task, self.today)
            overdue_count += status == "Overdue"
            self.tree.insert(
                "", "end", iid=str(task["id"]),
                values=(task["title"], task["due_date"], task["priority"], status),
                tags=(status,),
            )
        if selected_id in self.tasks:
            self.tree.selection_set(str(selected_id))
            self.tree.see(str(selected_id))
        self.summary.set(f"Today: {self.today.isoformat()}   |   Overdue: {overdue_count}")
        self.update_actions()

    def check_date(self):
        # Refresh after midnight even if the app has been left open.
        if date.today() != self.today:
            self.refresh()
        self.root.after(15_000, self.check_date)

    def selected_task(self):
        selection = self.tree.selection()
        return self.tasks.get(int(selection[0])) if selection else None

    def update_actions(self, event=None):
        task = self.selected_task()
        state = "normal" if task is not None else "disabled"
        self.edit_button.configure(state=state)
        self.delete_button.configure(state=state)
        self.complete_button.configure(
            state="normal" if task is not None and not task["completed"] else "disabled"
        )

    def save_form(self):
        try:
            values = validate_task(self.title.get(), self.due_date.get(), self.priority.get())
        except ValueError as error:
            messagebox.showwarning("Check task details", str(error), parent=self.root)
            return

        try:
            task_id = self.editing_id
            if task_id is None:
                task_id = self.store.add(*values)
            else:
                self.store.edit(task_id, *values)
        except sqlite3.Error as error:
            messagebox.showerror("Could not save task", str(error), parent=self.root)
            return

        self.reset_form()
        self.refresh(selected_id=task_id)

    def edit_task(self):
        task = self.selected_task()
        if task is None:
            return
        self.editing_id = task["id"]
        self.title.set(task["title"])
        self.due_date.set(task["due_date"])
        self.priority.set(task["priority"])
        self.save_button.configure(text="Save changes")
        self.cancel_button.configure(state="normal")
        self.title_entry.focus_set()

    def reset_form(self):
        self.editing_id = None
        self.title.set("")
        self.due_date.set(date.today().isoformat())
        self.priority.set("Medium")
        self.save_button.configure(text="Add task")
        self.cancel_button.configure(state="disabled")
        self.title_entry.focus_set()

    def complete_task(self):
        task = self.selected_task()
        if task is None:
            return
        try:
            self.store.complete(task["id"])
        except sqlite3.Error as error:
            messagebox.showerror("Could not complete task", str(error), parent=self.root)
            return
        self.refresh()

    def delete_task(self):
        task = self.selected_task()
        if task is None or not messagebox.askyesno(
            "Delete task", f'Delete "{task["title"]}"?', parent=self.root
        ):
            return
        try:
            self.store.delete(task["id"])
        except sqlite3.Error as error:
            messagebox.showerror("Could not delete task", str(error), parent=self.root)
            return
        if self.editing_id == task["id"]:
            self.reset_form()
        self.refresh()


def main():
    root = tk.Tk()
    try:
        store = TaskStore(DATABASE_PATH)
    except sqlite3.Error as error:
        messagebox.showerror("Could not open task database", str(error), parent=root)
        root.destroy()
        return
    AcademicPlanner(root, store)
    root.mainloop()


if __name__ == "__main__":
    main()
