import base64
import json
import re
from typing import Any

from google import genai
from google.genai import types

from main.services.gemini_config import get_gemini_config


def _strip_code_fences(text: str) -> str:
    out = (text or "").strip()
    if out.startswith("```"):
        out = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", out)
        out = re.sub(r"\s*```$", "", out)
    return out.strip()


def _extract_json(text: str) -> Any:
    clean = _strip_code_fences(text)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start = clean.find(opener)
        end = clean.rfind(closer)
        if start != -1 and end != -1 and end > start:
            chunk = clean[start : end + 1]
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                continue
    raise ValueError("Gemini response is not valid JSON")


def _gemini_generate_json(
    prompt: str,
    *,
    image_b64: str | None = None,
    image_mime: str = "image/jpeg",
    temperature: float = 0.3,
) -> Any:
    cfg = get_gemini_config()
    model = cfg["model"]
    api_key = cfg["api_key"]

    parts: list[types.Part] = [types.Part.from_text(text=prompt)]
    if image_b64:
        try:
            raw = base64.b64decode(image_b64, validate=True)
        except Exception as e:
            raise ValueError("Invalid base64 image data") from e
        parts.append(types.Part.from_bytes(data=raw, mime_type=image_mime))

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model,
            contents=parts,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
    except Exception as e:
        msg = str(e)
        if len(msg) > 400:
            msg = msg[:400] + "…"
        raise RuntimeError(f"Gemini request failed: {msg}") from e

    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned empty text")
    return _extract_json(text)


def extract_image_from_payload(payload: dict[str, Any]) -> tuple[str | None, str]:
    keys = (
        "bodyScanImageBase64",
        "bodyScanPhotoBase64",
        "bodyPhotoBase64",
        "photoBase64",
        "imageBase64",
    )
    for key in keys:
        raw = payload.get(key)
        if not raw or not isinstance(raw, str):
            continue
        if "," in raw and raw.lower().startswith("data:image/"):
            meta, encoded = raw.split(",", 1)
            mime = "image/jpeg"
            m = re.search(r"data:(image/[a-zA-Z0-9.+-]+);base64", meta, flags=re.I)
            if m:
                mime = m.group(1).lower()
            return encoded.strip(), mime
        return raw.strip(), "image/jpeg"
    return None, "image/jpeg"


def generate_assessment_plan(payload: dict[str, Any]) -> dict[str, Any]:
    image_b64, mime = extract_image_from_payload(payload)
    prompt = f"""
You are a sports coach and body-form assistant for Temina.
Using user's assessment data and optional body photo, return ONLY JSON object with this schema:
{{
  "program": {{
    "id": "short_slug",
    "name": "short title in Russian",
    "sessions": [
      {{
        "dayIndex": 1,
        "blocks": [
          {{
            "exerciseId": "PUSHUP|SQUAT|CRUNCH|PLANK",
            "sets": 2-4 integer,
            "reps": integer (for PLANK use seconds),
            "restSec": integer,
            "notes": "short Russian coaching note"
          }}
        ]
      }}
    ]
  }},
  "bodyAnalysis": {{
    "summary": "short Russian text",
    "postureRisks": ["..."],
    "focusAreas": ["..."]
  }}
}}
If no image is provided, infer bodyAnalysis from questionnaire only and mention uncertainty in summary.
Use only allowed exerciseId values.

Assessment JSON:
{json.dumps(payload, ensure_ascii=False)}
""".strip()
    data = _gemini_generate_json(prompt, image_b64=image_b64, image_mime=mime, temperature=0.2)
    if not isinstance(data, dict) or "program" not in data:
        raise ValueError("Gemini assessment plan response is invalid")
    return data
import base64
import json
import re
from typing import Any

from google import genai
from google.genai import types

from main.services.gemini_config import get_gemini_config


def _strip_code_fences(text: str) -> str:
    out = (text or "").strip()
    if out.startswith("```"):
        out = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", out)
        out = re.sub(r"\s*```$", "", out)
    return out.strip()


