import logging
from datetime import timedelta
from django.conf import settings
from livekit import api

logger = logging.getLogger(__name__)


class LiveKitService:
    @staticmethod
    def get_credentials():
        url = getattr(settings, 'LIVEKIT_URL', '')
        api_key = getattr(settings, 'LIVEKIT_API_KEY', '')
        api_secret = getattr(settings, 'LIVEKIT_API_SECRET', '')
        return url, api_key, api_secret

    @classmethod
    def generate_token(
        cls,
        room_name: str,
        identity: str,
        name: str = "",
        is_host: bool = False,
        ttl_minutes: int = 360,
        metadata: str = ""
    ) -> str:
        """
        Generates a LiveKit JWT token for either a host/faculty or a student/viewer.
        """
        url, api_key, api_secret = cls.get_credentials()
        if not api_key or not api_secret:
            raise ValueError("LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be configured in settings.")

        # Configure VideoGrants
        grants = api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,                  # Both Faculty and Students can publish camera, mic, screen share
            can_subscribe=True,                # Everyone can view/listen
            can_publish_data=True,             # Everyone can chat/send reactions
            room_admin=is_host,                # Only Faculty/Admin has admin permissions (mute, kick, end room)
            room_record=is_host,               # Only Faculty/Admin can trigger server recording
        )

        token = (
            api.AccessToken(api_key, api_secret)
            .with_identity(identity)
            .with_name(name)
            .with_grants(grants)
            .with_ttl(timedelta(minutes=ttl_minutes))
        )

        if metadata:
            token = token.with_metadata(metadata)

        return token.to_jwt()

    @classmethod
    def get_room_service(cls):
        url, api_key, api_secret = cls.get_credentials()
        if not url or not api_key or not api_secret:
            raise ValueError("LiveKit credentials not configured.")
        return api.LiveKitAPI(url, api_key=api_key, api_secret=api_secret)
