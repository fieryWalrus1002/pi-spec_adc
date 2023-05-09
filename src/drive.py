from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import glob


class DataUploader:
    def __init__(
        self, creds: str = None, parent_id: str = "1lIcJANSyJTZjpD25KN4Qt9w9geGL-oLF"
    ):
        self.parent_id = parent_id

        if creds == None:
            self.creds = glob.glob(f"../**/mycreds.json")[0]

        self.gauth = GoogleAuth()

    def upload(
        self,
        file_path: str = "washer.txt",
        folder_name: str = "",
    ):
        drive = GoogleDrive(self.gauth)

        if self.folder_exists(folder_name) == False and folder_name != "":
            self.create_folder(folder_name)

        dest_id = self.get_dest_id(folder_name)

        upfile = drive.CreateFile({"parents": [{"id": dest_id}]})
        upfile.SetContentFile(file_path)
        upfile.Upload()

    def get_dest_id(self, folder_name: str):
        if folder_name == "":
            return self.parent_id
        else:
            return self.get_folder_id(folder_name)

    def folder_exists(self, folder_name: str):
        if self.get_folder_id(folder_name) == "":
            return False
        else:
            return True

    def create_folder(
        self,
        folder_name: str,
    ):
        drive = GoogleDrive(self.gauth)

        folder = drive.CreateFile(
            {
                "title": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [{"id": self.parent_id}],
            }
        )
        folder.Upload()

        dest_id = self.get_folder_id(folder_name)

        return dest_id

    def get_folder_id(self, folder_name):
        drive = GoogleDrive(self.gauth)
        file_list = drive.ListFile().GetList()
        folder_id = ""

        for file in file_list:

            if (
                file["mimeType"] == "application/vnd.google-apps.folder"
                and file["title"] == folder_name
            ):

                folder_id = file["id"]

        return folder_id
