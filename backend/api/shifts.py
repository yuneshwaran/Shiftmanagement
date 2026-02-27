from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session , joinedload
from sqlalchemy import or_

from datetime import date, datetime , timedelta
import pytz 
from models.database import get_db
from models.models import (
    ProjectLead,
    ProjectEmployee,
    ProjectHoliday,
    Employee,
    ShiftAllocation,
    ProjectShiftMaster,
)
from models.schemas import (
    ShiftBatchRequest,
    ProjectShiftCreateRequest,
)
from api.dependencies import get_current_lead, get_project_or_403 , get_holidays_map ,get_current_user

router = APIRouter(
    prefix="/shifts",
    tags=["Shifts"],
    dependencies=[Depends(get_current_user)],
)
ist = pytz.timezone('Asia/Kolkata') 

@router.get("/masters")
def get_project_shifts(
    project_id: int,
    on_date: date | None = None,
    db: Session = Depends(get_db),
):
    if not on_date:
        on_date = date.today()

    shifts = (
        db.query(ProjectShiftMaster)
        .filter(
            ProjectShiftMaster.project_id == project_id,
            ProjectShiftMaster.effective_from <= on_date,
            (ProjectShiftMaster.effective_to.is_(None))
            | (ProjectShiftMaster.effective_to >= on_date),
            ProjectShiftMaster.is_active == True,
        )
        .order_by(ProjectShiftMaster.shift_code)
        .all()
    )

    return shifts


@router.get("/projects/{project_id}/shifts/history")
def get_project_shift_history(
    project_id: int,
    db: Session = Depends(get_db),
    lead = Depends(get_current_lead),
):
    get_project_or_403(project_id, lead, db)

    shifts = (
        db.query(ProjectShiftMaster)
        .filter(ProjectShiftMaster.project_id == project_id)
        .order_by(
            ProjectShiftMaster.shift_code,
            ProjectShiftMaster.effective_from.desc(),
        )
        .all()
    )

    return [
        {
            "shift_code": s.shift_code,
            "shift_name": s.shift_name,
            "start_time": str(s.start_time),
            "end_time": str(s.end_time),
            "weekday_allowance": float(s.weekday_allowance),
            "weekend_allowance": float(s.weekend_allowance),
            "effective_from": s.effective_from,
            "effective_to": s.effective_to,
            "is_active": s.is_active,
        }
        for s in shifts
    ]


@router.get("/weekly")
def get_weekly_allocation(
    project_id: int,
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):

    # ───────── ACCESS CONTROL ─────────
    if isinstance(user, ProjectLead):
        get_project_or_403(project_id, user, db)

    elif isinstance(user, Employee):
        mapping = (
            db.query(ProjectEmployee)
            .filter(
                ProjectEmployee.project_id == project_id,
                ProjectEmployee.emp_id == user.emp_id,
            )
            .first()
        )
        if not mapping:
            raise HTTPException(403, "Not authorized")

    else:
        raise HTTPException(403, "Unauthorized user")
    
    print("USER TYPE:", type(user))
    
    allocations = (
        db.query(ShiftAllocation)
        .options(
            joinedload(ShiftAllocation.employee),
            joinedload(ShiftAllocation.approver),
        )
        .filter(
            ShiftAllocation.project_id == project_id,
            ShiftAllocation.shift_date.between(from_date, to_date),
        )
        .all()
    )
    for alloc in allocations:
            print(
                "DATE:", alloc.shift_date,
                "APPROVED:", alloc.is_approved,
                "APPROVED_BY:", alloc.approved_by
            )
    holidays = (
        db.query(ProjectHoliday)
        .filter(
            ProjectHoliday.holiday_date.between(from_date, to_date),
            or_(
                ProjectHoliday.project_id == project_id,
                ProjectHoliday.project_id.is_(None),
            ),
        )
        .all()
    )

    holiday_map = {}
    for h in holidays:
        d = h.holiday_date.isoformat()
        holiday_map[d] = {
            "is_holiday": True,
            "holiday_name": h.holiday_name,
            "scope": "project" if h.project_id else "company",
        }

    result = {}

    for alloc in allocations:

        d = alloc.shift_date.isoformat()

        result.setdefault(d, {
            "shifts": {},
            "is_approved": True,
            "approved_by": None,
            "last_updated": None,
            **holiday_map.get(d, {"is_holiday": False}),
        })

        if not alloc.is_approved:
            result[d]["is_approved"] = False

        if (
            result[d]["last_updated"] is None
            or alloc.last_updated > result[d]["last_updated"]
        ):
            result[d]["last_updated"] = alloc.last_updated

        # Approver from relationship
        if alloc.is_approved and alloc.approver:
            result[d]["approved_by"] = alloc.approver.lead_name

        result[d]["shifts"].setdefault(
            alloc.shift_code, []
        ).append({
            "allocation_id": alloc.allocation_id,
            "emp_id": alloc.emp_id,
            "emp_name": alloc.employee.emp_name,
            "emp_lname": alloc.employee.emp_lname,
            "project_id": alloc.project_id,
            "is_approved": alloc.is_approved,
        })

    # Ensure holiday-only dates appear
    for d, h in holiday_map.items():
        result.setdefault(d, {
            "shifts": {},
            "is_approved": False,
            "approved_by": None,
            "last_updated": None,
            **h,
        })

    return result

