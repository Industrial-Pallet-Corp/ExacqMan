import requests, json
from time import sleep
from pprint import pprint
from tqdm import tqdm
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class Exacqvision:
    
    def __init__(self, base_url:str, username: str, password: str, timezone: ZoneInfo):
        self.base_url = base_url
        self.timezone = timezone
        self.session = self.login(username, password)


    def login(self, username: str, password: str) -> tuple[str, list[int]]:
        """
        Logs user into Exacqvision's API.

        Args:
            username (str): The username for the Exacqvision API.
            password (str): The password for the Exacqvision API.

        Returns:
            session_id (str): session_id to authorize other API calls.
            cameras (int[]): A list of camera IDs available to the user.

        Note that session_id is required for many other API calls.
        """

        url = f"{self.base_url}/v1/login.web"

        payload = f'u={username}&p={password}&responseVersion=2&s=0'
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        session_id = json.loads(response.text)['sessionId']

        #pprint(response.json())
        # print(session_id)
        return session_id


    def logout(self):
        '''Logs user out using a valid session_id'''

        if self.session:
            url = f"{self.base_url}/v1/logout.web?s={self.session}"
            response = requests.request("POST", url)
            return(response.text)
        else:
            print("No active session to logout.")


    def list_cameras(self):
        url = f"{self.base_url}v1/config.web?s={self.session}&output=json"

        response = requests.request("GET", url)
        cameras = json.loads(response.text)['Cameras']
        return cameras


    def convert_GMT_to_local(self, timestamp: str) -> str:
        '''Converts timezones so that the API returns the correct timestamps.'''

        # Parse the input string and assign the timezone in one line
        gmt_datetime = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=ZoneInfo('GMT'))

        # Convert to GMT timezone
        local_datetime = gmt_datetime.astimezone(self.timezone)

        # Format the result to include 'Z' at the end
        local_time = local_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')

        return local_time


    def convert_local_to_GMT(self, timestamp: str) -> str:
        '''Converts timezones so that the API returns the correct footage.'''

        # Parse the input string and assign the timezone in one line
        local_datetime = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=self.timezone)

        # Convert to GMT timezone
        gmt_datetime = local_datetime.astimezone(ZoneInfo('GMT'))

        # Format the result to include 'Z' at the end
        gmt_time = gmt_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')

        return gmt_time
    

    def create_search(self, camera_id: int, start: str, stop: str) -> tuple[str, requests.Response]:
        """
        Creates a search request for video recordings.

        Args:
            session (str): The session ID for authentication.
            camera_id (int): The ID of the camera to search.
            start (str): The start time of the search in RFC3339 UTC format.
            stop (str): The stop time of the search in RFC3339 UTC format.

        Returns:
            tuple: A tuple containing:
                - str: The search ID of the created search.
                - requests.Response: The response object from the search request.

        Raises:
            requests.exceptions.RequestException: If the request fails.

        Example:
            search_id, response = create_search(session='abcd1234', camera_id=1, start='2022-01-01T00:00:00Z', stop='2022-01-01T01:00:00Z')
        """

        # Convert timestamps to GMT
        start = self.convert_local_to_GMT(start)
        stop = self.convert_local_to_GMT(stop)

        url = f"{self.base_url}/v1/search.web?s={self.session}&start={start}&end={stop}&camera={camera_id}&output=json"
        # print(url)

        response = requests.request("GET", url)
        
        if response.status_code != 200: 
            print(f'Search request failed with status code: {response.status_code}')

        search_id = json.loads(response.text)['search_id']

        # pprint(response.json())

        return search_id, response


    def export_request(self, camera_id: int, start: str, stop: str, name: str=None) -> str:
        """
        Initiates an export request for video recordings.

        Args:
            session (str): The session ID for authentication.
            camera_id (int): The ID of the camera to export video from.
            start (str): The start time of the export in ISO 8601 format.
            stop (str): The end time of the export in ISO 8601 format.
            name (str, optional): The name of the exported file. Defaults to None.

        Returns:
            str: The export ID of the created export request.

        Raises:
            requests.exceptions.RequestException: If the request fails.

        Example:
            export_id = export_request(session='abcd1234', camera_id=1, start='2022-01-01T00:00:00Z', stop='2022-01-01T01:00:00Z', name='video_export')
        """

        # Convert timestamps to GMT
        start = self.convert_local_to_GMT(start)
        stop = self.convert_local_to_GMT(stop)

        url = f"{self.base_url}/v1/export.web?camera={camera_id}&s={self.session}&start={start}&end={stop}&format=mp4"
        if name:
            url = url+f'&name={name}'

        print('Creating export request.')
        response = requests.request("GET", url)
        # pprint(response.json())
        export_id = json.loads(response.text)['export_id']
        print(f'Export request created. Export ID is {export_id}')

        return export_id


    def export_status(self, export_id:str) -> bool:

        url = f"{self.base_url}/v1/export.web?export={export_id}"

        response = requests.request("GET", url)
        progress = json.loads(response.text)['progress']
        #pprint(response.json())
        
        if progress == 100:
            print('Export ready')
            return True
        else:
            print(f'Export in progress: {progress}% complete')
            return False


    def export_download(self, export_id:str) -> str:

        url = f"{self.base_url}/v1/export.web?export={export_id}&action=download"

        response = requests.get(url, stream=True)

        file_name = response.headers.get('Content-Disposition').split('filename=')[-1].strip('"')

        total_size = int(response.headers.get('content-length', 0))

        # Open the file in write-binary mode and initialize the progress bar
        with open(file_name, 'wb') as file, tqdm(
            desc=file_name,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
            leave=False
            # file=sys.stdout,  # Ensure progress bar prints to standard output
            # ncols=80,  # Adjust the width of the progress bar
        ) as bar:
            # Iterate over the response data in chunks and update the progress bar
            for data in response.iter_content(chunk_size=1024):
                size = file.write(data)
                bar.update(size)
                # sys.stdout.flush()  # Force flush standard output

        print(f"Video saved successfully as {file_name}!")

        return file_name


    def export_delete(self, export_id:str):

        url = f"{self.base_url}/v1/export.web?export={export_id}&action=finish"

        response = requests.request("GET", url)
        
        return(response.text)


    def get_video(self, camera: int, start: str, stop: str, video_filename: str):
        ''' 
        TODO add error checking for different fail states (export status stuck at 0)
        '''

        export_id = self.export_request(camera, start, stop, name = video_filename)

        sleep(2)  # Wait briefly before checking the status of the export
        
        count = 0
        while not self.export_status(export_id) and count<5:
            sleep(5)
            count += 1
        
        if count < 10:
            filename = self.export_download(export_id)
        else:
            print('Export failed. Deleting request')

        sleep(2)  # Give time after downloading before attempting delete
        self.export_delete(export_id)
        
        if filename:
            return filename
        else:
            return None
        
        
    def get_timestamps(self, camera_id: int, start: str, stop: str) -> list[datetime]:
        '''Extracts timestamps from create_search and converts them into a list of datetime objects, each representing one second of the video.'''
        
        search_id, response = self.create_search(camera_id, start, stop)

        clips = json.loads(response.text)['videoInfo'][0]['clips']

        # Returns list of all seconds between two times
        def generate_time_range(start_time, stop_time, stepsize=1):

            # Change to local time and convert to datetime
            start_time = datetime.strptime(self.convert_GMT_to_local(start_time), '%Y-%m-%dT%H:%M:%SZ')
            stop_time = datetime.strptime(self.convert_GMT_to_local(stop_time), '%Y-%m-%dT%H:%M:%SZ')

            delta = timedelta(seconds=stepsize)

            times = []
            while start_time <= stop_time:
                times.append(start_time)
                start_time += delta

            return times

        # Stretch every start/end time from clips into seconds
        ranged_timestamps = list(map(lambda x: generate_time_range(x['startTime'], x['endTime']), clips))

        # Flatten the timestamps into a one dimensional list.
        flattened_timestamps = [item for sublist in ranged_timestamps for item in sublist]

        # Filter out timestamp duplicates while maintaining their order.
        unique_timestamps = list(dict.fromkeys(flattened_timestamps))
        
        # Remove timestamps outside of the original start and stop times.
        start = datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ')
        stop = datetime.strptime(stop, '%Y-%m-%dT%H:%M:%SZ')
        finished_timestamps = [x for x in unique_timestamps if x>=start and x<=stop]

        return finished_timestamps
        
    