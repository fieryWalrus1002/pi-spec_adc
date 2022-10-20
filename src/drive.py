from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import glob


class DataUploader:
    def __init__(self, creds: str = None):
        if creds == None:
            creds = glob.glob(f"../**/mycreds.json")[0]
            print(creds)
        self.gauth = GoogleAuth()
        self.gauth.LoadCredentialsFile(creds)
        if self.gauth.credentials is None:
            self.gauth.LocalWebserverAuth()
            print("no gauth_credentials")
        elif self.gauth.access_token_expired:
            self.gauth.Refresh()
            print("refreshing credentials")
        else:
            self.gauth.Authorize()
            print("credentials authorized")
        self.gauth.SaveCredentialsFile("mycreds.json")
        print("creds saved to mycreds.json")

    def upload(
        self,
        file: str = "washer.txt",
        dest_id: str = "1lIcJANSyJTZjpD25KN4Qt9w9geGL-oLF",
    ):
        drive = GoogleDrive()
        upfile = drive.CreateFile({"parents": [{"id": dest_id}]})
        # upfile = drive.CreateFile()
        upfile.SetContentFile(file)
        upfile.Upload()


if __name__ == "__main__":

    uploader = DataUploader()

    filename = "washer.txt"
    uploader.upload(filename)
    print("done")