def _extract_json(text: str) -> Any:
    clean = _strip_code_fences(text)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Fallback: try to parse first JSON object/array slice.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = clean.find(opener)
        end = clean.rfind(closer)
        if start != -1 and end != -1 and end > start:
            chunk = clean[start : end + 1]
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                continue
    raise ValueError("Gemini response is not valid JSON")


def _gemini_generate_json(
    prompt: str,
    *,
    image_b64: str | None = None,
    image_mime: str = "image/jpeg",
    temperature: float = 0.3,
) -> Any:
    cfg = get_gemini_config()
    model = cfg["model"]
    api_key = cfg["api_key"]

    parts: list[types.Part] = [types.Part.from_text(text=prompt)]
    if image_b64:
        try:
            raw = base64.b64decode(image_b64, validate=True)
        except Exception as e:
            raise ValueError("Invalid base64 image data") from e
        parts.append(types.Part.from_bytes(data=raw, mime_type=image_mime))

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model,
            contents=parts,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
    except Exception as e:
        msg = str(e)
        if len(msg) > 400:
            msg = msg[:400] + "…"
        raise RuntimeError(f"Gemini request failed: {msg}") from e

    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned empty text")
    return _extract_json(text)


def extract_image_from_payload(payload: dict[str, Any]) -> tuple[str | None, str]:
    # Flexible keys to support different frontend payload shapes.
    keys = (
        "bodyScanImageBase64",
        "bodyScanPhotoBase64",
        "bodyPhotoBase64",
        "photoBase64",
        "imageBase64",
    )
    for key in keys:
        raw = payload.get(key)
        if not raw or not isinstance(raw, str):
            continue
        if "," in raw and raw.lower().startswith("data:image/"):
            meta, encoded = raw.split(",", 1)
            mime = "image/jpeg"
            m = re.search(r"data:(image/[a-zA-Z0-9.+-]+);base64", meta, flags=re.I)
            if m:
                mime = m.group(1).lower()
            return encoded.strip(), mime
        return raw.strip(), "image/jpeg"
    return None, "image/jpeg"


def generate_workout_plan_from_profile_context(context_text: str) -> list[dict[str, Any]]:
    prompt = f"""
You are a fitness coach for Temina.
Create ONLY JSON array (no markdown) with 3-4 items.
Allowed exercise ids only: pushups, squats, crunches, planks.
Each item schema:
{{
  "id": "pushups|squats|crunches|planks",
  "sets": integer from 2 to 4,
  "reps": "e.g. 10-15 or 30-60 sec"
}}
Respect health limitations and fitness level.

User profile:
{context_text}
""".strip()
    data = _gemini_generate_json(prompt, temperature=0.25)
    if not isinstance(data, list):
        raise ValueError("Gemini workout plan must be a JSON array")
    return data


def generate_assessment_plan(payload: dict[str, Any]) -> dict[str, Any]:
    image_b64, mime = extract_image_from_payload(payload)
    prompt = f"""
You are a sports coach and body-form assistant for Temina.
Using user's assessment data and optional body photo, return ONLY JSON object with this schema:
{{
  "program": {{
    "id": "short_slug",
    "name": "short title in Russian",
    "sessions": [
      {{
        "dayIndex": 1,
        "blocks": [
          {{
            "exerciseId": "PUSHUP|SQUAT|CRUNCH|PLANK",
            "sets": 2-4 integer,
            "reps": integer (for PLANK use seconds),
            "restSec": integer,
            "notes": "short Russian coaching note"
          }}
        ]
      }}
    ]
  }},
  "bodyAnalysis": {{
    "summary": "short Russian text",
    "postureRisks": ["..."],
    "focusAreas": ["..."]
  }}
}}
If no image is provided, infer bodyAnalysis from questionnaire only and mention uncertainty in summary.
Use only allowed exerciseId values.

Assessment JSON:
{json.dumps(payload, ensure_ascii=False)}
""".strip()
    data = _gemini_generate_json(prompt, image_b64=image_b64, image_mime=mime, temperature=0.2)
    if not isinstance(data, dict) or "program" not in data:
        raise ValueError("Gemini assessment plan response is invalid")
    return data
