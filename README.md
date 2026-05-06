# OpsFlow

OpsFlow is a lightweight workflow approval engine built with Django.

It allows teams to define approval workflows, start workflow runs, assign decisions to specific actors, and track each step from start to completion.

This project was built to demonstrate backend workflow orchestration, approval state transitions, access control, and auditability in a clean Django application.

---

## Why this exists

Many internal business processes rely on approval chains:

- purchase approvals
- finance sign-off
- compliance review
- operational escalations

OpsFlow models that process in a reusable way.

It provides:

- reusable workflow definitions
- ordered approval steps
- actor-based task assignment
- decision capture
- full audit history
- admin tooling for workflow operations

---

## Tech Stack

- Python 3.12
- Django 5
- SQLite
- Django Admin
- Django Test Framework

---

## Features

- Create reusable workflow definitions
- Configure ordered workflow steps
- Start workflow runs from a reference
- Assign active steps to specific users
- Approve, reject, send back, or escalate
- Track workflow state in real time
- Record full decision history
- Secure decision submission by assigned actor only
- Admin bulk approval/rejection actions
- Full audit visibility in Django Admin

---

## Running locally

```bash
git clone <repo-url>
cd opsflow

python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

---

## Demo Data

To seed clean demo workflow data for local development:

```bash
python manage.py seed_demo_workflows