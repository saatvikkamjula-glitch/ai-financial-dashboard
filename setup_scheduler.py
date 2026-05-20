import subprocess
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
PLIST_FILE = PROJECT_DIR / "com.finance.dashboard.plist"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
LAUNCH_AGENT_FILE = LAUNCH_AGENTS_DIR / "com.finance.dashboard.plist"


def ask_hour():
    while True:
        try:
            hour = int(input("What hour should the dashboard run? Use 0-23 format: ").strip())

            if 0 <= hour <= 23:
                return hour

            print("Hour must be between 0 and 23.")
        except ValueError:
            print("Please enter a valid number.")


def ask_minute():
    while True:
        try:
            minute = int(input("What minute should it run? Use 0-59: ").strip())

            if 0 <= minute <= 59:
                return minute

            print("Minute must be between 0 and 59.")
        except ValueError:
            print("Please enter a valid number.")


def format_time(hour, minute):
    if hour == 0:
        return f"12:{minute:02d} AM"

    if hour < 12:
        return f"{hour}:{minute:02d} AM"

    if hour == 12:
        return f"12:{minute:02d} PM"

    return f"{hour - 12}:{minute:02d} PM"


def build_plist(hour, minute):
    scheduled_command = PROJECT_DIR / "run_dashboard_scheduled.command"
    output_log = PROJECT_DIR / "reports" / "scheduler_output.log"
    error_log = PROJECT_DIR / "reports" / "scheduler_error.log"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN"
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">

<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.finance.dashboard</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{scheduled_command}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{PROJECT_DIR}</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>{output_log}</string>

    <key>StandardErrorPath</key>
    <string>{error_log}</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
"""


def run_command(command):
    result = subprocess.run(command, shell=True, text=True, capture_output=True)

    if result.stdout.strip():
        print(result.stdout.strip())

    if result.stderr.strip():
        print(result.stderr.strip())

    return result.returncode


def install_scheduler(hour, minute):
    PROJECT_DIR.joinpath("reports").mkdir(exist_ok=True)
    LAUNCH_AGENTS_DIR.mkdir(exist_ok=True)

    plist_content = build_plist(hour, minute)

    PLIST_FILE.write_text(plist_content, encoding="utf-8")
    LAUNCH_AGENT_FILE.write_text(plist_content, encoding="utf-8")

    run_command(f"chmod +x '{PROJECT_DIR / 'run_dashboard.command'}'")
    run_command(f"chmod +x '{PROJECT_DIR / 'run_dashboard_scheduled.command'}'")

    run_command(f"launchctl bootout gui/$(id -u) '{LAUNCH_AGENT_FILE}' 2>/dev/null")
    run_command(f"launchctl bootstrap gui/$(id -u) '{LAUNCH_AGENT_FILE}'")
    run_command("launchctl enable gui/$(id -u)/com.finance.dashboard")

    print("\nScheduler updated successfully.")
    print(f"Dashboard will run every day at {format_time(hour, minute)}.")
    print("\nYou can still run it manually anytime with:")
    print("./run_dashboard.command")


def main():
    print("AI Financial Dashboard Scheduler Setup")
    print("--------------------------------------")
    print("Use 24-hour time.")
    print("Examples:")
    print("9:00 AM  = hour 9, minute 0")
    print("6:30 PM  = hour 18, minute 30")
    print("10:00 PM = hour 22, minute 0\n")

    hour = ask_hour()
    minute = ask_minute()

    install_scheduler(hour, minute)


if __name__ == "__main__":
    main()