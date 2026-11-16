from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from main.decorators import subscription_required
from main.models import FitnessAssessment
from main.views.api_v1_helpers import require_authenticated_json


def _latest_assessment(user):
    return FitnessAssessment.objects.filter(user=user).order_by("-assessment_completed_at").first()


def _plan_from_assessment(assessment: FitnessAssessment | None):
    if assessment is None:
        return None
    payload = assessment.payload or {}
    plan = payload.get("generatedPlan") or payload.get("_generatedPlan") or {}
    program = plan.get("program") or {}
    body_analysis = plan.get("bodyAnalysis") or {}
    title = (
        plan.get("title")
        or program.get("name")
        or assessment.next_recommended_program_id
        or ""
    )
    description = (
        plan.get("summary")
        or plan.get("description")
        or body_analysis.get("summary")
        or "План создан на основе последней анкеты."
    )
    if not title:
        return None
    return {
        "title": title,
        "description": description,
        "workoutId": assessment.next_recommended_program_id or program.get("id") or None,
        "assessmentCompletedAt": assessment.assessment_completed_at.isoformat(),
    }


@require_GET
def api_v1_plan_current(request):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    plan = _plan_from_assessment(_latest_assessment(request.user))
    if plan is None:
        return JsonResponse({"plan": None, "detail": "План появится после заполнения анкеты"})
    return JsonResponse({"plan": plan})


@require_POST
@subscription_required
def api_v1_plan_generate(request):
    assessment = _latest_assessment(request.user)
    if assessment is None:
        return JsonResponse({"plan": None, "detail": "Для генерации плана сначала заполните анкету"})

    try:
        from main.views.assessment_plan_stub import stub_generate_training_plan

        payload = {
            k: v
            for k, v in (assessment.payload or {}).items()
            if not str(k).startswith("_")
        }
        stub_generate_training_plan(assessment, payload)
        assessment.refresh_from_db()
    except Exception:
        # Если генератор недоступен, ниже всё равно попробуем вернуть уже сохранённый план.
        pass

    plan = _plan_from_assessment(assessment)
    if plan is None:
        return JsonResponse({"plan": None, "detail": "Для генерации плана сначала заполните анкету"})
    return JsonResponse({"plan": plan})
