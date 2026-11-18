# Academic Task Planner

**Problem 9 · To-Do List with Deadlines**

A Python desktop app for tracking assignments, exams, and other academic deadlines. Add tasks with a title, due date, and priority. Sort the task list, edit or delete entries, and mark tasks as complete. Overdue incomplete tasks appear in red.

## Requirements and setup

You need Python 3.8 or later with Tkinter and SQLite support. The app uses Python's standard library, so there are no pip packages to install.

1. Download this repository using **Code → Download ZIP** and extract it, or clone the repository with Git.
2. Open a terminal in the extracted folder and run:

   ```bash
   python3 academic_planner.py
   ```

   On Windows, you can also run `py academic_planner.py`.

To check whether Tkinter is available, run `python3 -m tkinter` (or `py -m tkinter` on Windows). A small test window should open.

## How to use it

1. Enter a title, a due date in `YYYY-MM-DD` format, and a priority of **High**, **Medium**, or **Low**. Click **Add task**.
2. Use **Sort by** to choose **Due date** or **Priority**.
3. Select a row to **Mark complete**, **Edit task**, or **Delete task**. When editing, click **Save changes** to apply the update.

The app creates `academic_tasks.sqlite3` beside the Python file on first launch. Open the app from the same folder to see saved tasks. The folder must be writable.

## Architecture and group responsibilities

| Member | Area | What to explain |
| --- | --- | --- |
| 1 | Tkinter and input validation | `AcademicPlanner` connects buttons to methods. `validate_task()` rejects blank titles, invalid dates, and unsupported priorities. |
| 2 | Deadline comparison and status | `task_status()` parses the due date with `date.fromisoformat()`. An incomplete task is overdue when its due date is before today. A deadline equal to today appears as **Due today**. |
| 3 | Sorting and table refresh | `sort_tasks()` uses `sorted()` with a lambda key. Due-date sorting puts earlier dates first and breaks ties by priority. Priority sorting orders High, Medium, Low and breaks ties by due date. |
| 4 | SQLite and persistence | `TaskStore` stores tasks in a SQLite table. Each row has a unique ID. Successful writes commit to disk, and the app reads saved rows when reopened. |

When a user adds a task, the Tkinter form passes the input to `validate_task()`. After validation, `TaskStore` saves the task. The app reloads the rows, applies the selected sort order, and computes their statuses before updating the table.

## Demo

1. Add three tasks due yesterday, today, and tomorrow. Give them different priorities.
2. Show both sort modes. Confirm yesterday's incomplete task is red and today's task says **Due today**.
3. Mark the overdue task complete. Edit one of the remaining tasks and delete the other.
4. Close and reopen the app. Confirm the completion, edit, and deletion persisted.

## Repository files

| File | Purpose |
| --- | --- |
| `academic_planner.py` | Tkinter app, task logic, and SQLite storage |
| `README.md` | Setup, usage, architecture, and demo instructions |
| `.gitignore` | Excludes generated databases and local Python cache files |
