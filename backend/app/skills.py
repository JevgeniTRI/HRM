from fastapi import APIRouter, Response

from app.dependencies import DB
from app.schemas import AssessmentRead, AssessmentWrite, SkillRead, SkillSummary, SkillWrite
from app.services import skills

router = APIRouter(tags=["Навыки"])


@router.get("/skills", response_model=list[SkillSummary])
def list_skills(session: DB):
    return skills.list_skills(session)


@router.post("/skills", response_model=SkillRead, status_code=201)
def create_skill(data: SkillWrite, session: DB):
    return skills.create_skill(data, session)


@router.put("/skills/{skill_id}", response_model=SkillRead)
def update_skill(skill_id: int, data: SkillWrite, session: DB):
    return skills.update_skill(skill_id, data, session)


@router.delete("/skills/{skill_id}", status_code=204)
def delete_skill(skill_id: int, session: DB):
    skills.delete_skill(skill_id, session)
    return Response(status_code=204)


@router.put("/employees/{employee_id}/skills/{skill_id}", response_model=AssessmentRead)
def assess_skill(employee_id: int, skill_id: int, data: AssessmentWrite, session: DB):
    return skills.assess_skill(employee_id, skill_id, data, session)


@router.delete("/employees/{employee_id}/skills/{skill_id}", status_code=204)
def remove_assessment(employee_id: int, skill_id: int, session: DB):
    skills.remove_assessment(employee_id, skill_id, session)
    return Response(status_code=204)
