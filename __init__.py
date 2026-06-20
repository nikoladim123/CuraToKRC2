from .KRLWriter import KRLWriter
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin

class KRLWriterPlugin(OutputDevicePlugin):
    def start(self):
        self.getOutputDeviceManager().addOutputDevice(KRLWriter())

    def stop(self):
        self.getOutputDeviceManager().removeOutputDevice("krl_writer")

def getMetaData():
    return {}

def register(metadata=None):
    return {"output_device": KRLWriterPlugin()}
