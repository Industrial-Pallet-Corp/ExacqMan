from configparser import ConfigParser
from moviepy import VideoFileClip
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as duparse
from zoneinfo import ZoneInfo
from exacqvision import Exacqvision
from tqdm import tqdm
from ast import literal_eval
import cv2
import argparse
import sys


def import_config(config_file: str) -> ConfigParser:
    config = ConfigParser()
    config.read(config_file)

    if validate_config(config) == False:
        exit(1)

    return config


def validate_config(config: ConfigParser) -> bool:
    ''' Checks config file for errors and returns a bool indicating if it finds anything missing from the config file that would cause a crash.'''

    errors = []
    fatal = False

    # Check Sections first

    sections = ['Auth', 'Network', 'Cameras', 'Settings']

    for section in sections:
        if not config.has_section(section):
            errors.append(f'[{section}] section is missing from config')
            fatal = True
    
    if errors:
        print(f"{'\n'.join(errors)}")
    
    if fatal:
        return False # False because config is not valid

    # Validate entries individually
    if 'user' not in config['Auth'] or not config['Auth']['user'].strip():
        errors.append('user is missing or empty')
        fatal = True
    
    if 'password' not in config['Auth'] or not config['Auth']['password'].strip():
        errors.append('password is missing or empty')
        fatal = True

    if 'server_ip' not in config['Network'] or not config['Network']['server_ip'].strip():
        errors.append('server_ip is missing or empty')
        fatal = True

    if 'timezone' not in config['Settings'] or not config['Settings']['timezone'].strip():
        errors.append('timezone is missing or empty')
        fatal = True

    if 'timelapse_multiplier' not in config['Settings'] or not config['Settings']['timelapse_multiplier'].strip():
        errors.append('timelapse_multiplier is missing or empty. Program will default to 10') # Default is set by the timelapse_video function
    else:
        try:
            int(config['Settings']['timelapse_multiplier'])
        except ValueError:
            errors.append('timelapse_multiplier must be an integer')
            fatal = True

    if 'compression_level' not in config['Settings'] or not config['Settings']['compression_level'].strip():
        errors.append('compression_level is missing or empty. Program will default to medium') # Default is set by the compress_video function

    crop_dimensions = config['Settings'].get('crop_dimensions', '').strip()
    if crop_dimensions:
        
        try:
            crop_dimensions = literal_eval(crop_dimensions)
            # Check if all values are integers
            if not all(isinstance(coord, int) for point in crop_dimensions for coord in point):
                errors.append('crop_dimensions should contain integers only')
        except ValueError:
            errors.append('crop_dimensions should follow the format: ((x, y), (width, height))')
                


        
    for camera_number, camera_value in config['Cameras'].items():
            if not camera_value.strip():
                errors.append(f'Camera {camera_number} has no id')
                fatal = True
            else:
                try:
                    int(camera_value)
                except ValueError:
                    errors.append(f'Camera ID {camera_number} must be an integer')
                    fatal = True


    if errors:
        print(f"{'\n'.join(errors)}")
    
    if fatal:
        return False
    else:
        return True


