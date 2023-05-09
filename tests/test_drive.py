import unittest
from src.drive import DataUploader
from random import randint

print("what")


class TestDataUploader(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.folder_name = "random_school_laser"
        cls.file_path = "./battletech.txt"

    def test_folder_exists_false(self):
        uploader = DataUploader()
        self.assertFalse(uploader.folder_exists(f"pongoweaboo{randint(0, 99)}"))

    def test_create_folder(self):
        uploader = DataUploader()
        uploader.create_folder(self.folder_name)
        exists = uploader.folder_exists(self.folder_name)
        uploader.delete(self.folder_name)
        self.assertTrue(exists)

    def test_folder_exists_true(self):
        uploader = DataUploader()
        self.assertTrue(uploader.folder_exists(self.folder_name))

    def test_delete(self):
        uploader = DataUploader()
        uploader.create_folder(self.folder_name)
        uploader.delete_file(self.folder_name)
        self.assertFalse(uploader.folder_exists(self.folder_name))
