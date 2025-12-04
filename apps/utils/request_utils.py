def extract_request_meta(request):
    return {
        "ip": request.META.get("HTTP_X_FORWARDED_FOR")
                or request.META.get("REMOTE_ADDR"),
        "device": request.META.get("HTTP_USER_AGENT", "Unknown")
    }
