![](https://github.com/tatoline/kingdom-two-crowns-backuper/blob/main/logo.png?raw=true)

# Kingdom: Two Crowns Backuper

**Version:** v0.1

An open-source, unofficial backup utility for the game *Kingdom: Two Crowns*. This program automatically backs up your game saves at a configurable interval, allowing you to restore previous save files and manage your backup storage without any manual intervention.

> **Note:** This tool is not affiliated with Raw Fury, the publisher of *Kingdom: Two Crowns*.

[Download .exe file](https://github.com/tatoline/kingdom-two-crowns-backuper/releases/download/v0.1/kingdom-two-crowns-backuper.exe)

## Features

- **Automatic Backups:**  
  Periodically copies your game save file from the game's save directory to a backup folder.

- **Customizable Settings:**  
  - **Backup Interval:** Set the interval in seconds or minutes.
  - **Maximum Backup Size:** Define the maximum allowed size (in MB) for backups. When exceeded, the oldest backups are automatically deleted.
  - **Start-on-Launch Option:** Choose to start the backup process automatically when the program opens.

- **Organized Backup Structure:**  
  Backups are stored in daily folders (named by date) with sequential numbering and timestamps for easy restoration.

- **Restore & Delete Options:**  
  Easily restore a selected backup or delete individual backup files (or an entire day’s backups) using the intuitive graphical interface.

![](https://github.com/tatoline/kingdom-two-crowns-backuper/blob/main/view.jpg?raw=true)


## Installation & Usage

### Prerequisites

- **Python 3.6+**  
- **Tkinter:** Usually included with Python.  

### Running the Program

Clone the repository and run the program:

```bash
git clone https://github.com/tatoline/kingdom-two-crowns-backuper.git
cd kingdom-two-crowns-backuper
python kingdom-two-crowns-backuper.py
