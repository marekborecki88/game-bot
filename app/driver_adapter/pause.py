import sys
import time


def pause_and_display_progress_bar(pause_duration: int, message: str, refresh) -> None:
    """Pause execution for a specified duration while displaying a progress bar.

    Args:
        pause_duration: Total duration to pause in seconds.
        message: Message to display alongside the progress bar.
        interval: Interval in seconds to update the progress bar (default: 5).
    """


    print(message, pause_duration/60, " minutes")
    items = list(range(0, 100))
    l = len(items)
    interval = pause_duration / 100

    total_time = 0
    refresh_amount = 0

    print_progress(0, l, prefix='Progress:', length=30)
    for i, item in enumerate(items):
        time.sleep(interval)
        total_time += interval
        print_progress(i + 1, l, prefix='Progress:', length=30)
        if total_time >= (refresh_amount + 1) * 120:
            refresh()
            refresh_amount += 1

def print_progress(iteration, total, prefix='', length=30):
    percent = f"{100 * (iteration / float(total)):.1f}"
    filled_length = int(length * iteration // total)
    bar = '█' * filled_length + '-' * (length - filled_length)

    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% Complete')
    sys.stdout.flush()
