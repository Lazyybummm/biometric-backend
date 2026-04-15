import paho.mqtt.client as mqtt
import json
import asyncio
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.domain import Command, CommandStatus
from sqlalchemy import update
import logging

logger = logging.getLogger(__name__)

class MQTTManager:
    def __init__(self):
        self.client = mqtt.Client(client_id="gridsphere_backend")
        if settings.MQTT_USER:
            self.client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASS)
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
        self.client.loop_start()  # Runs the network loop in a background thread

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected to MQTT Broker. Result code {rc}")
        client.subscribe("gridsphere/+/+/acks")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            command_id = payload.get("cmd_id")
            status = payload.get("status")
            
            if command_id and status:
                # Safe cross-thread execution by creating a new event loop purely for the DB transaction
                asyncio.run(self.update_command_status(command_id, status))
        except Exception as e:
            logger.error(f"MQTT Parsing Error: {e}")

    async def update_command_status(self, command_id: int, status: str):
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Command)
                .where(Command.id == command_id)
                .values(status=CommandStatus.SUCCESS if status == "success" else CommandStatus.FAILED)
            )
            await db.commit()

    def publish_command(self, tenant_id: int, device_id: str, command_id: int, command: str, target_id: int):
        topic = f"gridsphere/{tenant_id}/{device_id}/commands"
        payload = json.dumps({"cmd_id": command_id, "command": command, "target_id": target_id})
        # QoS 1 guarantees delivery to the broker and retry mechanisms
        self.client.publish(topic, payload, qos=1)

mqtt_manager = MQTTManager()