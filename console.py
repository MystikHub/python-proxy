import subprocess
import npyscreen
import proxy
import time
from threading import Thread

# npyscreen app, loads the form and starts up the proxy server
class ManagementConsole(npyscreen.NPSAppManaged):
    def onStart(self):
        self.MainForm = self.addForm("MAIN", MainForm, name="Python proxy management console")
        self.proxyThread = Thread(target=proxy.main, args=(self.MainForm, ))
        # Making the proxy thread a daemon thread makes closing
        #   all the packet threads cleaner
        self.proxyThread.setDaemon(True)
        self.proxyThread.start()

class MainForm(npyscreen.ActionForm):
    def create(self):
        # Blacklist field
        self.blacklist = self.add(npyscreen.TitleText, name="Blacklist: ", value="")
        # Event handler for blacklist updates
        self.blacklist.when_value_edited = self.updateBlacklist

        # Instructions
        self.add(npyscreen.TitleText, name="Use comma separated host names", editable=False)
        self.add(npyscreen.TitleText, name="Press <CTRL + C> to stop the proxy server", editable=False)
        self.add(npyscreen.TitleText, name="Sometimes high traffic breaks the UI, press <Enter> twice to fix it", editable=False)
        self.add(npyscreen.TitleText, name="Proxy output: ", editable=False)

        # Output window
        self.output = self.add(npyscreen.MultiLineEdit, name="Output", value="", editable=False)
        # Property that represents proxy reports without the statistics
        self.raw_output = ""

    # Send a keyboard interrupt (^C) when the OK button is pressed
    def on_ok(self):
        raise KeyboardInterrupt

    # Update the global blacklist variable in the proxy file on each keypress
    def updateBlacklist(self):
        proxy.blacklist = self.blacklist.value.split(",")

    # Used in proxy.py. Prepends newInfo into the "Proxy output" window
    def updateOutput(self, newInfo):
        self.raw_output = newInfo + "\n" + self.raw_output

        self.output.value = "Total RX: {} B, Total TX: {} B, Average round-trip time: {:.0f} ms\n\n{}".format(proxy.totalRX, proxy.totalTX, proxy.avgTime * 1000, self.raw_output)
        # Update the output widget
        self.output.display()

# Start up the management console when this script runs
if __name__ == "__main__":
    App = ManagementConsole()
    App.run()