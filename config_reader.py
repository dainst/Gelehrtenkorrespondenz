import json


class ProjectCofiguration():
    """
    Initialize the configuration for a project by reading from a JSON file
    """
    def __init__(self, path_to_config):
        with open(path_to_config) as f:
            self._json = json.load(f)
        self._username = self._json["user"]
        self._password = self._json["password"]
        self.webanno_project_id = self._json["webanno_project_id"]
        self.authentication = (self._username, self._password)
        self.model = self._json["model_path"]
        self.preprocessing_regexp = self._json["preprocessing_regexp"]
        self.sentence_tokenizer = self._json["sentence_tokenizer"]
        self.dictionaries = self._json["dictionaries"]
        self.template = self._json["feature_template"]

        ### Paths to FILES
        # where the raw files to be annotated are found
        self.root_raw = self._json["root_raw"]
        # where the annotated training data are found
        self.root_training = self._json["root_training"]

