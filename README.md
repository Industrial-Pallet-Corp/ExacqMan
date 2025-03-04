# ExacqMan
Python-based footage extractor utilizing the ExacqVision Web API to extract video footage from specified cameras and apply timelapse or compression techniques based on user input.

For api testing, check out the Postman collection : https://weareipc.postman.co/workspace/Industrial-Pallet-Corp~f0dc5379-c365-405e-8a29-ee8050839c42/collection/38801065-56761369-c40d-4cb1-9ab1-3f0a7efb59c9?action=share&creator=38801065&active-environment=7096363-3d41cab2-1adc-47b2-8041-ef8c9b87eb00

For generating timestamps, check out this site : https://dencode.com/date?v=&tz=Etc%2FGreenwich
  - use the ISO8601 Date (Extend)

This program uses timestamps that must end in 'Z'. Typically, this denotes Greenwich Mean Time (GMT), but the program will use the timezone specified in the configuration file to accurately convert timezones. This approach avoids the issue of Daylight Saving Time altering the time offset.

## Requirements

- Python 3.x
- `requests`
- `tqdm`
- `moviepy`
- `cv2` (OpenCV)
- `tzdata`

## Usage

1. Clone this repository, or download exacqman.py, exacvision.py, and default.config.
2. Copy default.config and rename the copy to your liking. Fill in user and password fields. 
3. Change variables in the [Settings] category as desired. (Note: 'timelapse_multiplier' must be a positive integer and 'compression_level' must be one of [low, medium, high])
4. Change variables in the [Runtime] category if desired.
5. Run `python script_name.py --help` for usage info.

### Usage:

```
  -h | --help            Display this help text
  -v | --version         Display script version
  extract                Extract, timelapse, and compress a video file
    -[door_number]       Door number of camera wanted (must be an integer)
    -start               Starting timestamp of video requested
    -end                 Ending timestamp of video requested
    -config_file         Filepath of local config file
    -o | --output_name   Desired filepath
    --quality            Desired video quality (choices: low, medium, high)
    --multiplier         Desired timelapse multiplier (must be a positive integer)
  compress               Compress a video file
    -video_filename      Video file to compress
    -compression_quality Desired compression quality (choices: low, medium, high)
    -o | --output_name   Desired filepath
  timelapse              Create a timelapse video
    -video_filename      Video file for timelapse
    -multiplier          Desired timelapse multiplier (must be a positive integer)
    -o | --output_name   Desired filepath
```

## Testing

1. Ensure the configuration file is properly set up.
2. Run the script in the desired mode (extract, compress, or timelapse) with appropriate arguments.
3. When entering the start and stop timestamps, they should be of the form 'YYYY-MM-DDTHH:MM:SSZ' (e.g. '2025-01-28T13:00:00Z').
4. Observe the generated video files for the applied timelapse or compression effects.

### Example commands:

- Extract mode: `python script_name.py extract <door_number> <start> <end> <config_file> --output_name <output_name> --quality <quality> --multiplier <multiplier>`
- Compress mode: `python script_name.py compress <video_filename> <compression_quality> --output_name <output_name>`
- Timelapse mode: `python script_name.py timelapse <video_filename> <multiplier> --output_name <output_name>`

## Exacqvision API Interaction

The `exacvision.py` script interacts with the Exacqvision API to perform the following actions:

- **Login:** Logs the user into the Exacqvision API and retrieves session ID and available camera IDs.
- **Logout:** Logs the user out using a valid session ID.
- **List Cameras:** Lists available cameras for the authenticated user.
- **Create Search:** Initiates a search request for video recordings from a specified camera.
- **Export Request:** Initiates an export request for video recordings.
- **Export Status:** Checks the status of an export request.
- **Export Download:** Downloads the exported video file.
- **Export Delete:** Deletes an export request after completion.
- **Get Video:** Combines the above Export actions to retrieve and download video recordings.

Example usage for `exacvision.py` functions can be found within the script's docstrings and inline comments.
