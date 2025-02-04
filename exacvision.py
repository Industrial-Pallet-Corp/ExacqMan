import requests, json
from time import sleep
from pprint import pprint
from tqdm import tqdm

base_url = "http://10.20.4.12"

def login(username: str, password: str) -> tuple[str, list[int]]:
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

    url = f"{base_url}/v1/login.web"

    payload = f'u={username}&p={password}&responseVersion=2&s=0'
    headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    session_id = json.loads(response.text)['sessionId']
    cameras = json.loads(response.text)['group']['cameras']

    #pprint(response.json())
    # print(session_id)
    return session_id, cameras


def logout(session: str):
    '''Logs user out using a valid session_id'''

    if session:
        url = f"{base_url}/v1/logout.web?s={session}"
        response = requests.request("POST", url)
        return(response.text)
    else:
        print("No active session to logout.")


def list_cameras(session):
    url = f"{base_url}v1/config.web?s={session}&output=json"

    response = requests.request("GET", url)
    cameras = json.loads(response.text)['Cameras']
    return cameras


def create_search(session: str, camera_id: int, start: str, stop: str) -> str:
    """
    Creates a search request for video recordings.

    Args:
        session (str): The session ID for authentication.
        camera_id (int): The ID of the camera to search.
        start (str): The start time of the search in RFC3339 UTC format.
        stop (str): The stop time of the search in RFC3339 UTC format.

    Returns:
        str: The search ID of the created search.

    Raises:
        requests.exceptions.RequestException: If the request fails.

    Example:
        search_id = create_search(session='abcd1234', camera_id=1, start='2022-01-01T00:00:00Z', stop='2022-01-01T01:00:00Z')
    """

    url = f"{base_url}/v1/search.web?s={session}&start={start}&end={stop}&camera={camera_id}&output=json"
    print(url)

    response = requests.request("GET", url)
    
    if response.status_code == 200: 
        print('Request succeeded') 
    else: 
        print(f'Request failed with status code: {response.status_code}')

    search_id = json.loads(response.text)['search_id']

    # pprint(response.json())

    return search_id


def export_request(session: str, camera_id: int, start: str, stop: str, name: str=None) -> str:
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

    url = f"{base_url}/v1/export.web?camera={camera_id}&s={session}&start={start}&end={stop}&format=mp4"
    if name:
        url = url+f'&name={name}'

    response = requests.request("GET", url)
    export_id = json.loads(response.text)['export_id']
    # pprint(response.json())

    return export_id


def export_status(export_id:str) -> bool:

    url = f"{base_url}/v1/export.web?export={export_id}"

    response = requests.request("GET", url)
    progress = json.loads(response.text)['progress']
    #pprint(response.json())
    
    if progress == 100:
        print('Export ready')
        return True
    else:
        print(f'Export in progress: {progress}% complete')
        return False


def export_download(export_id:str) -> str:

    url = f"{base_url}/v1/export.web?export={export_id}&action=download"

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


def export_delete(export_id:str):

    url = f"{base_url}/v1/export.web?export={export_id}&action=finish"

    response = requests.request("GET", url)
    
    return(response.text)


def get_video(session: str, camera: int, start: str, stop: str, video_filename: str):
    ''' 
    TODO add error checking for different fail states (export status stuck at 0)
    '''

    export_id = export_request(session, camera, start, stop, name = video_filename)

    sleep(2)  # Wait briefly before checking the status of the export
    
    count = 0
    while not export_status(export_id) and count<5:
        sleep(5)
        count += 1
    
    if count < 10:
        filename = export_download(export_id)
    else:
        print('Export failed. Deleting request')

    sleep(2)  # Give time after downloading before attempting delete
    export_delete(export_id)
    
    if filename:
        return filename
    else:
        return None