@router.get("/employees/available")
def get_available_employees(
    project_id: int,
    shift_code: str,
    shift_date: date,
    db: Session = Depends(get_db),
    lead=Depends(get_current_lead),
):
    get_project_or_403(project_id, lead, db)

    assigned = (
        db.query(ShiftAllocation.emp_id)
        .filter(
            ShiftAllocation.project_id == project_id,
            ShiftAllocation.shift_code == shift_code,
            ShiftAllocation.shift_date == shift_date,
        )
        .subquery()
    )

    employees = (
        db.query(Employee)
        .join(ProjectEmployee)
        .filter(
            ProjectEmployee.project_id == project_id,
            ~Employee.emp_id.in_(assigned),
        )
        .all()
    )

    return [{"emp_id": e.emp_id, "emp_name": e.emp_name} for e in employees]

@router.post("/apply-batch")
def apply_shift_batch(
    payload: ShiftBatchRequest,
    db: Session = Depends(get_db),
    lead=Depends(get_current_lead),
):
    get_project_or_403(payload.project_id, lead, db)

    if payload.remove:
        db.query(ShiftAllocation).filter(
            ShiftAllocation.allocation_id.in_(payload.remove),
            ShiftAllocation.project_id == payload.project_id,
        ).delete(synchronize_session=False)


    for a in payload.add:
        exists = (
            db.query(ShiftAllocation)
            .filter(
                ShiftAllocation.project_id == payload.project_id,
                ShiftAllocation.emp_id == a.emp_id,
                ShiftAllocation.shift_code == a.shift_code,
                ShiftAllocation.shift_date == a.shift_date,
            )
            .first()
        )

        if exists:
            continue  

        db.add(
            ShiftAllocation(
                project_id=payload.project_id,
                emp_id=a.emp_id,
                shift_code=a.shift_code,
                shift_date=a.shift_date,
                is_approved=False,
            )
        )

    for a in payload.approvals:
        db.query(ShiftAllocation).filter(
            ShiftAllocation.project_id == payload.project_id,
            ShiftAllocation.shift_date == a.date,
        ).update(
            {
                ShiftAllocation.is_approved: a.is_approved,
                ShiftAllocation.last_updated: datetime.now(ist),
                ShiftAllocation.approved_by: lead.lead_id if a.is_approved else None,
            },
            synchronize_session=False,
        )

    db.commit()
    return {"status": "ok"}

@router.post("/projects/{project_id}/shifts")
def create_project_shift(
    project_id: int,
    data: ProjectShiftCreateRequest,
    db: Session = Depends(get_db),
    lead=Depends(get_current_lead),
):
    get_project_or_403(project_id, lead, db)

    # Check duplicate effective_from for same shift_code
    exists = db.query(ProjectShiftMaster).filter(
        ProjectShiftMaster.project_id == project_id,
        ProjectShiftMaster.shift_code == data.shift_code,
        ProjectShiftMaster.effective_from == data.effective_from,
    ).first()

    if exists:
        raise HTTPException(
            400,
            "Shift already exists for this effective date"
        )

    new_shift = ProjectShiftMaster(
        project_id=project_id,
        shift_code=data.shift_code,
        shift_name=data.shift_name,
        start_time=data.start_time,
        end_time=data.end_time,
        weekday_allowance=data.weekday_allowance,
        weekend_allowance=data.weekend_allowance,
        effective_from=data.effective_from,
        is_active=True,
    )

    db.add(new_shift)
    db.commit()

    return {"status": "created"}


@router.get("/projects/{project_id}/shifts")
def get_project_shifts(
    project_id: int,
    on_date: date,
    db: Session = Depends(get_db),
    lead=Depends(get_current_lead),
):
    get_project_or_403(project_id, lead, db)

    return (
        db.query(ProjectShiftMaster)
        .filter(
            ProjectShiftMaster.project_id == project_id,
            ProjectShiftMaster.effective_from <= on_date,
            (
                ProjectShiftMaster.effective_to.is_(None)
                | (ProjectShiftMaster.effective_to >= on_date)
            ),
            ProjectShiftMaster.is_active == True,
        )
        .order_by(ProjectShiftMaster.shift_code)
        .all()
    )


@router.put("/projects/{project_id}/shifts/{shift_code}")
def update_project_shift(
    project_id: int,
    shift_code: str,
    data: ProjectShiftCreateRequest,
    db: Session = Depends(get_db),
    lead = Depends(get_current_lead),
):
    get_project_or_403(project_id, lead, db)

    current = db.query(ProjectShiftMaster).filter(
        ProjectShiftMaster.project_id == project_id,
        ProjectShiftMaster.shift_code == shift_code,
        ProjectShiftMaster.effective_to.is_(None),
        ProjectShiftMaster.is_active == True,
    ).first()

    if not current:
        raise HTTPException(404, "Active shift not found")

    if data.effective_from <= current.effective_from:
        raise HTTPException(
            400,
            "effective_from must be after current effective_from"
        )

    current.effective_to = data.effective_from - timedelta(days=1)

    new_shift = ProjectShiftMaster(
        project_id=project_id,
        shift_code=shift_code,
        shift_name=data.shift_name,
        start_time=data.start_time,
        end_time=data.end_time,
        weekday_allowance=data.weekday_allowance,
        weekend_allowance=data.weekend_allowance,
        effective_from=data.effective_from,
        is_active=True,
    )

    db.add(new_shift)
    db.commit()

    return {"status": "versioned"}


