"""
Simple job queue for running background tasks in HyperBlend.
"""

import logging
import threading
import time
import queue
import traceback
from typing import Callable, Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Global job queue
_job_queue = queue.Queue()
_worker_thread = None
_worker_running = False
_job_history = []
_job_history_max_size = 100


def _worker_thread_function():
    """Worker thread function to process jobs from the queue."""
    global _worker_running

    logger.info("Background job worker thread started")

    while _worker_running:
        try:
            # Get a job from the queue with a timeout
            try:
                job = _job_queue.get(timeout=5)
            except queue.Empty:
                continue

            # Process the job
            job_id = job.get("id", "unknown")
            job_type = job.get("type", "unknown")
            job_args = job.get("args", {})
            job_function = job.get("function")

            logger.info(f"Processing background job: {job_id} ({job_type})")

            start_time = time.time()
            try:
                # Update job status to running
                job["status"] = "running"
                job["start_time"] = start_time

                # Execute the job function
                if callable(job_function):
                    result = job_function(**job_args)
                    job["result"] = result
                    job["status"] = "completed"
                else:
                    raise ValueError(f"Job function is not callable: {job_function}")
            except Exception as e:
                logger.error(f"Error processing job {job_id}: {str(e)}")
                logger.error(traceback.format_exc())
                job["status"] = "failed"
                job["error"] = str(e)
                job["traceback"] = traceback.format_exc()

            # Calculate duration
            end_time = time.time()
            job["end_time"] = end_time
            job["duration"] = end_time - start_time

            # Log job completion
            if job["status"] == "completed":
                logger.info(f"Job {job_id} completed in {job['duration']:.2f} seconds")
            else:
                logger.error(f"Job {job_id} failed after {job['duration']:.2f} seconds")

            # Add to job history and remove old entries if needed
            _job_history.append(job)
            while len(_job_history) > _job_history_max_size:
                _job_history.pop(0)

            # Mark job as done
            _job_queue.task_done()
        except Exception as e:
            logger.error(f"Error in worker thread: {str(e)}")
            logger.error(traceback.format_exc())
            time.sleep(10)  # Avoid tight loop in case of repeated errors

    logger.info("Background job worker thread stopped")


def start_worker():
    """Start the background worker thread."""
    global _worker_thread, _worker_running

    if _worker_thread and _worker_thread.is_alive():
        logger.info("Worker thread is already running")
        return

    _worker_running = True
    _worker_thread = threading.Thread(target=_worker_thread_function, daemon=True)
    _worker_thread.start()
    logger.info("Started background job worker thread")


def stop_worker():
    """Stop the background worker thread."""
    global _worker_running

    if not _worker_thread or not _worker_thread.is_alive():
        logger.info("No active worker thread to stop")
        return

    logger.info("Stopping background job worker thread...")
    _worker_running = False
    _worker_thread.join(timeout=10)
    logger.info("Background job worker thread stopped")


def queue_job(job_type: str, function: Callable, **kwargs) -> Dict[str, Any]:
    """
    Add a job to the queue.

    Args:
        job_type: Type of job (e.g., 'merge_molecules', 'enrich_molecule')
        function: Function to execute
        **kwargs: Arguments to pass to the function

    Returns:
        Dict containing job information
    """
    if not _worker_running:
        start_worker()

    job_id = f"{job_type}-{int(time.time())}-{hash(function) % 10000}"

    job = {
        "id": job_id,
        "type": job_type,
        "function": function,
        "args": kwargs,
        "status": "queued",
        "queue_time": time.time(),
    }

    _job_queue.put(job)
    logger.info(f"Queued job {job_id} of type {job_type}")

    # Return a copy of the job info without the function reference
    job_info = job.copy()
    job_info.pop("function")
    return job_info


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a job by ID.

    Args:
        job_id: Job ID to look up

    Returns:
        Dict containing job information or None if not found
    """
    for job in _job_history:
        if job.get("id") == job_id:
            job_info = job.copy()
            if "function" in job_info:
                job_info.pop("function")
            return job_info

    return None


def get_job_history() -> List[Dict[str, Any]]:
    """
    Get the history of jobs.

    Returns:
        List of job information dictionaries
    """
    job_history = []
    for job in _job_history:
        job_info = job.copy()
        if "function" in job_info:
            job_info.pop("function")
        job_history.append(job_info)

    return job_history
