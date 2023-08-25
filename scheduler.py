import schedule
import time

ONE_MINUTE = 60


def run_schedule(update_rates):
    # Run it first time
    update_rates()
    schedule.every().hour.do(update_rates)

    while True:
        schedule.run_pending()
        time.sleep(ONE_MINUTE)
