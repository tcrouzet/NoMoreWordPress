import datetime, sys

class DualOutput:
    def __init__(self, fichier):
        self.terminal = sys.stdout
        self.terminal_stderr = sys.stderr
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log = open(fichier, "a")
        self.log.write(f"\n\n----\n{now}\n") 

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def write_error(self, message):
        self.terminal_stderr.write(message)
        self.log.write(message)

    def flush(self):
        # Cette méthode flush est nécessaire pour l'interface de fichier.
        self.terminal.flush()
        self.log.flush()

    def close(self):
        if self.log:
            self.log.close()
            self.log = None

def timestamp_to_date(timestamp):
    date_time = datetime.datetime.fromtimestamp(timestamp)
    readable_date = date_time.strftime("%Y-%m-%d")
    return readable_date
