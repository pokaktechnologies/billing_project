from channels.generic.websocket import AsyncJsonWebsocketConsumer

class AttendanceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.group_name = "attendance_notifications"

        # Join group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"message": "✅ Connected to attendance notifications"})

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Optional: echo back messages
        await self.send_json({"echo": content})

    # Receive message from scheduler
    async def send_notification(self, event):
        await self.send_json({
            "type": "notification",
            "message": event["message"]
        })
