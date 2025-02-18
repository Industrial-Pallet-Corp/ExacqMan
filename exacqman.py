
from configparser import ConfigParser
from moviepy import VideoFileClip
from cv2 import VideoCapture, VideoWriter, VideoWriter_fourcc, putText, CAP_PROP_FPS, CAP_PROP_FRAME_COUNT, CAP_PROP_POS_FRAMES, FONT_HERSHEY_SIMPLEX, LINE_AA
from datetime import datetime
from zoneinfo import ZoneInfo
import exacqvision
import argparse
from tqdm import tqdm
import sys



def import_config(config_file):
    config = ConfigParser()
    config.read(config_file)

    if validate_config(config) == False:
        exit(1)

    return config


def validate_config(config):

    errors = []
    fatal = False

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
        errors.append('timelapse_multiplier is missing or empty. Program will default to 10')
    else:
        try:
            int(config['Settings']['timelapse_multiplier'])
        except ValueError:
            errors.append('timelapse_multiplier must be an integer')
            fatal = True

    if 'compression_level' not in config['Settings'] or not config['Settings']['compression_level'].strip():
        errors.append('compression_level is missing or empty. Program will default to medium')

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


def timelapse_video(original_video_path, timelapsed_video_path=None, multiplier=10, timestamps = None):
    '''timelapses a video by the multiplier (must be an integer)'''

    # If not specified, rename the output file to the same as input with speed appended to it (e.g. video_4x.mp4)
    if timelapsed_video_path is None:
        timelapsed_video_path=f'_{multiplier}x.'.join(original_video_path.split('.'))

    vid = VideoCapture(original_video_path)

    if not vid.isOpened():
        print("Error: Could not open video file.")
        exit()

    fps = vid.get(CAP_PROP_FPS)  # Get the original frames per second
    success, frame = vid.read()
    height, width, layers = frame.shape # Set the right resolution
    total_frames = vid.get(CAP_PROP_FRAME_COUNT)
    if timestamps:
        number_of_timestamps = len(timestamps)
    pbar = tqdm(total=total_frames) # Initialize the progress bar

    print('Beginning timelapse')
    writer = VideoWriter(timelapsed_video_path, VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    count = 0

    while success:
        
        if timestamps:
            frame_position = vid.get(CAP_PROP_POS_FRAMES)
            current_timestamp = timestamps[int(frame_position/total_frames*(number_of_timestamps-1))]
            timestamp_string = current_timestamp.strftime('%Y-%m-%d %H:%M:%S')

            # Add the timestamp to the bottom left of the video
            putText(frame, timestamp_string, (10, height - 10), FONT_HERSHEY_SIMPLEX, 5.0, (0,255,0), 3, LINE_AA)

        if count % multiplier == 0:  
            writer.write(frame)
            
        success, frame = vid.read()
        count += 1

        pbar.update(1)

    writer.release()
    vid.release()
    
    print('Video successfully timelapsed.')
    return timelapsed_video_path


def compress_video(original_video_path, compressed_video_path=None, quality = 'medium', codec = "libx264"):
    '''Compresses mp4 video at a provided bitrate'''

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
        print('please enter a valid compression quality')
        exit(1)

    video = VideoFileClip(original_video_path, target_resolution=resolution)
    print('Beginning Video compression.')
    video.write_videofile(compressed_video_path, bitrate=bitrate, codec=codec) #libx264 gave really good compression per runtime
    
    print('Video successfully compressed.')

    return compressed_video_path


def parse_arguments():

    arg_parser = argparse.ArgumentParser()

    subparsers = arg_parser.add_subparsers(dest='command')

    # Default mode subcommand
    default_parser = subparsers.add_parser('default', help='Extract, timelapse, and compress a video file')
    default_parser.add_argument('door_number', type=str, help='Door number of camera wanted')
    default_parser.add_argument('start', type=str, help='Starting timestamp of video requested')
    default_parser.add_argument('end', type=str, help='Ending timestamp of video requested')
    default_parser.add_argument('config_file', type=str, help='Filepath of local config file')
    default_parser.add_argument('-o', '--output_name', type=str, help='Desired filepath')
    default_parser.add_argument('--quality', type=str, choices=['low', 'medium', 'high'], help='Desired video quality')
    default_parser.add_argument('--multiplier', type=int, help='Desired timelapse multiplier (must be a positive integer)')

    # Compress subcommand
    compress_parser = subparsers.add_parser('compress', help='Compress a video file')
    compress_parser.add_argument('video_filename', type=str, help='Video file to compress')
    compress_parser.add_argument('compression_quality', type=str, choices=['low', 'medium', 'high'], help='Desired compression quality')
    compress_parser.add_argument('-o', '--output_name', type=str, help='Desired filepath')

    # Timelapse subcommand
    timelapse_parser = subparsers.add_parser('timelapse', help='Create a timelapse video')
    timelapse_parser.add_argument('video_filename', type=str, help='Video file for timelapse')
    timelapse_parser.add_argument('multiplier', type=int, help='Desired timelapse multiplier (must be a positive integer)')
    timelapse_parser.add_argument('-o', '--output_name', type=str, help='Desired filepath')

    # Prints help text if the command doesn't begin with default, timelapse, or compress
    if len(sys.argv) < 2 or sys.argv[1] not in ['default', 'timelapse', 'compress']:
        arg_parser.print_help()
        exit(1)

    return arg_parser.parse_args()


def main():
    
    args = parse_arguments()

    if args.command == 'default':
    
        config = import_config(args.config_file)

        username = config['Auth']['user']
        password = config['Auth']['password']
        cameras = config['Cameras']
        timezone = config['Settings']['timezone']
        server_ip = config['Network']['server_ip']

        if args.multiplier:
            multiplier = args.multiplier
        else:
            multiplier = int(config['Settings']['timelapse_multiplier'])

        if args.quality:
            quality = args.quality
        else:
            quality = config['Settings']['compression_level']

        timezone = ZoneInfo(timezone)

        # Instantiate api class and retrieve video
        exapi = exacqvision.Exacqvision(server_ip, username, password, timezone)
        extracted_video_name = exapi.get_video(cameras.get(args.door_number), args.start, args.end, video_filename=args.output_name) #'2025-01-16T14:50:21Z', '2025-01-16T15:35:21Z')
        video_timestamps = exapi.get_timestamps(cameras.get(args.door_number), args.start, args.end)
        exapi.logout()

        # Process video after extraction
        timelapsed_video_path = timelapse_video(extracted_video_name, multiplier=multiplier, timestamps = video_timestamps)
        compress_video(timelapsed_video_path, quality=quality)

    if args.command == 'compress':

        compress_video(args.video_filename, args.output_name, quality=args.compression_quality)

    if args.command == 'timelapse':

        timelapse_video(args.video_filename, args.output_name, multiplier=args.multiplier)


if __name__ == "__main__":
    
    main()

    # config = import_config('mydefault.config')

    # username = config['Auth']['user']
    # password = config['Auth']['password']
    # cameras = config['Cameras']
    # timezone = config['Settings']['timezone']
    # server_ip = config['Network']['server_ip']

    # exapi = exacqvision.Exacqvision(server_ip, username, password, ZoneInfo(timezone))
    # print(exapi.get_timestamps('3483648', '2025-02-06T18:29:30Z', '2025-02-06T18:30:00Z'))

