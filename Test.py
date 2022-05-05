# Sample code for running a test with ACEstatPy
from time import sleep

from acestatpy import ACEstatPy, ParameterError

# PORT may need changed.
# Available ports can be listed with test.acestat.Serial.PORTS()
PORT = "COM6"

class Test(object):
    def __init__(self):
        self.test = None
        self.testComplete = False
        self.acestat = ACEstatPy()
        self.acestat.onTestStart(self.onStart)
        # self.acestat.onResult(self.onResult)
        self.acestat.onTestEnd(self.onEnd)
        self.acestat.onReady(self.onReady)
        self.acestat.onError(self.onError)
        self.acestat.Serial.onMessageSending(self.messageS)
        self.acestat.Serial.onDisconnected(self.onDisconnected)
        # self.acestat.Serial.onMessageReceived(self.messageR)

    def onStart(self, test):
        print("Starting:", test)
        self.test = test

    def onEnd(self, test):
        print("Ending:", test)
        test.export()

    def onError(self, e):
        print("Error:", e)

    def onResult(self, id):
        print("Result:", self.test.results[id])

    def onReady(self, isReady):
        if isReady:
            print("Ready")
        else:
            print("Not ready")

    def messageS(self, msg):
        print("\nSending:", msg)

    def messageR(self, msg):
        print("\nReceived:", msg.replace("\r\n", "\n"), end="")#.replace("\r\n", "    "))
        # print()
        pass

    def onDisconnected(self, err=None):
        print("Disconnected:", err)
        test.acestat.removeFromQueue(0)

if __name__ == "__main__":
    test = Test()
    # params = test.acestat.Definitions["CV"].presets["Example"].parameters
    # for t in test.acestat.Definitions:
    #     print(t)
    #     for p in test.acestat.Definitions[t].plots:
    #         print(f"\t{p}")
    # raise SystemExit

    test.acestat.connect(PORT, 115200)
    # test.acestat.togglePause(True)
    sampleTest = test.acestat.Definitions["CV"].presets["Example"].parameters
    # print(sampleTest)
    # sampleTest["TEI"] = "1"
    # sampleTest["SVI"] = "-50"
    # sampleTest["VVI"] = "50"
    # sampleTest["EVI"] = "-50"
    try:
        test.acestat.addToQueue("CV", sampleTest, iterations=1, export="example.csv")
        test.acestat.addToQueue("CV", sampleTest, iterations=1, export="./examples/")
    except ParameterError as e:
        print(e.id, e.message)
    # test.acestat.addToQueue("SWV", test.acestat.Definitions["SWV"].presets["Example"].parameters, iterations=1)
    # Needs time for board to start the test
    # sleep(2)
    # Should cancel remaining iterations, without cancelling the running test
    # test.acestat.removeFromQueue(0, force=False)

    # Wait for queue to complete
    while len(test.acestat.queue):
        sleep(1)

    test.acestat.disconnect()
