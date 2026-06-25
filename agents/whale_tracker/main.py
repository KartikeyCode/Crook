import asyncio
import logging
from dotenv import load_dotenv
from croo import EventType, DeliverOrderRequest, DeliverableType, ListOptions
from shared.croo_client import make_client
from shared.schemas import WhaleTrackerRequest
from agents.whale_tracker.fetcher import fetch_whale_data

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("whale-tracker")


async def deliver(client, order_id: str, requirements: str):
    try:
        req = WhaleTrackerRequest.model_validate_json(requirements)
        result = await fetch_whale_data(req)
        await client.deliver_order(order_id, DeliverOrderRequest(
            deliverable_type=DeliverableType.TEXT,
            deliverable_text=result.model_dump_json(),
        ))
        log.info(f"Delivered order {order_id}")
    except Exception as e:
        log.error(f"Failed order {order_id}: {e}")
        await client.reject_order(order_id, str(e))


async def main():
    client = make_client()
    stream = await client.connect_websocket()

    orphaned = await client.list_orders(ListOptions(role="provider", status="paid"))
    for order in (orphaned.orders or []):
        log.info(f"Recovering orphaned order {order.id}")
        asyncio.create_task(deliver(client, order.id, order.requirements))

    stream.on(EventType.NEGOTIATION_CREATED,
              lambda e: asyncio.create_task(client.accept_negotiation(e.negotiation_id)))
    stream.on(EventType.ORDER_PAID,
              lambda e: asyncio.create_task(deliver(client, e.order_id, e.requirements)))

    log.info("Whale Tracker agent listening...")
    await stream.listen()


if __name__ == "__main__":
    asyncio.run(main())
