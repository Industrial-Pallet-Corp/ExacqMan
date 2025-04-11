import requests, json
from requests.exceptions import RequestException
from time import sleep
from pprint import pprint
from tqdm import tqdm
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class ExacqvisionError(Exception):
    """Custom exception for Exacqvision API errors."""
    pass


class ExacqvisionTimeoutError(ExacqvisionError):
    """Custom exception for Exacqvision API timeout errors."""
    pass


class Exacqvision:
    """
    Interface for interacting with the Exacqvision API to manage video exports and camera data.

    Attributes:
        base_url (str): Base URL of the Exacqvision server.
        timezone (ZoneInfo): Timezone for handling timestamps.
        session (str): Session ID for authenticated API calls.
    """
    
    def __init__(self, base_url:str, username: str, password: str, timezone: ZoneInfo):
        self.base_url = base_url
        self.timezone = timezone
        self.session = self.login(username, password)


    def login(self, username: str, password: str) -> str:
        """
        Authenticates with the Exacqvision API and retrieves a session ID.

        Args:
            username (str): Username for authentication.
            password (str): Password for authentication.

        Returns:
            str: Session ID for subsequent API calls.
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
        """
        Retrieves a list of cameras available on the Exacqvision server.

        Returns:
            list: List of camera details.
        """
        url = f"{self.base_url}/v1/config.web?s={self.session}&output=json"

        response = requests.request("GET", url)
        cameras = json.loads(response.text)['Cameras']
        return cameras


    def convert_GMT_to_local(self, time: datetime) -> datetime:
        '''Converts a GMT datetime to the local timezone.'''

        # Parse the input string and assign the timezone in one line
        gmt_datetime = time.replace(tzinfo=ZoneInfo('GMT'))

        # Convert to GMT timezone
        local_datetime = gmt_datetime.astimezone(self.timezone)

        return local_datetime


    def convert_local_to_GMT(self, time: datetime) -> datetime:
        '''Converts a local timezone datetime to GMT.'''

        # Parse the input string and assign the timezone in one line
        local_datetime = time.replace(tzinfo=self.timezone)

        # Convert to GMT timezone
        gmt_datetime = local_datetime.astimezone(ZoneInfo('GMT'))

        return gmt_datetime
    

    def convert_datetime_to_iso8601(self, timezone: ZoneInfo, *datetimes: datetime) -> tuple[str]:
        '''Adds timezone data to datetimes, then converts to timestamps in ISO8601 format'''
        return tuple(dt.replace(tzinfo=timezone).isoformat() for dt in datetimes)
    

    def create_search(self, camera_id: int, start: datetime, stop: datetime) -> tuple[str, requests.Response]:
        """
        Creates a search request for video recordings within a time range.

        Args:
            camera_id (int): ID of the camera.
            start (datetime): Start time of the search.
            stop (datetime): End time of the search.

        Returns:
            tuple[str, requests.Response]: Search ID and the API response.

        Raises:
            ExacqvisionError: If the search request fails.
        """

        # Convert datetimes into timestamps
        start, stop = self.convert_datetime_to_iso8601(self.timezone, start, stop)

        url = f"{self.base_url}/v1/search.web?s={self.session}&start={start}&end={stop}&camera={camera_id}&output=json"
        # print(url)

        try:
            response = requests.request("GET", url)
            response.raise_for_status()
            search_id = json.loads(response.text)['search_id']
            return search_id, response
        except (RequestException, ValueError, KeyError) as e:
            raise ExacqvisionError(f"Export request failed: {str(e)}")


    def export_request(self, camera_id: int, start: datetime, stop: datetime, name: str=None) -> str:
        """
        Initiates a video export request.

        Args:
            camera_id (int): ID of the camera.
            start (datetime): Start time of the video.
            stop (datetime): End time of the video.
            name (str, optional): Desired name for the exported file.

        Returns:
            str: Export ID for tracking the request.

        Raises:
            ExacqvisionError: If the export request fails.
        """

        # Convert datetimes into timestamps
        start, stop = self.convert_datetime_to_iso8601(self.timezone, start, stop)

        url = f"{self.base_url}/v1/export.web?camera={camera_id}&s={self.session}&start={start}&end={stop}&format=mp4"
        if name:
            url = url+f'&name={name}'

        cameras = self.list_cameras()
        if not any(int(camera['id']) == int(camera_id) for camera in cameras):
            raise ExacqvisionError(f'CameraID: {camera_id} is not found in server')

        print('Creating export request.')
        try:
            response = requests.request("GET", url)
            response.raise_for_status()
            export_id = json.loads(response.text).get('export_id')
            if not export_id:
                raise ExacqvisionError("Export creation failed: No export ID found in the response.")
            print(f'Export request created. Export ID is {export_id}')
            return export_id
        except (RequestException, ValueError, KeyError) as e:
            raise ExacqvisionError(f"Export request failed: {str(e)}")


    def export_status(self, export_id:str) -> bool:
        """
        Checks the status of an export request.

        Args:
            export_id (str): ID of the export request.

        Returns:
            bool: True if the export is complete (100%), False otherwise.
        """
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
        """
        Downloads the completed video export.

        Args:
            export_id (str): ID of the export request.

        Returns:
            str: Path to the downloaded video file.
        """

        url = f"{self.base_url}/v1/export.web?export={export_id}&action=download"

        response = requests.get(url, stream=True) # Setting stream to true is necessary to keep the progress bar updating while downloading the file.

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
            # ncols=80,  # Adjust the width of the progress bar
        ) as bar:
            # Iterate over the response data in chunks and update the progress bar
            for data in response.iter_content(chunk_size=1024):
                size = file.write(data)
                bar.update(size)

        print(f"Video saved successfully as {file_name}!")

        return file_name


    def export_delete(self, export_id:str):
        '''Deletes an export request from the server.'''
        url = f"{self.base_url}/v1/export.web?export={export_id}&action=finish"

        response = requests.request("GET", url)
        
        return(response.text)


    def get_video(self, camera: int, start: datetime, stop: datetime, video_filename: str, timeout: int = 25):
        """
        Exports and downloads a video from the specified camera and time range.

        Args:
            camera (int):           ID of the camera.
            start (datetime):       Start time of the search as a datetime object.
            stop (datetime):        End time of the search as a datetime object.
            video_filename (str):   Desired name for the exported video file.
            timeout (int):          How many seconds the script will wait for export_status to be 100%

        Returns:
            str: Path to the downloaded video file.

        Raises:
            ExacqvisionError: If the export or download fails.
            ExacqvisionTimeoutError: If the export does not complete within the timeout.
        """
        export_id = None
        try:
            export_id = self.export_request(camera, start, stop, name=video_filename)
            sleep(2)  # Wait briefly before checking status

            elapsed_time = 0
            while not self.export_status(export_id) and elapsed_time < timeout:
                sleep(5)
                elapsed_time += 5

            if elapsed_time >= timeout:
                raise ExacqvisionTimeoutError(f"Export {export_id} failed to complete within time.")

            return self.export_download(export_id)

        except ExacqvisionError as e:
            raise ExacqvisionError(f"Failed to get video: {str(e)}")
        finally:
            if export_id:
                sleep(2)  # Ensure download completes before cleanup
                self.export_delete(export_id)  # Clean up export request
        
        
    def get_timestamps(self, camera_id: int, start: datetime, stop: datetime) -> list[datetime]:
        """
        Retrieves timestamps for video clips within a time range.

        Args:
            camera_id (int): ID of the camera.
            start (datetime): Start time of the range.
            stop (datetime): End time of the range.

        Returns:
            list[datetime]: List of unique timestamps (one per second) in the local timezone.
        """
        
        search_id, response = self.create_search(camera_id, start, stop)

        clips = json.loads(response.text)['videoInfo'][0]['clips']

        # Returns list of all seconds between two times
        def generate_time_range(start_time, stop_time, stepsize=1):

            # Change to datetime object and then convert to local timezone
            start_datetime = self.convert_GMT_to_local(datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ'))
            stop_datetime = self.convert_GMT_to_local(datetime.strptime(stop_time, '%Y-%m-%dT%H:%M:%SZ'))

            delta = timedelta(seconds=stepsize)

            times = []
            while start_datetime <= stop_datetime:
                times.append(start_datetime)
                start_datetime += delta

            return times

        # Stretch every start/end time from clips into seconds
        ranged_timestamps = list(map(lambda x: generate_time_range(x['startTime'], x['endTime']), clips))

        # Flatten the timestamps into a one dimensional list.
        flattened_timestamps = [item for sublist in ranged_timestamps for item in sublist]

        # Filter out timestamp duplicates while maintaining their order.
        unique_timestamps = list(dict.fromkeys(flattened_timestamps))
        
        # Add timezone info to start and stop datetimes to prevent crashing due to them being offset-naive
        start = start.replace(tzinfo=self.timezone)
        stop =  stop.replace(tzinfo=self.timezone)

        # Remove timestamps outside of the original start and stop times.
        finished_timestamps = [x for x in unique_timestamps if x>=start and x<=stop]

        return finished_timestamps
    