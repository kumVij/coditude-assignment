from concurrent.futures import ThreadPoolExecutor

from celery import Celery

from app.config import get_settings

settings = get_settings()
celery_app = Celery("hiring_assistant", broker=settings.redis_url, backend=settings.redis_url)
_local_executor = ThreadPoolExecutor(max_workers=4)


def enqueue_screening(batch_id: str) -> None:
    if settings.queue_backend.lower() == "celery":
        celery_app.send_task("app.services.screening_worker.process_screening_batch", args=[batch_id])
    else:
        from app.services.screening_worker import process_screening_batch

        _local_executor.submit(process_screening_batch, batch_id)
