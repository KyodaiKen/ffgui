import yaml

class Codec():
    Name = ""
    DisplayName = ""
    Tags = []
    Executable = ""
    SourceFormats = []
    DestinationFormats = []
    Languages = {}
    Parameters = {}

    def from_yaml(self, filename):
        with open(filename) as f:
            codec = yaml.safe_load(f)

        self.Name = codec['Name']
        self.DisplayName = codec['DisplayName']
        self.Tags = codec['Tags']
        self.Executable = codec['Executable']
        self.SourceFormats = codec['SourceFormats']
        self.DestinationFormats = codec['DestinationFormats']
        self.Languages = codec['Languages']
        self.Parameters = codec['Parameters']
