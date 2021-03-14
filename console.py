import subprocess
import npyscreen
import proxy
import time
from threading import Thread

class ManagementConsole(npyscreen.NPSAppManaged):
    def onStart(self):
        self.MainForm = self.addForm("MAIN", MainForm, name="Python proxy management console")
        self.proxyThread = Thread(target=proxy.main, args=(self.MainForm, ))
        self.proxyThread.setDaemon(True)
        self.proxyThread.start()

class MainForm(npyscreen.ActionForm):
    def create(self):
        self.blacklist = self.add(npyscreen.TitleText, name="Blacklist: ", value="")
        self.blacklist.when_value_edited = self.updateBlacklist
        self.add(npyscreen.TitleText, name="Use comma separated host names", editable=False)
        self.add(npyscreen.TitleText, name="Press <CTRL + C> to stop the proxy server", editable=False)
        self.add(npyscreen.TitleText, name="Sometimes high traffic breaks the UI, press <Enter> twice to fix it", editable=False)
        self.add(npyscreen.TitleText, name="Proxy output: ", editable=False)
        self.output = self.add(npyscreen.MultiLineEdit, name="Output", value="", editable=False)
        self.raw_output = ""

    def on_ok(self):
        raise KeyboardInterrupt

    def updateBlacklist(self):
        proxy.blacklist = self.blacklist.value.split(",")

    def updateOutput(self, newInfo):
        self.raw_output = newInfo + "\n" + self.raw_output

        self.output.value = "Total RX: {} B, Total TX: {} B, Average round-trip time: {:.0f} ms\n\n{}".format(proxy.totalRX, proxy.totalTX, proxy.avgTime * 1000, self.raw_output)
        self.output.display()

if __name__ == "__main__":
    App = ManagementConsole()
    App.run()