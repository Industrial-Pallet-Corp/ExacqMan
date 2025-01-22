import requests, json
from pprint import pprint

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

    pprint(response.json())
    print(session_id)
    return session_id, cameras


def logout(session):
    '''Logs user out using a valid session_id'''

    if session:
        url = f"{base_url}/v1/logout.web?s={session}"
        response = requests.request("POST", url)
        print(response.text)
    else:
        print("No active session to logout.")


def create_search(session, cameraId, start, stop):
    url = f"{base_url}/v1/search.web?s={session}&start={start}&end={stop}&camera={cameraId}&output=json"
    print(url)

    response = requests.request("GET", url)
    
    if response.status_code == 200: 
        print('Request succeeded') 
    else: 
        print(f'Request failed with status code: {response.status_code}')

    pprint(response.json())


def export_request(session, cameraId, start, stop, name=None):

    url = f"{base_url}/v1/export.web?camera={cameraId}&s={session}&start={start}&end={stop}&format=mp4"
    if name:
        url = url+f'&name={name}'

    response = requests.request("GET", url)
    export_id = json.loads(response.text)['export_id']
    pprint(response.json())

    return export_id


def export_status(export_id):

    url = f"{base_url}/v1/export.web?export={export_id}"

    response = requests.request("GET", url)
    progress = json.loads(response.text)['progress']
    pprint(response.json())

    return progress


def export_download(export_id):

    url = f"{base_url}/v1/export.web?export={export_id}&action=download"

    response = requests.request("GET", url)

    file_name = response.headers.get('Content-Disposition').split('filename=')[-1].strip('"')

    with open(file_name, 'wb') as file:
        file.write(response.content)

    print(f"Video saved successfully as {file_name}!")

    print(response.text)


def export_delete(export_id):

    url = f"{base_url}/v1/export.web?export={export_id}&action=download"

    response = requests.request("GET", url)
    
    print(response.text)


def extract_video():
    pass