import json
import glob
from typing import Iterator


class Config:
    def __init__(self, cfg_filename):
        self.cfg = self.load(cfg_filename)

    def load(self, cfg_filename):
        with open(glob.glob(f"../*/{cfg_filename}")[0]) as config_file:
            raw_data = config_file.read()

        json_data = json.loads(raw_data)
        json_dict = {i: j for i, j in json_data}
        print(json_dict)

        # what = {{i: j for i, j in a} for a in json_data}
        # print(what)

    # @property
    # def nm_dict(self):
    #     return self._json["nm_dict"]

    # def __iter__(self):
    #     return iter([i for i in self._json])


if __name__ == "__main__":

    cfg = Config("config.json")

    # print(cfg.cfg)
