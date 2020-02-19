#!/usr/bin/env python3
import locale
import sys
import threading
import traceback

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from include import HydrusConstants as HC
from include import HydrusData
from include import HydrusGlobals as HG
from include import QtPorting as QP
from include import TestController
from twisted.internet import reactor

try:
    locale.setlocale(locale.LC_ALL, '')
except:
    pass

if __name__ == '__main__':

    args = sys.argv[1:]

    if len(args) > 0:

        only_run = args[0]

    else:

        only_run = None

    try:

        threading.Thread(target=reactor.run,
                         kwargs={
                             'installSignalHandlers': 0
                         }).start()

        QP.MonkeyPatchMissingMethods()
        app = QW.QApplication(sys.argv)

        app.call_after_catcher = QC.QObject(app)

        app.call_after_catcher.installEventFilter(
            QP.CallAfterEventFilter(app.call_after_catcher))

        try:

            # we run the tests on the Qt thread atm
            # keep a window alive the whole time so the app doesn't finish its mainloop

            win = QW.QWidget(None)
            win.setWindowTitle('Running tests...')

            controller = TestController.Controller(win, only_run)

            def do_it():

                controller.Run(win)

            QP.CallAfter(do_it)

            app.exec_()

        except:

            HydrusData.DebugPrint(traceback.format_exc())

        finally:

            HG.view_shutdown = True

            controller.pubimmediate('wake_daemons')

            HG.model_shutdown = True

            controller.pubimmediate('wake_daemons')

            controller.TidyUp()

    except:

        HydrusData.DebugPrint(traceback.format_exc())

    finally:

        reactor.callFromThread(reactor.stop)

        print('This was version ' + str(HC.SOFTWARE_VERSION))

        input()
