"""ChasmScheduler — schedule recurring research pipelines via APScheduler.

Uses a background thread scheduler so the main process stays responsive.
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from chasm.core.logger import get_logger
from chasm.graph.builder import ChasmGraph
from chasm.workflows.pipeline import run_weekly_research

logger = get_logger(__name__)


class ChasmScheduler:
    """Manages scheduled execution of the Chasm research pipeline."""

    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler()
        logger.info("ChasmScheduler initialised.")

    def start_weekly_pulse(self, graph: ChasmGraph) -> None:
        """Schedule the research pipeline to run every Monday at 08:00.

        Args:
            graph: The ChasmGraph to pass to each pipeline run.
        """
        self.scheduler.add_job(
            run_weekly_research,
            trigger="cron",
            day_of_week="mon",
            hour=8,
            args=[graph],
            id="weekly_research",
            name="Weekly Research Pipeline",
            replace_existing=True,
        )
        self.scheduler.start()

        next_run = self.scheduler.get_job("weekly_research").next_run_time
        logger.info("Weekly pulse scheduled — next run: %s", next_run)
        print(f"\n✓ Scheduler started — weekly pipeline runs every Monday at 08:00")
        print(f"  Next run: {next_run}")
        print(f"  Press Ctrl+C to stop.\n")

    def shutdown(self) -> None:
        """Gracefully shut down the scheduler."""
        self.scheduler.shutdown()
        logger.info("ChasmScheduler shut down.")
