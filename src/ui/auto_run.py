import subprocess
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Timer

WATCHED_FILE = "main_window.py"
DEBOUNCE_DELAY = 1.0  # seconds

class ScriptRunner(FileSystemEventHandler):
    def __init__(self):
        self.debounce_timer = None
        self.process = None  # Track running process

    def on_modified(self, event):
        if event.src_path.endswith(WATCHED_FILE):
            if self.debounce_timer:
                self.debounce_timer.cancel()
            self.debounce_timer = Timer(DEBOUNCE_DELAY, self.run_script)
            self.debounce_timer.start()

    def run_script(self):
        print(f"\n🔁 Detected change in {WATCHED_FILE}, restarting...\n")

        # Stop previous process if it's running
        if self.process and self.process.poll() is None:
            print("🛑 Stopping previous process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()

        # Start new process
        try:
            self.process = subprocess.Popen(["python", WATCHED_FILE])
        except Exception as e:
            print(f"❌ Failed to start script:\n{e}")


if __name__ == "__main__":
    path = os.path.abspath(".")
    event_handler = ScriptRunner()
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=False)
    observer.start()

    print(f"👀 Watching {WATCHED_FILE} for changes...\nPress Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 Stopped watching.")
        # Kill subprocess on exit
        if event_handler.process and event_handler.process.poll() is None:
            event_handler.process.terminate()
            event_handler.process.wait()
    observer.join()