def process_video(original_video_path: str, output_video_path: str = None, multiplier: int = 10, timestamps: list[datetime] = None, crop: bool = False, crop_dimensions = None) -> str:
    """
    Creates a timelapse video from the original video file by applying the specified multiplier.

    If timestamps are provided, they are added to the video.

    Args:
        original_video_path (str):                  The filepath of the original video.
        output_video_path (str, optional):          The filepath for the output video. 
        multiplier (int, optional):                 The timelapse multiplier (must be a positive integer). Default is 10.
        timestamps (list of datetime, optional):    A list of timestamps to be added to the video. 
                                                    If provided, each frame's timestamp will be added to the video.

    Returns:
        str: The filepath of the processed video.

    Raises:
        SystemExit: If the original video file cannot be opened.
    """

    def fit_to_screen(frame, window_name):
        """Resize a frame to fit within the screen dimensions."""
        screen_width, screen_height = cv2.getWindowImageRect(window_name)[2:]
        original_height, original_width = frame.shape[:2]

        # Determine scaling factor to fit frame within screen dimensions
        scale_width = screen_width / original_width
        scale_height = screen_height / original_height
        scale = min(scale_width, scale_height)  # Use the smaller scale factor

        resized_width = int(original_width * scale)
        resized_height = int(original_height * scale)
        resized_frame = cv2.resize(frame, (resized_width, resized_height))

        return resized_frame, scale


    def select_crop(frame) -> tuple[tuple[int,int], tuple[int,int]]:
        # Create a window to get screen dimensions
        window_name = "Select ROI"
        
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 960, 540)  # Temporary window size

        # Resize frame to fit screen dimensions
        resized_frame, scale = fit_to_screen(frame, window_name)

        instructions = "Drag to select ROI, then press Enter."

        # Replace 'first_frame' with frame with instructions
        frame_with_text = resized_frame.copy()
        text_size = cv2.getTextSize(instructions, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        text_x = (frame_with_text.shape[1] - text_size[0]) // 2
        text_y = 30  # Position at the top of the frame
        cv2.putText(frame_with_text, instructions, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        # Show the resized frame and allow ROI selection
        roi = cv2.selectROI(window_name, frame_with_text, showCrosshair=True, fromCenter=False)
        cv2.destroyAllWindows()  # Close the ROI selection window

        # Scale ROI coordinates back to original resolution
        x, y, w, h = map(int, roi)
        x = int(x / scale)
        y = int(y / scale)
        w = int(w / scale)
        h = int(h / scale)

        coords = ((x,y),(w,h))
        print(f'Crop coord: {coords}')
        return coords


    def calculate_font_scale(video_width: int, font_thickness: int) -> float:
        # Static timestamp to calculate scale
        timestamp_string = datetime(2025, 3, 28, 6, 43, 20).strftime('%Y-%m-%d %H:%M:%S')

        # Calculate available width for the text (80% of the video width)
        max_text_width = int(video_width * 0.8)

        # Dynamically determine font scale based on text width
        text_size = cv2.getTextSize(timestamp_string, cv2.FONT_HERSHEY_SIMPLEX, 1, font_thickness)[0]
        text_width, text_height = text_size

        font_scale = max_text_width / text_width
        
        return font_scale


    def calculate_xy_text_position(video_height: int, video_width: int, timestamp_string: str, font_scale: float, thickness: int) -> tuple[int]:
        # Recalculate text size with the dynamic font scale
        text_size = cv2.getTextSize(timestamp_string, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_width, text_height = text_size

        # Calculate position: centered horizontally, with 10% margin at the bottom
        x_position = (video_width - text_width) // 2  # Center horizontally
        y_position = int(video_height - (video_height * 0.1))  # 10% margin from the bottom

        return x_position, y_position


    # Ensure the input file has the correct extension
    if not original_video_path.endswith('.mp4'):
        original_video_path = original_video_path + '.mp4'

    # Ensure multiplier is an integer greater than 0 or default to 10
    if multiplier <= 0 or not isinstance(multiplier, int):
        raise TypeError("Timelapse multiplier must be a positive integer.")

    # If not specified, rename the output file to the same as input with speed appended to it (e.g. video_4x.mp4)
    if output_video_path is None:
        output_video_path=f'_{multiplier}x.'.join(original_video_path.split('.'))

    vid = cv2.VideoCapture(original_video_path)
    if not vid.isOpened():
        print("Error: Could not open video file.")
        exit()

    fps = vid.get(cv2.CAP_PROP_FPS)
    success, frame = vid.read()
    height, width = frame.shape[:2]

    # Handle cropping setup
    if crop:
        if crop_dimensions is None:
            crop_dimensions = select_crop(frame)

        (x, y), (crop_width, crop_height) = crop_dimensions
        
        # Validate crop dimensions
        if x + crop_width > width or y + crop_height > height:
            print(f"Warning: Crop dimensions ({x}, {y}, {crop_width}, {crop_height}) exceed frame size ({width}, {height})")
            # Adjust crop dimensions to fit within frame
            crop_width = min(crop_width, width - x)
            crop_height = min(crop_height, height - y)
            print(f"Adjusted to: ({x}, {y}, {crop_width}, {crop_height})")
    else:
        crop_width, crop_height = width, height
        x, y = 0, 0

    total_frames = vid.get(cv2.CAP_PROP_FRAME_COUNT)
    if timestamps:
        number_of_timestamps = len(timestamps)

    thickness = 2
    font_scale = calculate_font_scale(crop_width, thickness)  # Use crop_width instead of width

    print('Processing Video.')
    pbar = tqdm(total=total_frames, leave=False)
    # Use crop dimensions for output video
    writer = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (crop_width, crop_height))
    count = 0

    while success:
        if crop:
            # Ensure crop stays within bounds
            finished_frame = frame[y:y+crop_height, x:x+crop_width]
            if finished_frame.shape[:2] != (crop_height, crop_width):
                print(f"Warning: Cropped frame size {finished_frame.shape[:2]} doesn't match expected ({crop_height}, {crop_width})")
        else:
            finished_frame = frame

        if timestamps:
            frame_position = vid.get(cv2.CAP_PROP_POS_FRAMES)
            current_timestamp = timestamps[int(frame_position / total_frames * (number_of_timestamps - 1))]
            timestamp_string = current_timestamp.strftime('%Y-%m-%d %H:%M:%S')
            x_pos, y_pos = calculate_xy_text_position(crop_height, crop_width, timestamp_string, font_scale, thickness)
            cv2.putText(finished_frame, timestamp_string, (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

        if count % multiplier == 0:
            writer.write(finished_frame)

        success, frame = vid.read()
        count += 1
        pbar.update(1)

    pbar.close()
    writer.release()
    vid.release()
    
    print('Video successfully processed.')
    return output_video_path, crop_dimensions


def compress_video(original_video_path: str, compressed_video_path: str = None, quality: str = 'medium', crop: bool = False, custom_resolution: tuple[int,int] = None, codec: str = "libx264") -> str:
    """
    Compresses a video file to a specified quality and codec.

    Args:
        original_video_path (str): The file path of the original video.
        compressed_video_path (str, optional): The desired file path for the compressed video. Defaults to None.
        quality (str): The quality level for the compressed video ('low', 'medium', 'high'). Defaults to 'medium'.
        codec (str): The codec to use for compression. Defaults to 'libx264'.

    Returns:
        str: The file path of the compressed video.

    Raises:
        ValueError: If the quality is not 'low', 'medium', or 'high'.
    """

    # Ensure the input file has the correct extension
    if not original_video_path.endswith('.mp4'):
        original_video_path += '.mp4'

    # If not specified, rename the output file to the same as input with codec and bitrate appended to it (e.g. video_libx264_500K.mp4)
    if compressed_video_path is None:
        compressed_video_path = f'_{codec}_{quality}.'.join(original_video_path.split('.'))

    if quality == 'low':
        bitrate = '250K'
        resolution = (1280, 720)
    elif quality == 'medium':
        bitrate = '500K'
        resolution = (1920, 1080)
    elif quality == 'high':
        bitrate = '1M'
        resolution = (1920, 1080)
    else:
        raise ValueError("Compression quality must be one of: 'low', 'medium', 'high'")

    if crop:
        resolution = custom_resolution

    print('Beginning Video compression.')

    with VideoFileClip(original_video_path, target_resolution=resolution) as video:
        video.write_videofile(compressed_video_path, bitrate=bitrate, codec=codec) #libx264 gave really good compression per runtime
    
    print('Video successfully compressed.')

    return compressed_video_path


def parse_arguments():
    """
    Parses command-line arguments and configuration file for video processing tasks.

    This function identifies and processes configuration files provided in the command-line arguments.
    It initializes the argument parser, sets up subcommands, and defines specific arguments for the 'extract',
    'compress', and 'timelapse' commands. If an invalid command is detected, it displays the help text and exits.

    Returns:
        tuple: Contains parsed command-line arguments and configuration settings.

    """


    config_file = next((arg for arg in sys.argv if arg.endswith(".config")), None) # Returns the first argument that contains the substring '.config'

    # This if/else is necessary to keep the extract subparser from crashing when trying to set defaults.
    if config_file:
        config = import_config(config_file)
        door_number = config['Runtime']['door_number']
        date = config['Runtime']['date']
        start_time = config['Runtime']['start_time']
        end_time = config['Runtime']['end_time']
        filename = config['Runtime']['filename']
        quality = config['Settings']['compression_level']
        timelapse_multiplier = int(config['Settings']['timelapse_multiplier'])
    else:
        config = None
        door_number = None
        date = None
        start_time = None
        end_time = None
        filename = None
        quality = None
        timelapse_multiplier = None


    arg_parser = argparse.ArgumentParser()

    subparsers = arg_parser.add_subparsers(dest='command')

    # Extract mode subcommand
    extract_parser = subparsers.add_parser('extract', help='Extract, timelapse, and compress a video file')
    extract_parser.add_argument('door_number', nargs='?', default=door_number, type=str, help='Door number of camera wanted (must be an integer)')
    extract_parser.add_argument('date', nargs='?', default=date, type=str, help='Date of the requested video. If the footage spans past midnight, provide the date on which the footage starts. (e.g. 3/11)')
    extract_parser.add_argument('start', nargs='?', default=start_time, type=str, help='Starting timestamp of video requested (e.g. 11am)')
    extract_parser.add_argument('end', nargs='?', default=end_time, type=str, help='Ending timestamp of video requested (e.g. 5pm)')
    extract_parser.add_argument('config_file', type=str, help='Filepath of local config file')
    extract_parser.add_argument('-o', '--output_name', default=filename, type=str, help='Desired filepath')
    extract_parser.add_argument('--quality', type=str, default=quality, choices=['low', 'medium', 'high'], help='Desired video quality')
    extract_parser.add_argument('--multiplier', type=int, default=timelapse_multiplier, help='Desired timelapse multiplier (must be a positive integer)')
    extract_parser.add_argument('-c', '--crop', action='store_true', help='Crop the video. Set by config file or query user.')

    # Compress subcommand
    compress_parser = subparsers.add_parser('compress', help='Compress a video file')
    compress_parser.add_argument('video_filename', type=str, help='Video file to compress')
    compress_parser.add_argument('compression_quality', default=quality, type=str, choices=['low', 'medium', 'high'], help='Desired compression quality')
    compress_parser.add_argument('-o', '--output_name', default=filename, type=str, help='Desired filepath')

    # Timelapse subcommand
    timelapse_parser = subparsers.add_parser('timelapse', help='Create a timelapse video')
    timelapse_parser.add_argument('video_filename', type=str, help='Video file for timelapse')
    timelapse_parser.add_argument('multiplier', type=int, default=timelapse_multiplier, help='Desired timelapse multiplier (must be a positive integer)')
    timelapse_parser.add_argument('-o', '--output_name', default=filename, type=str, help='Desired filepath')

    # Prints help text if the command doesn't begin with default, timelapse, or compress
    if len(sys.argv) < 2 or sys.argv[1] not in ['extract', 'timelapse', 'compress']:
        arg_parser.print_help()
        exit(1)

    return arg_parser.parse_args(), config


def convert_input_to_datetime(date:str, start:str, end:str) -> tuple[datetime, datetime]:
    '''Takes simple tokens for date and time and returns start and end as datetimes.'''
    
    start_datetime = duparse(f'{date} {start}')
    end_datetime = duparse(f'{date} {end}')

    # Adjust the date's year from the current year to the previous if the date hasn't happened yet.
    if start_datetime > datetime.now():
        start_datetime = start_datetime - relativedelta(years=1)
        end_datetime = end_datetime - relativedelta(years=1)

    # Adjust the end timestamp date to the following day if the end time occurs earlier than the start time.
    if end_datetime < start_datetime :
        end_datetime = end_datetime + timedelta(days=1)

    return start_datetime, end_datetime


def main():
    """
    Main entry point of the script.
    This function handles various video processing tasks including extraction, compression, 
    and timelapse creation based on the command-line arguments provided.

    Workflow:
    - Parses command-line arguments and configuration settings.
    - If the command is 'extract', retrieves video from the server, processes it with a timelapse effect, and compresses it.
    - If the command is 'compress', compresses an existing video file.
    - If the command is 'timelapse', applies a timelapse effect to an existing video file.

    Arguments:
    None (parses command-line arguments internally).

    Configuration:
    - Auth: Authentication credentials including user and password.
    - Cameras: Camera IDs using door number as key.
    - Settings: Timezone, timelapse multiplier, and compression level.
    - Network: Server IP address.
    - Runtime: Door number, filename, date, start_time, and end_time.

    Returns:
    None
    """
    
    args, config = parse_arguments()

    if args.command == 'extract':
    
        username = config['Auth']['user']
        password = config['Auth']['password']
        cameras = config['Cameras']
        timezone = config['Settings']['timezone']
        server_ip = config['Network']['server_ip']

        start, end = convert_input_to_datetime(args.date, args.start, args.end)

        timezone = ZoneInfo(timezone)

        # Instantiate api class and retrieve video
        exapi = Exacqvision(server_ip, username, password, timezone)
        extracted_video_name = exapi.get_video(cameras.get(args.door_number), start, end, video_filename=args.output_name)
        video_timestamps = exapi.get_timestamps(cameras.get(args.door_number), start, end)
        exapi.logout()

        # Process video after extraction
        try:
            crop_dimensions=literal_eval(config['Settings']['crop_dimensions'])
            # print(crop_dimensions)
        except:
            crop_dimensions=None

        processed_video_path,crop_dimensions = process_video(extracted_video_name, multiplier=args.multiplier, timestamps=video_timestamps, crop=args.crop, crop_dimensions=crop_dimensions)
        compress_video(processed_video_path, quality=args.quality, crop=args.crop, custom_resolution=crop_dimensions[1])

    elif args.command == 'compress':
        compress_video(args.video_filename, args.output_name, quality=args.compression_quality, crop=args.crop, custom_resolution=crop_dimensions[1])

    elif args.command == 'timelapse':

        process_video(args.video_filename, args.output_name, multiplier=args.multiplier)


if __name__ == "__main__":
    
    main()
