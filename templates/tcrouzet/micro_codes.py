# templates/<template>/micro_codes.py

class MicroCodes:
    def __init__(self, layout=None):
        self.layout = layout  # accès à config, template_dir, etc.

    def hello(self, name="monde"):
        return f"<strong>Bonjour {name} !</strong>"
