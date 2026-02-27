from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date

from models.database import get_db
from models.models import (
    Project,
    ProjectHoliday,
    ProjectEmployee,
    ProjectLeadAssignment,
    ShiftAllocation,
    ProjectShiftMaster,
    Employee,
)
from api.dependencies import(
    get_current_lead,
    get_project_or_403,
    get_holidays_map,
    )



router = APIRouter(
    prefix="/allowances",
    tags=["Allowances"],
    dependencies=[Depends(get_current_lead)],
)



@router.get("/reports/employee-allowance")
def employee_allowance_report(
    project_id: int,
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db),
    lead=Depends(get_current_lead),
):
    get_project_or_403(project_id, lead, db)

    # Fetch active shifts
    shifts = (
        db.query(ProjectShiftMaster)
        .filter(
            ProjectShiftMaster.project_id == project_id,
            ProjectShiftMaster.effective_from <= to_date,
            (ProjectShiftMaster.effective_to.is_(None)) |
            (ProjectShiftMaster.effective_to >= from_date),
            ProjectShiftMaster.is_active == True,
        )
        .all()
    )

    shift_map = {s.shift_code: s for s in shifts}

    # Fetch approved allocations
    allocations = (
        db.query(
            ShiftAllocation.emp_id,
            Employee.emp_name,
            Employee.emp_lname,
            ShiftAllocation.shift_code,
            ShiftAllocation.shift_date,
        )
        .join(Employee)
        .filter(
            ShiftAllocation.project_id == project_id,
            ShiftAllocation.shift_date.between(from_date, to_date),
            ShiftAllocation.is_approved == True,
        )
        .all()
    )

    holidays = get_holidays_map(db, project_id, from_date, to_date)

    report = {}

    for emp_id, emp_name, emp_lname, shift_code, shift_date in allocations:

        shift = shift_map.get(shift_code)
        if not shift:
            continue

        emp = report.setdefault(emp_id, {
            "emp_id": emp_id,
            "emp_name": emp_name,
            "emp_lname": emp_lname,
            "shift_counts": {},
            "weekend_shift_count": 0,
            "holiday_shift_count": 0,
            "total_allowance": 0,
        })

        is_weekend = shift_date.weekday() >= 5
        is_holiday = shift_date.isoformat() in holidays

        if is_weekend or is_holiday:
            allowance = float(shift.weekend_allowance)

            if is_weekend:
                emp["weekend_shift_count"] += 1
            elif is_holiday:
                emp["holiday_shift_count"] += 1
        else:
            allowance = float(shift.weekday_allowance)
            emp["shift_counts"][shift_code] = (
                emp["shift_counts"].get(shift_code, 0) + 1
            )

        emp["total_allowance"] += allowance

    return {
        "shifts": [
            {
                "shift_code": s.shift_code,
                "shift_name": s.shift_name,
                "start_time": str(s.start_time),
                "end_time": str(s.end_time),
                "weekday_allowance": float(s.weekday_allowance),
                "weekend_allowance": float(s.weekend_allowance),
            }
            for s in shifts
        ],
        "rows": list(report.values()),
    }

