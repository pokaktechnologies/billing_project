import jwt
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

class BlacklistCheckMiddleware(MiddlewareMixin):
    def process_request(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        # print(f"Auth Header: {auth_header}")

        token = auth_header.split(" ")[1]
        try:
            decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user = JWTAuthentication().get_user(validated_token=decoded)
            force_logout_time = getattr(user, "force_logout_time", None)
            if force_logout_time and decoded["iat"] < int(force_logout_time.timestamp()):
                return JsonResponse(
                    {"detail": "Session expired. Please log in again."},
                    status=401,
                )
        except InvalidToken:
            return JsonResponse({"detail": "Invalid token"}, status=401)
        except jwt.ExpiredSignatureError:
            return JsonResponse({"detail": "Token expired"}, status=401)
        except Exception:
            return None  # let DRF handle other errors

        return None
