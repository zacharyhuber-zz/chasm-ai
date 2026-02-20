"""
Chasm - AI-Powered Product Feedback Knowledge Graph

Entry point for the Chasm application.
Ingests unstructured product feedback, maps it into a Knowledge Graph
using NetworkX, and uses Vector Embeddings for semantic linking.
"""

import argparse
import time

from chasm.core.config import settings
from chasm.core.logger import get_logger
from chasm.graph.builder import ChasmGraph

logger = get_logger(__name__)


def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate workflow."""
    parser = argparse.ArgumentParser(
        description="Chasm — AI-Powered Hardware Feedback Knowledge Graph",
    )
    parser.add_argument(
        "--onboard",
        metavar="URL",
        type=str,
        help="Onboard a new company by scraping its website for products.",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Start the weekly research pipeline scheduler (runs every Monday at 08:00).",
    )

    args = parser.parse_args()
    graph = ChasmGraph()

    if args.onboard:
        from chasm.workflows.onboarding import onboard_new_company

        onboard_new_company(args.onboard, graph)

    elif args.schedule:
        from chasm.core.scheduler import ChasmScheduler

        scheduler = ChasmScheduler()
        scheduler.start_weekly_pulse(graph)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[!] Shutting down scheduler …")
            scheduler.shutdown()
            print("    Scheduler stopped. Goodbye.\n")

    else:
        logger.info("Chasm System Initialized.")
        print("Chasm System Initialized.")
        print("\nUsage:")
        print("  python main.py --onboard <COMPANY_URL>")
        print("  python main.py --schedule")
        print("\nExamples:")
        print("  python main.py --onboard https://www.dji.com")
        print("  python main.py --schedule")


if __name__ == "__main__":
    main()
