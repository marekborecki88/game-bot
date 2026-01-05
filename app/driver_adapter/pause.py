import time
from tqdm import tqdm

def pause_and_display_progress_bar(pause_duration: int, message: str, interval: int = 5) -> None:
    """Pause execution for a specified duration while displaying a progress bar.

    Args:
        pause_duration: Total duration to pause in seconds.
        message: Message to display alongside the progress bar.
        interval: Interval in seconds to update the progress bar (default: 5).
    """


    print(message)
    with tqdm(total=int(pause_duration), unit="s") as pbar:
        elapsed = 0
        while elapsed < pause_duration:
            time.sleep(min(interval, pause_duration - elapsed))
            elapsed += min(interval, pause_duration - elapsed)
            pbar.update(min(interval, pause_duration - elapsed))
