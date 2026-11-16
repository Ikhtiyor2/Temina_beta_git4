"""
GenerateTrainingPlan bridge for the native assessment API.
Uses Gemini when configured; falls back to a deterministic starter plan.
После сохранения плана — создаётся недельный план (WeeklyPlan).
"""
import logging

from django.utils import timezone

from main.services.gemini_ai import generate_assessment_plan
from main.services.weekly_plan_service import ensure_weekly_plan_after_assessment

logger = logging.getLogger(__name__)


def stub_generate_training_plan(assessment, payload: dict) -> None:
    try:
        plan = generate_assessment_plan(payload)
        generated_by = "gemini"
        plan_version = "gemini_assessment_v1"
    except Exception:
        plan = {
            "program": {
                "id": "stub_program_v1",
                "name": "Базовый план после анкеты",
                "sessions": [
                    {
                        "dayIndex": 1,
                        "blocks": [
                            {
                                "exerciseId": "PUSHUP",
                                "sets": 3,
                                "reps": 12,
                                "restSec": 60,
                                "notes": "Контроль техники",
                            }
                        ],
                    }
                ],
            },
            "bodyAnalysis": {
                "summary": "Оценка по анкете без фото.",
                "postureRisks": [],
                "focusAreas": ["общая выносливость"],
            },
        }
        generated_by = "fallback"
        plan_version = "stub_json_v1"

    assessment.next_recommended_program_id = plan["program"]["id"]
    assessment.generated_plan_version = plan_version
    assessment.payload = {
        **payload,
        "_generatedPlan": plan,
        "_generatedAt": timezone.now().isoformat(),
        "_generatedBy": generated_by,
    }
    assessment.save(update_fields=["next_recommended_program_id", "generated_plan_version", "payload"])

    try:
        ensure_weekly_plan_after_assessment(assessment)
    except Exception as e:
        logger.warning("weekly plan after assessment: %s", e)
