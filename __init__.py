#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demonstrates the appearance / interactivity of GradientWidget
(without actually doing anything useful with it)

"""
#import initExample ## Add path to library (just for examples; you do not need this)

import os
import itertools
import struct
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np

class speed_box(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QVBoxLayout(self)
        textbox = QtGui.QLabel(self)
        textbox.setText('Length (s)')
        self.spinbox = QtGui.QSpinBox(self)
        layout.addWidget(textbox)
        layout.addWidget(self.spinbox)
        self.setLayout(layout)

    def value(self):
        return self.spinbox.value()

    def setValue(self, val):
        self.spinbox.setValue(val)

def qcolor_to_rgb_raw(pos, color):
    return struct.pack('dBBB', pos, color.red(), color.green(), color.blue())

#We still need to get the speed
class led_editor(QtGui.QWidget):
    def __init__(self, parent=None, name=""):
        QtGui.QWidget.__init__(self, parent)
        self.speed_textbox = speed_box(self)
        groupbox = QtGui.QGroupBox(self)
        grid = QtGui.QVBoxLayout(self)
        self.gradient = pg.GradientWidget(orientation='left')
        self.gradient.setColorMode('rgb')
        grid.addWidget(self.gradient)
        grid.addWidget(self.speed_textbox)
        groupbox.setLayout(grid)
        groupbox.setTitle(name)
        outergrid = QtGui.QStackedLayout(self)
        outergrid.addWidget(groupbox)
        self.setLayout(outergrid)

    def nodes_raw_header(self):
        #Speed and number of keypoints
        return struct.pack('LL', self.speed_textbox.value(),len(self.gradient.listTicks()))

    def export_raw_gradient(self):
        #Keypoints
        return b''.join([qcolor_to_rgb_raw(self.gradient.tickValue(i[0]), i[0].color) for i in self.gradient.listTicks()])

    def load_raw_ticks(self, ticks):
        self.gradient.setColorMode('rgb')
        for existing_tick, loaded_tick in itertools.zip_longest(self.gradient.listTicks(), ticks):
            if loaded_tick == None:
                self.gradient.removeTick(existing_tick[0])
            elif existing_tick == None:
                color = QtGui.QColor()
                color.setRgb(loaded_tick[1], loaded_tick[2], loaded_tick[3])
                self.gradient.addTick(loaded_tick[0], color)
            else:
                color = QtGui.QColor()
                color.setRgb(loaded_tick[1], loaded_tick[2], loaded_tick[3])

                self.gradient.setTickValue(existing_tick[0], loaded_tick[0])
                self.gradient.setTickColor(existing_tick[0], color)
        self.gradient.updateGradient()

    def setSpeed(self, value):
        self.speed_textbox.setValue(value)

class save_button(QtGui.QPushButton):
    def __init__(self, parent=None, led_editors=()):
        QtGui.QWidget.__init__(self, parent)
        self.setText("Save")
        self.led_editors = led_editors

    def mousePressEvent(self, event):
        filename = QtGui.QFileDialog.getSaveFileName(self, "Save Blend", "/var/lib/b76/config.b76", "Blend76 Files (*.b76)")[0]
        if filename != "":
            with open(filename, 'wb') as f:
                #Number of LEDs
                f.write(struct.pack('B',len(self.led_editors)))
                #Headers (speed and number of keypoints)
                f.write(b''.join([i.nodes_raw_header() for i in self.led_editors]))
                #Keypoints
                f.write(b''.join([i.export_raw_gradient() for i in self.led_editors]))

class load_button(QtGui.QPushButton):
    def __init__(self, parent=None, led_editors=()):
        QtGui.QWidget.__init__(self, parent)
        self.setText("Load")
        self.led_editors = led_editors

    def mousePressEvent(self, event):
        filename = QtGui.QFileDialog.getOpenFileName(self, "Save Blend", "/var/lib/b76/config.b76", "Blend76 Files (*.b76)")[0]
        if filename != "":
            with open(filename, 'rb') as f:
                #Number of LEDs
                number_of_leds = struct.unpack('B', f.read(1))[0]
                #[Length, keypoints]
                headers = [struct.unpack('LL',f.read(16)) for i in range(number_of_leds)]
                #Go through and do .addTick for the widgets
                for header, led_editor in zip(headers, self.led_editors):
                    length, keypoint_count = header
                    led_editor.setSpeed(int(length))
                    led_editor.load_raw_ticks([struct.unpack('dBBB', f.read(11)) for i in range(keypoint_count)])



class editor_holder(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QGridLayout()
        led_editors = (led_editor(None, "Left"), led_editor(None, "Centre"), led_editor(None, "Right"))

        for i,j in enumerate(led_editors):
            layout.addWidget(j, 0, i)

        layout.addWidget(save_button(None, led_editors), 1, 0)
        layout.addWidget(load_button(None, led_editors), 1, 1)
        self.setLayout(layout)

app = QtGui.QApplication([])
w = QtGui.QMainWindow()
w.show()
w.setWindowTitle('Oryx Pro Backlight Editor')
w.setGeometry(10, 50, 480, 480)
w.setCentralWidget(editor_holder())
## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    try:
        os.mkdir("/var/lib/b76")
    except FileExistsError:
        pass

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
