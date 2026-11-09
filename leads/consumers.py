
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class LeadNotificationConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):

        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close()
            return

        self.group_name = f"lead_notifications_{user.id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        await self.send_json({
            "type": "connection",
            "message": "Connected to lead notifications"
        })

    async def disconnect(self, close_code):

        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def notification_message(self, event):

        await self.send_json({
            "type": "notification",
            "data": event["data"]
        })
