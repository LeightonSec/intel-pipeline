import schedule
import time
import logging
from pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def morning_run():
    logger.info("Scheduled AM run starting...")
    run_pipeline("AM")

def evening_run():
    logger.info("Scheduled PM run starting...")
    run_pipeline("PM")

# Schedule runs
schedule.every().day.at("07:00").do(morning_run)
schedule.every().day.at("19:00").do(evening_run)

if __name__ == "__main__":
    logger.info("Intel pipeline scheduler started.")
    logger.info("Scheduled: 07:00 AM and 19:00 PM daily.")
    
    # Run immediately on start for testing
    logger.info("Running initial pipeline now...")
    run_pipeline("AM")
    
    while True:
        schedule.run_pending()
        time.sleep(60)