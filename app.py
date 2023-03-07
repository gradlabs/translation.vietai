import os
import ast
import json
import faust
import asyncio
import aiohttp
import logging

KAFKA_HOST = os.getenv("BROKER", "kafka:9092")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 8))
TIMEOUT = float(os.getenv("TIMEOUT", 0.1))
INFER_URL = os.getenv(
    "INFER_URL", "http://localhost:8501/v1/models/transformer:predict"
)

logger = logging.getLogger(__name__)

app = faust.App("msd_trans", broker=f"kafka://{KAFKA_HOST}", value_serializer="raw")
shipper_in = app.topic("shipper_in")


def to_dict(event):
    return ast.literal_eval(event.value.decode())


def to_bytes(msg):
    return json.dumps(msg).encode()


async def ship(translations, events):
    tasks = []
    for translated, event in zip(translations, events):
        msg = to_dict(event)
        msg["data"] = translated[4:]
        task = asyncio.create_task(
            shipper_in.send(
                key=event.key,
                value=to_bytes(msg),
                headers=event.headers,
            )
        )
        tasks.append(task)
        logger.info(f"Processed {event} -> {translated}")
    await asyncio.gather(*tasks)


async def process_events(events, lang):
    # Prepare data
    payload = {"language": lang, "data": [to_dict(event)["data"] for event in events]}

    # Send request
    async with aiohttp.ClientSession() as session:
        async with session.post(INFER_URL, data=payload) as response:
            # Log status and content-type
            logger.info("Status: {}".format(response.status))
            logger.info("Content-type: {}".format(response.headers["content-type"]))
            # Get response asynchronously
            translations = await response.text()
            logger.info("Body: {}".format(translations))
    # Ship to next topic
    await ship(translations, events)


@app.agent("msd_vi2en")
async def vi2en_process(stream):
    async for events in stream.take_events(BATCH_SIZE, within=TIMEOUT):
        await process_events(events, "vi")


@app.agent("msd_en2vi")
async def en2vi_process(stream):
    async for events in stream.take_events(BATCH_SIZE, within=TIMEOUT):
        await process_events(events, "en")


app.main()
