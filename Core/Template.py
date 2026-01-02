import yaml

class Template():
    Name = ""
    Tags = []
    Codec = ""
    Parameters = {}

    def __init__(self, name, tags, codec):
        self.Name = name
        self.Tags = tags
        self.Codec = codec

    def from_yaml(self, filename):
        with open(filename) as f:
            tpl = yaml.safe_load(f)

        self.Name = tpl['Name']
        self.Tags = tpl['Tags']
        self.Codec = tpl['Codec']
        self.Parameters = tpl['Parameters']