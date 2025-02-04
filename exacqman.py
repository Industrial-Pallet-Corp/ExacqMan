
from configparser import ConfigParser
from moviepy import VideoFileClip
from cv2 import VideoCapture, VideoWriter, VideoWriter_fourcc, CAP_PROP_FPS
import exacvision as exapi
import argparse
import sys


def import_config(config_file):
    config = ConfigParser()
    config.read(config_file)

    if validate_config(config) == False:
        quit

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


def timelapse_video(original_video_path, timelapsed_video_path=None, multiplier=10):
    '''timelapses a video by the multiplier (must be an integer)'''

    # If not specified, rename the output file to the same as input with speed appended to it (e.g. video_4x.mp4)
    if timelapsed_video_path is None:
        timelapsed_video_path=f'_{multiplier}x.'.join(original_video_path.split('.'))

    vid = VideoCapture(original_video_path)
    fps = vid.get(CAP_PROP_FPS)  # Get the original frames per second
    success, frame = vid.read()
    height, width, layers = frame.shape #set the right resolution 
    print('Beginning timelapse')
    writer = VideoWriter(timelapsed_video_path, VideoWriter_fourcc(*"MP4V"), fps, (width, height))
    count = 0

    while success:
        if count % multiplier == 0:  
            writer.write(frame)
            
        success, frame = vid.read()
        count += 1

    writer.release()
    vid.release()
    
    print('Video successfully timelapsed.')
    return timelapsed_video_path


def compress_video(original_video_path, compressed_video_path=None, quality = 'medium', codec = "libx264"):
    '''Compresses video at a provided bitrate'''

    # If not specified, rename the output file to the same as input with codec and bitrate appended to it (e.g. video_libx264_500K.mp4)
    if compressed_video_path is None:
        compressed_video_path = f'_{codec}_{quality}.'.join(original_video_path.split('.'))

    if quality == 'low':
        bitrate = "250K"
        resolution = (1280, 720)
    elif quality == 'medium':
        bitrate = "500K"
        resolution = (1920, 1080)
    elif quality == 'high':
        bitrate = "1M"
        resolution = (3840, 2160)
    else:
        print('please enter a valid compression quality')
        quit

    video = VideoFileClip(original_video_path)
    print('Beginning Video compression.')
    video.write_videofile(compressed_video_path, bitrate=bitrate, codec=codec) #libx264 gave really good compression per runtime
    print('Video successfully compressed.')

    return compressed_video_path


def main():
    # TODO final main should take (door_number, start, end) as parameters, for now it just timelapses and compresses a video file
    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument('door_number', type=str, help='door number of camera wanted')
    arg_parser.add_argument('start', type=str, help='starting timestamp of video requested')
    arg_parser.add_argument('end', type=str, help='ending timestamp of video requested')
    arg_parser.add_argument('config_file', type=str, help='filepath of local config file')
    arg_parser.add_argument('--output_name', type=str, help='desired filepath')
    arg_parser.add_argument('--quality', type=str, help='desired video quality (low, medium, high)')

    args = arg_parser.parse_args()
    
    config = import_config(args.config_file)

    username = config['Auth']['user']
    password = config['Auth']['password']
    cameras = config['Cameras']
    multiplier = int(config['Settings']['timelapse_multiplier'])
    quality = config['Settings']['compression_level']


    session, camera_list = exapi.login(username, password)
    extracted_video_name = exapi.get_video(session, cameras.get(args.door_number), args.start, args.end, video_filename=args.output_name) #'2025-01-16T14:50:21Z', '2025-01-16T15:35:21Z')
    exapi.logout(session)

    timelapsed_video_path = timelapse_video(extracted_video_name, multiplier=multiplier)
    compress_video(timelapsed_video_path, quality=quality)



if __name__ == "__main__":
    # if len(sys.argv) != 4:
    #     print("Program usage requires parameters (Example: exacqman.py 8 2025-01-15T14:50:21Z 2025-01-15T15:50:21Z)")
    # main(sys.argv[1], sys.argv[2], sys.argv[3]) # reads the arguments from the command line interface
    # TODO add error checking to ensure format of CLI command is correct
    main()

