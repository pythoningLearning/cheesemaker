# -*- coding: utf-8 -*-

# Authors: David Whitlock <alovedalongthe@gmail.com>
# A simple image viewer
# Copyright (C) 2013 David Whitlock
#
# Cheesemaker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cheesemaker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cheesemaker.  If not, see <http://www.gnu.org/licenses/gpl.html>.

from PyQt4 import QtCore, QtGui
from gi.repository import GExiv2
import os
import sys
import dbus
#import random
from . import preferences
#from . import preferences, editimage

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.printer = QtGui.QPrinter()
        self.create_actions()
        self.create_menu()
        self.create_dict()
        self.load_img = self.load_img_fit
        self.auto_orientation = True
        self.delay = 5

        self.scene = QtGui.QGraphicsScene()
        self.img_view = ImageView(self)
        self.img_view.setScene(self.scene)
        self.setCentralWidget(self.img_view)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)

        self.read_prefs()
        self.readable_list = ('bmp', 'gif', 'jpg', 'jpeg', 'mng', 'png', 'pbm',
                'pgm', 'ppm', 'tif', 'tiff', 'xbm', 'xpm', 'svg', 'tga')
        self.writeable_list = ('bmp', 'jpg', 'jpeg', 'png', 'ppm', 'tif', 'tiff', 'xbm', 'xpm')
        self.resize(700, 500)

    def create_actions(self):
        self.open_act = QtGui.QAction('&Open...', self, shortcut='Ctrl+O',
                triggered=self.open)
        self.print_act = QtGui.QAction('&Print...', self, shortcut='Ctrl+P',
                enabled=False, triggered=self.print_img)
        self.exit_act = QtGui.QAction('E&xit', self, shortcut='Ctrl+Q',
                triggered=self.close)
        self.fulls_act = QtGui.QAction('Fullscreen', self,
                shortcut='F11', checkable=True, triggered=self.toggle_fullscreen)
        self.ss_act = QtGui.QAction('Slideshow', self,
                shortcut='F5', checkable=True, triggered=self.toggle_slideshow)
        self.next_act = QtGui.QAction('Next image', self, shortcut='Right',
                triggered=self.go_next_img)
        self.prev_act = QtGui.QAction('Previous image', self, shortcut='Left',
                triggered=self.go_prev_img)
        self.rotleft_act = QtGui.QAction('Rotate left', self, shortcut='Ctrl+Left',
                triggered=self.img_rotate_left)
        self.rotright_act = QtGui.QAction('Rotate right', self, shortcut='Ctrl+Right',
                triggered=self.img_rotate_right)
        self.fliph_act = QtGui.QAction('Flip image horizontally', self, shortcut='Ctrl+H',
                triggered=self.img_fliph)
        self.flipv_act = QtGui.QAction('Flip image vertically', self, shortcut='Ctrl+V',
                triggered=self.img_flipv)
        self.zin_act = QtGui.QAction('Zoom &In', self,
                shortcut='Up', enabled=True, triggered=self.zoom_in)
        self.zout_act = QtGui.QAction('Zoom &Out', self,
                shortcut='Down', enabled=True, triggered=self.zoom_out)
        self.fit_win_act = QtGui.QAction('Best &fit', self,
                checkable=True, shortcut='F', triggered=self.zoom_default)
        self.fit_win_act.setChecked(True)
        self.prefs_act = QtGui.QAction('Preferences', self, triggered=self.set_prefs)
        self.help_act = QtGui.QAction('&Help', self, shortcut='F1', triggered=self.help_page)
        self.about_act = QtGui.QAction('&About', self, triggered=self.about_cm)
        self.aboutQt_act = QtGui.QAction('About &Qt', self,
                triggered=QtGui.qApp.aboutQt)

    def create_menu(self):
        self.popup = QtGui.QMenu(self)
        action_list = [self.open_act, self.print_act, self.fulls_act, self.ss_act, self.next_act, self.prev_act,
                self.zin_act, self.zout_act, self.fit_win_act, self.rotleft_act, self.rotright_act,
                self.fliph_act, self.flipv_act, self.prefs_act, self.help_act, self.about_act, self.aboutQt_act, self.exit_act]
        for act in action_list:
            self.popup.addAction(act)
            self.addAction(act)

    def showMenu(self, pos):
        self.popup.popup(self.mapToGlobal(pos))
 
    def create_dict(self):
        self.orient_dict = {None: self.do_nothing,
                '1': self.do_nothing,
                '2': self.img_fliph,
                '3': self.img_rotate_ud,
                '4': self.img_flipv,
                '5': self.img_rotate_fliph,
                '6': self.img_rotate_right,
                '7': self.img_rotate_flipv,
                '8': self.img_rotate_left}

    def read_prefs(self):
        try:
            conf = preferences.Config()
            values = conf.read_config()
            self.auto_orientation = values[0]
            self.slide_delay = values[1]
            self.quality = values[2]
        except:
            self.auto_orientation = True
            self.slide_delay = 5
            self.quality = 90

    def set_prefs(self):
        dialog = preferences.PrefsDialog(self)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            self.auto_orientation = dialog.auto_orientation
            self.slide_delay = dialog.delay_spinb.value()
            self.quality = dialog.qual_spinb.value()
            conf = preferences.Config()
            conf.write_config(self.auto_orientation, self.slide_delay, self.quality)
        dialog.destroy()

    def open(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Open File',
                QtCore.QDir.currentPath())
        if filename:
            if filename.endswith(self.readable_list):
                self.open_img(filename)
            else:
                QtGui.QMessageBox.information(self, 'Error', 'Cannot load {}.'.format(filename))

    def open_img(self, filename):
        self.reload_img(filename)
        dirname = os.path.dirname(filename)
        self.set_img_list(dirname)
        self.img_index = self.filelist.index(filename)

    def set_img_list(self, dirname):
        filelist = os.listdir(dirname)
        self.filelist = [os.path.join(dirname, filename) for filename in filelist
                        if filename.lower().endswith(self.readable_list)]
        self.filelist.sort()
        self.last_file = len(self.filelist) - 1

    def reload_img(self, filename):
        self.scene.clear()
        image = QtGui.QImage(filename)
        self.pixmap = QtGui.QPixmap.fromImage(image)
        self.load_img()
        if self.auto_orientation:
            try:
                orient = GExiv2.Metadata(filename)['Exif.Image.Orientation']
                self.orient_dict[orient]()
            except:
                pass

    def load_img_fit(self):
        self.scene.addPixmap(self.pixmap)
        self.scene.setSceneRect(0, 0, self.pixmap.width(), self.pixmap.height())
        self.img_view.fitInView(self.scene.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def load_img_1to1(self):
        self.img_view.resetMatrix()
        self.scene.addPixmap(self.pixmap)
        pixitem = QtGui.QGraphicsPixmapItem(self.pixmap)
        self.img_view.centerOn(pixitem)

    def go_next_img(self):
        self.img_index = self.img_index + 1 if self.img_index < self.last_file else 0
        filename = self.filelist[self.img_index]
        self.reload_img(filename)

    def go_prev_img(self):
        self.img_index = self.img_index - 1 if self.img_index else self.last_file
        filename = self.filelist[self.img_index]
        self.reload_img(filename)

    def zoom_default(self):
        if self.fit_win_act.isChecked():
            self.load_img = self.load_img_fit
            self.load_img()
        else:
            self.load_img = self.load_img_1to1
            self.load_img()

    def zoom_in(self):
        self.img_view.zoom(1.1)

    def zoom_out(self):
        self.img_view.zoom(1 / 1.1)

    def img_rotate_left(self):
        self.scene.clear()
        self.pixmap = self.pixmap.transformed(QtGui.QTransform().rotate(270))
        self.load_img()

    def img_rotate_right(self):
        self.scene.clear()
        self.pixmap = self.pixmap.transformed(QtGui.QTransform().rotate(90))
        self.load_img()

    def img_fliph(self):
        self.scene.clear()
        self.pixmap = self.pixmap.transformed(QtGui.QTransform().scale(-1, 1))
        self.load_img()

    def img_flipv(self):
        self.scene.clear()
        self.pixmap = self.pixmap.transformed(QtGui.QTransform().scale(1, -1))
        self.load_img()

    def img_rotate_ud(self, button):
        self.scene.clear()
        self.pixmap = self.pixmap.transformed(QtGui.QTransform().rotate(180))
        self.load_img()

    def img_rotate_fliph(self):
        self.img_rotate_right()
        self.img_fliph()

    def img_rotate_flipv(self):
        self.img_rotate_right()
        self.img_flipv()

    def toggle_fullscreen(self):
        if self.fulls_act.isChecked():
            self.showFullScreen()
        else:
            self.showNormal()

    def toggle_slideshow(self):
        if self.ss_act.isChecked():
            self.showFullScreen()
            self.start_ss()
        else:
            self.toggle_fullscreen()
            self.timer.stop()
            self.ss_timer.stop()

    def start_ss(self):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_img)
        self.timer.start(self.delay * 1000)
        self.ss_timer = QtCore.QTimer()
        self.ss_timer.timeout.connect(self.update_img)
        self.ss_timer.start(60000)

    def update_img(self):
        self.go_next_img()

    def inhibit_screensaver(self):
        bus = dbus.SessionBus()
        ss = bus.get_object('org.freedesktop.ScreenSaver','/ScreenSaver')
        self.inhibit_method = ss.get_dbus_method('SimulateUserActivity','org.freedesktop.ScreenSaver')

    def save_img(self):
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Save your image',
                QtCore.QDir.currentPath())
        if filename:
            if not filename.endswith(self.writeable_list):
                QtGui.QMessageBox.information(self, 'Error', 'Cannot save {}.'.format(filename))
                return
            print(filename)

    def print_img(self):
        dialog = QtGui.QPrintDialog(self.printer, self)
        if dialog.exec_():
            painter = QtGui.QPainter(self.printer)
            rect = painter.viewport()
            size = self.pixmap().size()
            size.scale(rect.size(), QtCore.Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(self.pixmap().rect())
            painter.drawPixmap(0, 0, self.pixmap())

    def resizeEvent(self, event=None):
        if self.fit_win_act.isChecked():
            try:
                self.load_img()
            except:
                pass

    def help_page(self):
        preferences.HelpDialog(self)

    def about_cm(self):
        about_message = 'Version: 0.3.0\nAuthor: David Whitlock\nLicense: GPLv3'
        QtGui.QMessageBox.about(self, 'About Cheesemaker', about_message)

    def do_nothing(self):
        return

class ImageView(QtGui.QGraphicsView):
    def __init__(self, parent=None):
        QtGui.QGraphicsView.__init__(self, parent)

        self.load_img = parent.load_img
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QtCore.Qt.black)
        self.setPalette(pal)
        self.setFrameShape(QtGui.QFrame.NoFrame)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
        QtGui.QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.setDragMode(QtGui.QGraphicsView.NoDrag)
        QtGui.QGraphicsView.mouseReleaseEvent(self, event)

    def zoom(self, zoomratio):
        self.scale(zoomratio, zoomratio)

    def wheelEvent(self,  event):
        zoomratio = 1.1
        if event.delta() < 0:
            zoomratio = 1.0 / zoomratio
        self.scale(zoomratio, zoomratio)

def main():
    app = QtGui.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    args = sys.argv[1:]
    filename = args[0] if args else None
    if filename and filename.endswith(win.readable_list):
        win.open_img(filename)
    app.exec_()