@router.get("/reports/employee-allowance/aggregate")
def employee_allowance_report_aggregate(
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db),
    lead=Depends(get_current_lead),
):
    
    if lead.is_admin:
        project_ids = [
            p.project_id for p in db.query(Project).filter(Project.is_active == True)
        ]
    else:
        project_ids = [
            pid for (pid,) in db.query(ProjectLeadAssignment.project_id)
            .filter(ProjectLeadAssignment.lead_id == lead.lead_id)
            .all()
        ]
    if not project_ids:
        return {"shifts": [], "rows": []}

    # 🔹 Fetch all active shift masters for these projects
    shifts = (
        db.query(ProjectShiftMaster)
        .filter(
            ProjectShiftMaster.project_id.in_(project_ids),
            ProjectShiftMaster.effective_from <= to_date,
            (ProjectShiftMaster.effective_to.is_(None)) |
            (ProjectShiftMaster.effective_to >= from_date),
            ProjectShiftMaster.is_active == True,
        )
        .all()
    )

    # 🔹 Build shift_map with MAX allowance per shift_code
    shift_map = {}

    for s in shifts:
        existing = shift_map.get(s.shift_code)
        if not existing:
            shift_map[s.shift_code] = s
        else:
            # Take higher allowances
            if s.weekday_allowance > existing.weekday_allowance:
                existing.weekday_allowance = s.weekday_allowance
            if s.weekend_allowance > existing.weekend_allowance:
                existing.weekend_allowance = s.weekend_allowance

    # 🔹 Fetch all approved allocations across projects
    allocations = (
        db.query(
            ShiftAllocation.emp_id,
            Employee.emp_name,
            Employee.emp_lname,
            ShiftAllocation.shift_code,
            ShiftAllocation.shift_date,
        )
        .join(Employee)
        .filter(
            ShiftAllocation.project_id.in_(project_ids),
            ShiftAllocation.shift_date.between(from_date, to_date),
            ShiftAllocation.is_approved == True,
        )
        .all()
    )

    # 🔹 Fetch holidays across projects
    holidays = get_holidays_map(db, None, from_date, to_date)

    report = {}
    seen_shifts = set()   # 🔥 Deduplication set

    for emp_id, emp_name, emp_lname, shift_code, shift_date in allocations:

        unique_key = (emp_id, shift_date, shift_code)
        if unique_key in seen_shifts:
            continue
        seen_shifts.add(unique_key)

        shift = shift_map.get(shift_code)
        if not shift:
            continue

        emp = report.setdefault(emp_id, {
            "emp_id": emp_id,
            "emp_name": emp_name,
            "emp_lname": emp_lname,
            "shift_counts": {},
            "weekend_shift_count": 0,
            "holiday_shift_count": 0,
            "total_allowance": 0,
        })

        is_weekend = shift_date.weekday() >= 5
        is_holiday = shift_date.isoformat() in holidays

        if is_weekend or is_holiday:
            allowance = float(shift.weekend_allowance)

            if is_weekend:
                emp["weekend_shift_count"] += 1
            else:
                emp["holiday_shift_count"] += 1
        else:
            allowance = float(shift.weekday_allowance)
            emp["shift_counts"][shift_code] = (
                emp["shift_counts"].get(shift_code, 0) + 1
            )

        emp["total_allowance"] += allowance

    return {
        "shifts": [
            {
                "shift_code": s.shift_code,
                "shift_name": s.shift_name,
                "start_time": str(s.start_time),
                "end_time": str(s.end_time),
                "weekday_allowance": float(s.weekday_allowance),
                "weekend_allowance": float(s.weekend_allowance),
            }
            for s in shift_map.values()
        ],
        "rows": list(report.values()),
    }


