from django.http import JsonResponse, HttpResponseGone
from django.contrib.auth.decorators import login_required

# ======================================================
# LEGACY VIDEO VIEWS — DISABLED
# ======================================================
#
# ВАЖНО:
# Серверная камера (cv2.VideoCapture) НЕ ИСПОЛЬЗУЕТСЯ
# Видео всегда приходит из браузера
#
# Этот файл оставлен ТОЛЬКО для:
# - обратной совместимости
# - чтобы старые URL не ломались
# ======================================================


@login_required
def video_feed_disabled(request, *args, **kwargs):
    """
    Legacy endpoint.
    Серверная камера отключена навсегда.
    """
    return HttpResponseGone(
        "Server-side camera is disabled. "
        "Use browser camera + /api/ai/process instead."
    )


# Алиасы старых view (чтобы urls.py не падал)

video_feed_pushups = video_feed_disabled
video_feed_squats = video_feed_disabled
video_feed_pullups = video_feed_disabled
video_feed_crunches = video_feed_disabled
video_feed_planks = video_feed_disabled
video_feed = video_feed_disabled
video_feed1 = video_feed_disabled
video_feed2 = video_feed_disabled
video_feed3 = video_feed_disabled
