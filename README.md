# ExacqMan

A Python-based tool for extracting video footage from ExacqVision servers using the ExacqVision Web API. It supports creating timelapse videos, compressing footage, and overlaying timestamps, with flexible configuration via command-line arguments and config files.

For API testing, [explore the Postman collection](https://weareipc.postman.co/workspace/Industrial-Pallet-Corp~f0dc5379-c365-405e-8a29-ee8050839c42/collection/38801065-56761369-c40d-4cb1-9ab1-3f0a7efb59c9?action=share&creator=38801065&active-environment=7096363-3d41cab2-1adc-47b2-8041-ef8c9b87eb00).

## Requirements

- Python 3.8+
- `requests`
- `tqdm`
- `moviepy`
- `opencv-python` (cv2)
- `python-dateutil`
- `tzdata`

## Setup

1. Clone this repository or download `exacqman.py`, `exacqvision.py`, and `default.config`.
2. Copy `default.config` and rename it (e.g., `mydefault.config`).
3. Edit the config file:
   - **[Auth]**: Set `user` and `password` for ExacqVision API access.
   - **[Network]**: List server names and their IP addresses.
   - **[Cameras]**: Map camera aliases to their IDs.
   - **[Settings]**: Configure `timezone`, `timelapse_multiplier` (positive integer), `compression_level` (`low`, `medium`, or `high`), `crop_dimensions` (leave blank for interactive cropping), and `font_weight` (positive integer for timestamp thickness).
   - **[Runtime]**: Optionally set defaults for `server`, `camera_alias`, `filename`, `date`, `start_time`, and `end_time`.
4. Save the config file.

## Usage

Run `python exacqman.py --help` for detailed command-line options. The script supports three modes:

### Commands

- **extract**: Retrieves video from an ExacqVision server, applies timelapse, adds timestamps, and compresses the output.
- **compress**: Compresses an existing video file to a specified quality.
- **timelapse**: Creates a timelapse video from an existing file, with optional cropping and timestamping.

### Command-Line Syntax

```bash
python exacqman.py [-h | --help] <command> [<args>]
```

#### Extract Mode

```bash
python exacqman.py extract [camera_alias] [date] [start] [end] [config_file] [--server SERVER] [-o OUTPUT_NAME] [--quality {low,medium,high}] [--multiplier MULTIPLIER] [-c]
```

- `camera_alias`: Camera name (e.g., "front_door").
- `date`: Date in MM/DD format (e.g., "3/11"). Use the start date if footage spans midnight.
- `start`: Start time (e.g., "6pm", "18:30").
- `end`: End time (e.g., "8pm", "20:00").
- `config_file`: Path to configuration file.
- `--server`: Server name (e.g., "ch" for Clark Hill).
- `-o, --output_name`: Output file path (default: based on input with suffixes).
- `--quality`: Compression quality (`low`, `medium`, `high`).
- `--multiplier`: Timelapse speed factor (positive integer).
- `-c, --crop`: Enable cropping (interactive if `crop_dimensions` not set).

#### Compress Mode

```bash
python exacqman.py compress video_filename quality [-o OUTPUT_NAME]
```

- `video_filename`: Input video file path.
- `quality`: Compression quality (`low`, `medium`, `high`).
- `-o, --output_name`: Output file path.

#### Timelapse Mode

```bash
python exacqman.py timelapse video_filename multiplier [-o OUTPUT_NAME] [-c]
```

- `video_filename`: Input video file path.
- `multiplier`: Timelapse speed factor (positive integer).
- `-o, --output_name`: Output file path.
- `-c, --crop`: Enable cropping.

### Example Commands

- Extract video from a camera for March 11, 6 PM to 8 PM, with config and cropping:
  ```bash
  python exacqman.py extract front_door 3/11 6pm 8pm mydefault.config --server ch --output_name output.mp4 --quality medium --multiplier 10 --crop
  ```
- Compress a video to medium quality:
  ```bash
  python exacqman.py compress input.mp4 medium --output_name compressed.mp4
  ```
- Create a 5x timelapse video:
  ```bash
  python exacqman.py timelapse input.mp4 5 --output_name timelapse.mp4 --crop
  ```

## Configuration File

The config file (`default.config` template) is structured as follows:

```ini
[Auth]
user = your_username
password = your_password

[Network]
ch = 192.168.1.100
ny = 192.168.2.100

[Cameras]
front_door = 1
back_door = 2

[Settings]
timezone = US/Eastern
timelapse_multiplier = 10
compression_level = medium
crop_dimensions = 
font_weight = 2

[Runtime]
server = ch
camera_alias = front_door
filename = output.mp4
date = 3/11
start_time = 6pm
end_time = 8pm
```

- Leave `crop_dimensions` blank to select interactively during runtime; the script will output coordinates to copy into the config.
- Ensure `timelapse_multiplier` and `font_weight` are positive integers.
- `compression_level` must be `low`, `medium`, or `high`.

## Testing

1. Verify the configuration file is properly set up.
2. Test with sample commands in each mode.
3. Date format: `MM/DD` or `MM/DD/YYYY`.
4. Time format: `HH:MM:SSAM|PM` (e.g., "6:00:00PM"), or simplified (e.g., "6pm").
5. Check output videos for correct timelapse speed, compression quality, cropping, and timestamp accuracy.

## Exacqvision API Interaction

The `exacqvision.py` module handles API communication:

- **Login**: Authenticates and retrieves a session ID.
- **Logout**: Ends the session.
- **List Cameras**: Retrieves available cameras.
- **Create Search**: Queries video clip timestamps.
- **Export Request**: Initiates video export.
- **Export Status**: Monitors export request progress.
- **Export Download**: Downloads the video.
- **Export Delete**: Cleans up export requests.
- **Get Video**: Combines export steps to retrieve a video.
- **Get Timestamps**: Extracts timestamps for video frames.

See docstrings in `exacqvision.py` for detailed usage.

## Notes

- The script adds timestamps to extracted videos using server-provided clip data.
- Cropping can be set in the config or selected interactively during runtime.
- Output files are always `.mp4`.
- Compression uses `libx264` codec with adjustable bitrate and resolution based on quality settings.
- Ensure network access to the ExacqVision server and valid credentials.