@router.get("/reports/employee-allowance/detailed")
def employee_allowance_detailed(
    from_date: date,
    to_date: date,
    project_id: int | None = None,
    emp_id: int | None = None,
    db: Session = Depends(get_db),
    lead=Depends(get_current_lead),
):

    # 🔹 Get accessible projects
    if lead.is_admin:
        project_ids = [
            p.project_id for p in db.query(Project).all()
        ]
    else:
        project_ids = [
            pid for (pid,) in db.query(ProjectLeadAssignment.project_id)
            .filter(ProjectLeadAssignment.lead_id == lead.lead_id)
            .all()
        ]

    if project_id:
        if project_id not in project_ids:
            return {"summary": {}, "daily": []}
        project_ids = [project_id]

    if not project_ids:
        return {"summary": {}, "daily": []}

    # 🔹 Fetch shift masters
    shifts = (
        db.query(ProjectShiftMaster)
        .filter(
            ProjectShiftMaster.project_id.in_(project_ids),
            ProjectShiftMaster.effective_from <= to_date,
            (ProjectShiftMaster.effective_to.is_(None)) |
            (ProjectShiftMaster.effective_to >= from_date),
            ProjectShiftMaster.is_active == True,
        )
        .all()
    )

    # Build shift map with max allowance
    shift_map = {}
    for s in shifts:
        existing = shift_map.get(s.shift_code)
        if not existing:
            shift_map[s.shift_code] = s
        else:
            if s.weekday_allowance > existing.weekday_allowance:
                existing.weekday_allowance = s.weekday_allowance
            if s.weekend_allowance > existing.weekend_allowance:
                existing.weekend_allowance = s.weekend_allowance

    # 🔹 Fetch allocations
    query = (
        db.query(
            ShiftAllocation.emp_id,
            Employee.emp_name,            
            Employee.emp_lname,
            ShiftAllocation.shift_code,
            ShiftAllocation.shift_date,
            ShiftAllocation.project_id,
        )
        .join(Employee)
        .filter(
            ShiftAllocation.project_id.in_(project_ids),
            ShiftAllocation.shift_date.between(from_date, to_date),
            ShiftAllocation.is_approved == True,
        )
    )

    if emp_id:
        query = query.filter(ShiftAllocation.emp_id == emp_id)

    allocations = query.all()

    holidays = {
        h.holiday_date.isoformat(): h
        for h in db.query(ProjectHoliday)
        .filter(
            ProjectHoliday.project_id.in_(project_ids),
            ProjectHoliday.holiday_date.between(from_date, to_date),
        )
        .all()
    }

    seen = set()
    summary = {
        "weekday_count": 0,
        "weekend_count": 0,
        "holiday_count": 0,
        "total_allowance": 0,
    }

    daily = []

    for emp_id_val, emp_name, emp_lname, shift_code, shift_date, proj_id in allocations:

        unique_key = (emp_id_val, shift_date, shift_code)
        if unique_key in seen:
            continue
        seen.add(unique_key)

        shift = shift_map.get(shift_code)
        if not shift:
            continue

        is_weekend = shift_date.weekday() >= 5
        is_holiday = shift_date.isoformat() in holidays

        if is_weekend or is_holiday:
            allowance = float(shift.weekend_allowance)
            if is_weekend:
                summary["weekend_count"] += 1
                shift_type = "Weekend"
            else:
                summary["holiday_count"] += 1
                shift_type = "Holiday"
        else:
            allowance = float(shift.weekday_allowance)
            summary["weekday_count"] += 1
            shift_type = "Weekday"

        summary["total_allowance"] += allowance

        project_name = (
            db.query(Project.name)
            .filter(Project.project_id == proj_id)
            .scalar()
        )

        daily.append({
            "date": shift_date,
            "project": project_name,
            "shift_code": shift_code,
            "type": shift_type,
            "allowance": allowance,
            "employee": emp_name
        })

    return {
        "employee": {
            "emp_id": emp_id,
            "emp_name": emp_name,
            "emp_lname": emp_lname,
        } if emp_id else None,
        "summary": summary,
        "daily": sorted(daily, key=lambda x: x["date"]),
    }


@router.get("/reports/employees")
def get_employees_for_report(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    lead=Depends(get_current_lead),
):
    query = (
        db.query(
            Employee.emp_id,
            Employee.emp_name,
            Employee.emp_lname,
            Project.project_id,
            Project.name.label("project_name"),
        )
        .join(ProjectEmployee, ProjectEmployee.emp_id == Employee.emp_id)
        .join(Project, Project.project_id == ProjectEmployee.project_id)
    )

    if project_id:
        query = query.filter(Project.project_id == project_id)

    results = query.all()

    full_name = f"{emp_name} {emp_lname }".strip()
    employees = {}

    for emp_id, emp_name, emp_lname, proj_id, proj_name in results:
        emp = employees.setdefault(emp_id, {
            "emp_id": emp_id,
            "emp_name": full_name,
            "projects": []
        })

        emp["projects"].append({
            "project_id": proj_id,
            "project_name": proj_name
        })

    return list(employees.values())