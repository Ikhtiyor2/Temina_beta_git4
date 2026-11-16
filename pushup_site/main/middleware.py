"""Optional middleware stubs — TimeTracking model removed; keep passthrough only."""


class TimeTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
