# <service_app>/middleware.py
import jwt
from django.conf import settings
from django.http import JsonResponse


class UserContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_paths = set(
            getattr(
                settings,
                "JWT_AUTH_EXEMPT_PATHS",
                ("/health", "/api/v1/health"),
            )
        )

    def __call__(self, request):
        if request.path in self.exempt_paths:
            return self.get_response(request)

        auth_header = request.headers.get("Authorization", "")
        scheme, separator, token = auth_header.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            return JsonResponse({"error": "Unauthorized"}, status=401)

        signing_secret = getattr(settings, "JWT_SIGNING_SECRET", settings.SECRET_KEY)
        algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")

        try:
            claims = jwt.decode(
                token.strip(),
                signing_secret,
                algorithms=[algorithm],
                options={"require": ["exp", "iat", "sub", "uid", "role"]},
            )
        except jwt.PyJWTError as exc:
            print("JWT DECODE ERROR:", type(exc).__name__, exc)
            return JsonResponse({"error": "Unauthorized"}, status=401)

        if not all(
            isinstance(claims.get(key), str) and claims[key]
            for key in ("sub", "uid", "role")
        ):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        request.user_id = claims["uid"]
        request.user_code = claims["sub"]
        request.user_role = claims["role"]
        request.user_email = claims.get("email")
        request.auth_claims = claims

        return self.get_response(request)
