#! /usr/bin/env python
#
# example2_mpl.py -- Simple, configurable FITS viewer using a matplotlib
#                      QtAgg backend for Ginga and embedded in a Qt program.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
Usage:
   example2_mpl.py [fits file]

You need Qt5 or Qt6 with pyqt bindings (or pyside) installed to run this
example.
"""
import sys

from ginga import toolkit
toolkit.use('qt')

from matplotlib.figure import Figure

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp
from ginga.mplw.ImageViewMpl import CanvasView
from ginga.mplw.FigureCanvasQt import FigureCanvas
from ginga.misc import log
from ginga import colors
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.util.loader import load_data


class FitsViewer(QtGui.QMainWindow):

    def __init__(self, logger):
        super(FitsViewer, self).__init__()
        self.logger = logger
        self.drawcolors = colors.get_colors()
        self.dc = get_canvas_types()

        fig = Figure()
        w = FigureCanvas(fig)

        fi = CanvasView(logger=logger)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.set_callback('drag-drop', self.drop_file_cb)
        fi.set_callback('cursor-changed', self.cursor_cb)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.show_mode_indicator(True, corner='ur')
        fi.ui_set_active(True)
        fi.show_mode_indicator(True, corner='ur')
        self.fitsimage = fi
        fi.set_figure(fig)

        bd = fi.get_bindings()
        bd.enable_all(True)

        # canvas that we will draw on
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('rectangle', color='lightblue')
        canvas.set_surface(fi)
        self.canvas = canvas
        # add canvas to view
        fi.get_canvas().add(canvas)
        canvas.ui_set_active(True)
        canvas.register_for_cursor_drawing(fi)
        canvas.add_callback('draw-event', self.draw_cb)

        # add little mode indicator that shows keyboard modal states
        fi.show_mode_indicator(True, corner='ur')

        w.resize(512, 512)

        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(QtCore.QMargins(2, 2, 2, 2))
        vbox.setSpacing(1)
        vbox.addWidget(w, stretch=1)

        self.readout = QtGui.QLabel("")
        vbox.addWidget(self.readout, stretch=0,
                       alignment=QtCore.Qt.AlignCenter)

        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(QtCore.QMargins(4, 2, 4, 2))

        wdrawtype = QtGui.QComboBox()
        self.drawtypes = self.canvas.get_drawtypes()
        for name in self.drawtypes:
            wdrawtype.addItem(name)
        index = self.drawtypes.index('rectangle')
        wdrawtype.setCurrentIndex(index)
        wdrawtype.activated.connect(self.set_drawparams)
        self.wdrawtype = wdrawtype

        wdrawcolor = QtGui.QComboBox()
        for name in self.drawcolors:
            wdrawcolor.addItem(name)
        index = self.drawcolors.index('lightblue')
        wdrawcolor.setCurrentIndex(index)
        wdrawcolor.activated.connect(self.set_drawparams)
        self.wdrawcolor = wdrawcolor

        wfill = QtGui.QCheckBox("Fill")
        wfill.stateChanged.connect(self.set_drawparams)
        self.wfill = wfill

        walpha = QtGui.QDoubleSpinBox()
        walpha.setRange(0.0, 1.0)
        walpha.setSingleStep(0.1)
        walpha.setValue(1.0)
        walpha.valueChanged.connect(self.set_drawparams)
        self.walpha = walpha

        wclear = QtGui.QPushButton("Clear Canvas")
        wclear.clicked.connect(self.clear_canvas)
        wopen = QtGui.QPushButton("Open File")
        wopen.clicked.connect(self.open_file)
        wquit = QtGui.QPushButton("Quit")
        wquit.clicked.connect(self.close)

        hbox.addStretch(1)
        for w in (wopen, wdrawtype, wdrawcolor, wfill,
                  QtGui.QLabel('Alpha:'), walpha, wclear, wquit):
            hbox.addWidget(w, stretch=0)

        hw = QtGui.QWidget()
        hw.setLayout(hbox)
        vbox.addWidget(hw, stretch=0)

        mode = self.canvas.get_draw_mode()
        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(QtCore.QMargins(4, 2, 4, 2))

        btn1 = QtGui.QRadioButton("Draw")
        btn1.setChecked(mode == 'draw')
        btn1.toggled.connect(lambda val: self.set_mode_cb('draw', val))
        btn1.setToolTip("Choose this to draw on the canvas")
        hbox.addWidget(btn1)

        btn2 = QtGui.QRadioButton("Edit")
        btn2.setChecked(mode == 'edit')
        btn2.toggled.connect(lambda val: self.set_mode_cb('edit', val))
        btn2.setToolTip("Choose this to edit things on the canvas")
        hbox.addWidget(btn2)

        btn3 = QtGui.QRadioButton("Pick")
        btn3.setChecked(mode == 'pick')
        btn3.toggled.connect(lambda val: self.set_mode_cb('pick', val))
        btn3.setToolTip("Choose this to pick things on the canvas")
        hbox.addWidget(btn3)

        hbox.addWidget(QtGui.QLabel(''), stretch=1)
        hw = QtGui.QWidget()
        hw.setLayout(hbox)
        vbox.addWidget(hw, stretch=0)

        vw = QtGui.QWidget()
        self.setCentralWidget(vw)
        vw.setLayout(vbox)

    def set_drawparams(self, kind):
        index = self.wdrawtype.currentIndex()
        kind = self.drawtypes[index]
        index = self.wdrawcolor.currentIndex()
        fill = (self.wfill.checkState() != 0)
        alpha = self.walpha.value()

        params = {'color': self.drawcolors[index],
                  'alpha': alpha,
                  }
        if kind in ('circle', 'rectangle', 'polygon', 'triangle',
                    'righttriangle', 'ellipse', 'square', 'box'):
            params['fill'] = fill
            params['fillalpha'] = alpha

        self.canvas.set_drawtype(kind, **params)

    def clear_canvas(self):
        self.canvas.delete_all_objects()

    def load_file(self, filepath):
        image = load_data(filepath, logger=self.logger)
        self.fitsimage.set_image(image)
        self.setWindowTitle(filepath)

    def open_file(self):
        res = QtGui.QFileDialog.getOpenFileName(self, "Open FITS file",
                                                ".", "FITS files (*.fits)")
        if isinstance(res, tuple):
            fileName = res[0]
        else:
            fileName = str(res)
        if len(fileName) != 0:
            self.load_file(fileName)

    def drop_file_cb(self, viewer, paths):
        fileName = paths[0]
        self.load_file(fileName)

    def cursor_cb(self, viewer, button, data_x, data_y):
        """This gets called when the data position relative to the cursor
        changes.
        """
        # Get the value under the data coordinates
        try:
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = viewer.get_data(int(data_x + viewer.data_off),
                                    int(data_y + viewer.data_off))

        except Exception:
            value = None

        fits_x, fits_y = data_x + 1, data_y + 1

        # Calculate WCS RA
        try:
            # NOTE: image function operates on DATA space coords
            image = viewer.get_image()
            if image is None:
                # No image loaded
                return
            ra_txt, dec_txt = image.pixtoradec(fits_x, fits_y,
                                               format='str', coords='fits')
        except Exception as e:
            self.logger.warning("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.setText(text)

    def set_mode_cb(self, mode, tf):
        self.logger.info("canvas mode changed (%s) %s" % (mode, tf))
        if not (tf is False):
            self.canvas.set_draw_mode(mode)
        return True

    def draw_cb(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        obj.add_callback('pick-down', self.pick_cb, 'down')
        obj.add_callback('pick-up', self.pick_cb, 'up')
        obj.add_callback('pick-move', self.pick_cb, 'move')
        obj.add_callback('pick-hover', self.pick_cb, 'hover')
        obj.add_callback('pick-enter', self.pick_cb, 'enter')
        obj.add_callback('pick-leave', self.pick_cb, 'leave')
        obj.add_callback('pick-key', self.pick_cb, 'key')
        obj.pickable = True
        obj.add_callback('edited', self.edit_cb)

    def pick_cb(self, obj, canvas, event, pt, ptype):
        self.logger.info("pick event '%s' with obj %s at (%.2f, %.2f)" % (
            ptype, obj.kind, pt[0], pt[1]))
        return True

    def edit_cb(self, obj):
        self.logger.info("object %s has been edited" % (obj.kind))
        return True


def main(options, args):

    if QtHelp.have_pyqt6 or QtHelp.have_pyside6:
        QtGui.QApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCore.Qt.HighDpiScaleFactorRoundingPolicy.Floor)
    app = QtGui.QApplication(args)

    logger = log.get_logger(name="example2", options=options)
    w = FitsViewer(logger)
    w.resize(524, 540)
    w.show()
    app.setActiveWindow(w)
    w.raise_()
    w.activateWindow()

    if len(args) > 0:
        w.load_file(args[0])

    app.exec_()


if __name__ == "__main__":

    # Parse command line options
    from argparse import ArgumentParser

    argprs = ArgumentParser()

    argprs.add_argument("--debug", dest="debug", default=False,
                        action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("--profile", dest="profile", action="store_true",
                        default=False,
                        help="Run the profiler on main()")
    log.addlogopts(argprs)

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print(("%s profile:" % sys.argv[0]))
        profile.run('main(options, args)')

    else:
        main(options, args)

# END
