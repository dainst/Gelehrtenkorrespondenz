import json
import os

class ProjectCofiguration():
    """
    Initialize the configuration for a project by reading from a JSON file
    """
    def __init__(self, path_to_config):
        with open(path_to_config) as f:
            self._json = json.load(f)
        self.project_root = self._json["project_root"]
        self._username = self._json["user"]
        self._password = self._json["password"]

        self.webanno_project_id = self._json["webanno_project_id"]
        self.authentication = (self._username, self._password)

        self.preprocessing_regexp = os.path.join(self.project_root, self._json["preprocessing_regexp"])
        self.sentence_tokenizer = self._json["sentence_tokenizer"]
        self.template = self._json["feature_template"]

        ### Paths to models and tools
        self.model = os.path.join(self.project_root, self._json["model_path"])

        ### Paths to FILES
        # where the raw files to be annotated are found
        self.root_raw = os.path.join(self.project_root, self._json["root_raw"])
        # where the annotated training data are found
        self.root_training = os.path.join(self.project_root, self._json["root_training"])

    @property
    def dictionaries(self):
        d = {}
        for k,v in self._json["dictionaries"].items():
            d[k] = os.path.join(self.project_root, v)
        return d





