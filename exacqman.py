
from configparser import ConfigParser
from moviepy import VideoFileClip
from cv2 import VideoCapture, VideoWriter, VideoWriter_fourcc, CAP_PROP_FPS
import exacqman_api
import sys


def import_config():
    '''deprecated unless another use comes up (code is duplicated in main())'''

    config = ConfigParser()
    config.read('config.ini')

    username = config['Auth']['user']
    password = config['Auth']['password']

    print (f'{username} : {password}')
    return config


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


def compress_video(original_video_path, compressed_video_path=None, target_bitrate="500K", codec = "libx264"):
    '''Compresses video at a provided bitrate'''

    # If not specified, rename the output file to the same as input with codec and bitrate appended to it (e.g. video_libx264_500K.mp4)
    if compressed_video_path is None:
        compressed_video_path = f'_{codec}_{target_bitrate}.'.join(original_video_path.split('.'))

    video = VideoFileClip(original_video_path)
    print('Beginning Video compression.')
    video.write_videofile(compressed_video_path, bitrate=target_bitrate, codec=codec) #libx264 gave really good compression per runtime
    print('Video successfully compressed.')

    return compressed_video_path


def main(extracted_video):
    # TODO final main should take (door_number, start, end) as parameters, for now it just timelapses and compresses a video file

    '''config = ConfigParser()
    config.read('config.ini')

    username = config['Auth']['user']
    password = config['Auth']['password']'''


    #extracted_video = "C:/Users/bluea/Python/Test Workspace/video_tweaking/python-test.mp4"
    timelapsed_video_path = timelapse_video(extracted_video)
    compress_video(timelapsed_video_path)



if __name__ == "__main__":
    main(sys.argv[1]) # reads the file from the command line interface
    # TODO add error checking to ensure format of CLI command is correct

