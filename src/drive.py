from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


class DataUploader:
    def __init__(self):
        self.gauth = GoogleAuth()
        self.gauth.LoadCredentialsFile("mycreds.txt")
        if self.gauth.credentials is None:
            self.gauth.LocalWebserverAuth()
        elif self.gauth.access_token_expired:
            self.gauth.Refresh()
        else:
            self.gauth.Authorize()
        self.gauth.SaveCredentialsFile("mycreds.txt")

    def upload(self, file):
        drive = GoogleDrive()
        upfile = drive.CreateFile({"parents": [{"id": "1DEDCwzhbn3TAJ8n12x2DjyZGoQI3375j"}]})
        upfile = drive.CreateFile()
        upfile.SetContentFile(file)
        upfile.Upload()
        