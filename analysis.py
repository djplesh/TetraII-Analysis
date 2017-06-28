# -*- coding: utf-8 -*-
"""
@author: Jonah Hoffman
"""

import sys
from os import startfile, getcwd, path
import threading
import multiprocessing as mp
from calendar import monthrange
from time import gmtime, strftime
import re

from PySide import QtGui, QtCore

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from plot_hists_gui3 import rates


def run_rates(pipe_c, ind, name, date, duration, threshold, path, error_pipe_c):
    """runs rates() in a format able to be subprocessed (see pickle library)"""
    try:
        data2m = []
        data20u = []
        info = []
        data2m, data20u, info, errors = rates(box_num=name, start_date=date, duration=duration, 
                                              threshold=threshold, path0=path)
        error_pipe_c.send(errors)
        pipe_c.send([data2m, data20u, info])
    except Exception as inst:
        error_pipe_c.send([inst])
        pipe_c.send(-1)


class RatesError(Exception):

    """Raised when exceptions are caught in run_rates()"""

    pass


class CanvasWidget(FigureCanvas):

    def __init__(self, fig):
        self.fig = fig
        super(CanvasWidget, self).__init__(self.fig)
        self.toolbar = NavigationToolbar(self, self)


    def clear(self):
        self.fig.clear()


class RatePlot(QtGui.QWidget):

    """A widget that processes and displays rate information for events in selected data"""

    def __init__(self):
        super(RatePlot, self).__init__()
        self.initUI()

    def initUI(self):
        #set variables
        self.path = 'C:/tetra2/array/'
        self.date = '2015_01_01'
        self.array = []
        self.errorlog = str(getcwd()) + '/info/errorlog.txt'
        self.config = str(getcwd()) + '/info/config.txt'
        self.get_config()
        self.duration = 1
        self.threshold = 30
        self.set_lists()
        self.threads = []
        self.processes = []
        self.todo = 0

        #create widgets
        #box Tree
        boxTree = QtGui.QTreeWidget(self)
        header = QtGui.QTreeWidgetItem(['Box Select', 'Events'])
        boxTree.setHeaderItem(header)
        boxTree.setFixedWidth(240)
        boxTree.itemClicked.connect(self.tree_clicked)
        boxTree.setColumnWidth(0, 160)
        boxTree.setColumnWidth(1, 60)

        brParent = QtGui.QTreeWidgetItem(boxTree)
        brParent.setText(0, 'LSU')
        for x in xrange(2):
            child = QtGui.QTreeWidgetItem(brParent, ['LSU_0{}'.format(x+1), '--'])
            child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
            child.setCheckState(0, QtCore.Qt.Unchecked)
            self.array.append(child)

        alParent = QtGui.QTreeWidgetItem(boxTree)
        alParent.setText(0, 'Hunstville')
        for x in xrange(2):
            child = QtGui.QTreeWidgetItem(alParent, ['UAH_0{}'.format(x+1), '--'])
            child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
            child.setCheckState(0, QtCore.Qt.Unchecked)
            self.array.append(child)

        prParent = QtGui.QTreeWidgetItem(boxTree)
        prParent.setText(0, 'Puerto Rico')
        for x in xrange(9):
            child = QtGui.QTreeWidgetItem(prParent, ['PR_0{}'.format(x+1), '--'])
            child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
            child.setCheckState(0, QtCore.Qt.Unchecked)
            self.array.append(child)
        child = QtGui.QTreeWidgetItem(prParent, ['PR_10', '--'])
        child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
        child.setCheckState(0, QtCore.Qt.Unchecked)
        self.array.append(child)

        paParent = QtGui.QTreeWidgetItem(boxTree)
        paParent.setText(0, 'Panama')
        for x in xrange(5):
            child = QtGui.QTreeWidgetItem(paParent, ['PA_0{}'.format(x+1), '--'])
            child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
            child.setCheckState(0, QtCore.Qt.Unchecked)
            self.array.append(child)

        #date widgets
        self.yearBox = QtGui.QSpinBox()
        self.yearBox.setRange(2015, 2017)
        self.yearBox.setValue(int(self.date[:4]))
        self.yearBox.setSingleStep(1)
        self.yearBox.valueChanged.connect(self.set_year)

        self.monthBox = QtGui.QSpinBox()
        self.monthBox.setRange(1, 12)
        self.monthBox.setValue(int(self.date[5:7]))
        self.monthBox.setSingleStep(1)
        self.monthBox.valueChanged.connect(self.set_month)

        self.dayBox = QtGui.QSpinBox()
        self.dayBox.setRange(1, 31)
        self.dayBox.setValue(int(self.date[8:10]))
        self.dayBox.setSingleStep(1)
        self.dayBox.valueChanged.connect(self.set_day)

        self.durationBox = QtGui.QSpinBox()
        self.durationBox.setRange(1, 1000)
        self.durationBox.setSingleStep(1)
        self.durationBox.valueChanged.connect(self.get_enddate)

        #threshold widgets
        self.threshLbl = QtGui.QLabel(str(self.threshold)+u' \u03C3', self)
        self.threshLbl.setAlignment(QtCore.Qt.AlignCenter)
        self.threshLbl.setMargin(2)
        self.threshLbl.setFixedHeight(20)
        self.threshLbl.setFixedWidth(40)

        self.threshSlider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.threshSlider.setMinimum(10)
        self.threshSlider.setMaximum(40)
        self.threshSlider.setValue(30)
        self.threshSlider.setTickPosition(QtGui.QSlider.TicksAbove)
        self.threshSlider.setTickInterval(10)
        self.threshSlider.valueChanged.connect(self.set_threshold)

        #Bin Widgets
        self.sBinBtn = QtGui.QRadioButton('2 ms', self)
        self.sBinBtn.toggled.connect(self.set_bins)

        self.lBinBtn = QtGui.QRadioButton('20 '+u'\u03BC'+'s', self)
        self.lBinBtn.toggled.connect(self.set_bins)

        #Graph Control Widgets
        graphBtn = QtGui.QPushButton('Graph', self)
        graphBtn.clicked.connect(self.graph)

        cancelBtn = QtGui.QPushButton('Cancel', self)
        cancelBtn.clicked.connect(self.cancel)

        prevBtn = QtGui.QPushButton('Previous', self)
        prevBtn.clicked.connect(self.prev_graph)

        nextBtn = QtGui.QPushButton('Next', self)
        nextBtn.clicked.connect(self.next_graph)

        self.pageLbl = QtGui.QLabel('0 of 0', self)
        self.pageLbl.setAlignment(QtCore.Qt.AlignCenter)

        #info widgets
        self.dateLbl = QtGui.QLabel('--', self)
        self.dateLbl.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.dateLbl.setAlignment(QtCore.Qt.AlignCenter)
        self.dateLbl.setMargin(2)
        self.dateLbl.setFixedHeight(20)
        self.dateLbl.setFixedWidth(80)

        self.aveCountLbl = QtGui.QLabel('--', self)
        self.aveCountLbl.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.aveCountLbl.setAlignment(QtCore.Qt.AlignCenter)
        self.aveCountLbl.setMargin(2)
        self.aveCountLbl.setFixedHeight(20)

        self.minCountLbl = QtGui.QLabel('--', self)
        self.minCountLbl.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.minCountLbl.setAlignment(QtCore.Qt.AlignCenter)
        self.minCountLbl.setMargin(2)
        self.minCountLbl.setFixedHeight(20)

        #top status bar
        statusLbl = QtGui.QLabel('status:', self)

        self.status = QtGui.QLabel('--', self)
        self.status.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.status.setAlignment(QtCore.Qt.AlignCenter)
        self.status.setMargin(2)
        self.status.setFixedHeight(20)
        self.status.setFixedWidth(160)
        
        #infoBox
        self.infoBox = QtGui.QListWidget(self)
        self.infoBox.setFixedWidth(240)
        self.infoBox.setFixedHeight(200)

        #setup graph
        self.fig = Figure(figsize=(800, 600),
                          dpi=72,
                          facecolor=(1, 1, 1),
                          edgecolor=(0, 0, 0))
        self.ax = self.fig.add_subplot(111)
        self.ax.plot([0, 1])
        self.canvas = CanvasWidget(self.fig)
        self.tabs = QtGui.QTabWidget()

        self.tabs.insertTab(0, self.canvas, 'Empty')
        #self.toolbar = NavigationToolbar(self.canvas, self)

        #setup layout
        dateGroup = QtGui.QGroupBox('Dates')
        dateLayout = QtGui.QGridLayout()
        dateLayout.addWidget(QtGui.QLabel('Year', self), 0, 0, 1, 1)
        dateLayout.addWidget(QtGui.QLabel('Month', self), 0, 1, 1, 1)
        dateLayout.addWidget(QtGui.QLabel('Day', self), 0, 2, 1, 1)
        dateLayout.addWidget(self.yearBox, 1, 0, 1, 1)
        dateLayout.addWidget(self.monthBox, 1, 1, 1, 1)
        dateLayout.addWidget(self.dayBox, 1, 2, 1, 1)
        dateLayout.addWidget(QtGui.QLabel('Duration:', self), 2, 1, 1, 1)
        dateLayout.addWidget(self.durationBox, 2, 2, 1, 1)
        dateGroup.setLayout(dateLayout)

        threshGroup = QtGui.QGroupBox('Threshold')
        threshLayout = QtGui.QGridLayout()
        threshLayout.addWidget(self.threshLbl, 0, 0, 1, 1)
        threshLayout.addWidget(self.threshSlider, 0, 1, 1, 2)
        threshGroup.setLayout(threshLayout)

        binGroup = QtGui.QGroupBox('Bin Size')
        binLayout = QtGui.QGridLayout()
        binLayout.addWidget(self.sBinBtn, 0, 0, 1, 1)
        binLayout.addWidget(self.lBinBtn, 0, 1, 1, 1)
        binGroup.setLayout(binLayout)

        graphGroup = QtGui.QGroupBox('Graph')
        graphLayout = QtGui.QGridLayout()
        graphLayout.addWidget(graphBtn, 0, 0, 1, 2)
        graphLayout.addWidget(cancelBtn, 0, 2, 1, 1)
        graphLayout.addWidget(prevBtn, 2, 0, 1, 1)
        graphLayout.addWidget(nextBtn, 2, 1, 1, 1)
        graphLayout.addWidget(self.pageLbl, 2, 2, 1, 1)
        graphGroup.setLayout(graphLayout)
        
        infoGroup = QtGui.QGroupBox('Info')
        infoLayout = QtGui.QGridLayout()
        infoLayout.addWidget(QtGui.QLabel('Date:', self), 0, 0, 1, 1)
        infoLayout.addWidget(self.dateLbl, 0, 1, 1, 1)
        infoLayout.addWidget(QtGui.QLabel('Ave Rate:', self), 1, 0, 1, 1)
        infoLayout.addWidget(self.aveCountLbl, 1, 1, 1, 1)
        infoLayout.addWidget(QtGui.QLabel('Min Rate:', self), 2, 0, 1, 1)
        infoLayout.addWidget(self.minCountLbl, 2, 1, 1, 1)
        infoGroup.setLayout(infoLayout)
        
        statusLayout = QtGui.QHBoxLayout()
        statusLayout.addWidget(statusLbl)
        statusLayout.addWidget(self.status)
        statusLayout.setAlignment(QtCore.Qt.AlignLeft)
        
        boxLayout = QtGui.QVBoxLayout()
        boxLayout.addLayout(statusLayout)
        boxLayout.addWidget(boxTree)
        boxLayout.addWidget(QtGui.QLabel('Run Messages', self))
        boxLayout.addWidget(self.infoBox)
        
        graphLayout = QtGui.QVBoxLayout()
        graphLayout.addWidget(self.tabs)
        #graphLayout.addWidget(self.toolbar)
        
        topLayout = QtGui.QHBoxLayout()
        topLayout.addLayout(boxLayout)
        topLayout.addLayout(graphLayout)
        
        bottomLayout = QtGui.QGridLayout()
        bottomLayout.addWidget(dateGroup, 0, 1, 2, 1)
        bottomLayout.addWidget(threshGroup, 0, 0, 1, 1)
        bottomLayout.addWidget(binGroup, 1, 0, 1, 1)
        bottomLayout.addWidget(graphGroup, 0, 4, 2, 1)
        bottomLayout.addWidget(infoGroup, 0, 3, 2, 1)
        bottomLayout.setAlignment(QtCore.Qt.AlignTop)
        
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addLayout(topLayout)
        mainLayout.addLayout(bottomLayout)
        self.setLayout(mainLayout)
        
        #final setup
        self.ndx = self.tabs.currentIndex
        self.sBinBtn.setChecked(True)
        self.tabs.currentChanged.connect(self.changed_tabs)
        
    def graph(self):
        #block if currently graphing
        for thread in self.threads:
            if thread.isAlive():
                return
        #re/initialize varables
        self.status.setText('--')
        self.infoBox.clear()
        for i in range(19):
            self.array[i].setText(1, '--')
        self.threads = []
        self.processes = []
        self.tabs.clear()
        self.set_lists()
        #create a thread for each selected box
        for ind, box in zip(range(19), [x for x in self.array if x.checkState(0) != QtCore.Qt.CheckState.Unchecked]):
            fig = Figure(figsize=(800, 600), dpi=72, 
                         facecolor=(1, 1, 1), edgecolor=(0, 0, 0))
            self.tabs.insertTab(ind, CanvasWidget(fig), box.text(0))
            try:
                thread = threading.Thread(target=self._rate_plot, args=(ind, str(box.text(0))))
                self.threads.append(thread)
                thread.daemon = True
                thread.start()
                if ind == 0:
                    self.status.setText('Graphing...') #set status
            except Exception as inst:
                self.log_error(inst, message='could not create thread')
            self.todo += 1
            ind += 1
        #if no boxes selected, revert to default tab
        if self.tabs.count() == 0:
            self.tabs.addTab(self.canvas, 'Empty')
        
    def _rate_plot(self, ind, name):
        try:
            #use multithreading to run rates()
            pipe_p, pipe_c = mp.Pipe()
            error_pipe_p, error_pipe_c = mp.Pipe()
            p = mp.Process(target=run_rates, args=(pipe_c, ind, name, self.date, 
                                                   self.duration, self.threshold,
                                                   self.path, error_pipe_c))
            p.start()
            self.processes.append(p)
            hold = pipe_p.recv()
            errors = error_pipe_p.recv()
            if hold == -1:
                raise RatesError
            self.data2m[ind] = hold[0]
            self.data20u[ind] = hold[1]
            self.info[ind] = hold[2]
            p.join()
        except RatesError:
            self.log_error(errors[0], 'could not run rates()')
            return
        except Exception as inst:
            self.log_error(inst, 'could not create process')
            return
        finally:
            for error in errors:
                self.infoBox.addItem(error)
            self.todo -= 1
        #check which bin size to use
        if self.sBinBtn.isChecked():
            self.data[ind] = self.data2m[ind]
            self.bins[ind] = 0.002
        else:
            self.data[ind] = self.data20u[ind]
            self.bins[ind] = 0.00002
        self.totalPlots[ind] = len(self.data[ind])
        if self.data[ind]:
            try:
                #create plot
                self.tabs.widget(ind).clear()
                ax = self.tabs.widget(ind).fig.add_subplot(111)
                ax.bar(self.data[ind][0][1], self.data[ind][0][0], width=self.bins[ind])
                try:
                    self.tabs.widget(ind).draw()
                except:
                    pass
                self.currentPlot[ind] = 1 
            except Exception as inst:
                self.log_error(inst, 'could not update figure')
                return
            self.aveCountLbl.setText(str('%.3f' % self.info[ind][0][0]))
            self.minCountLbl.setText(str(self.info[ind][0][1]))
            self.dateLbl.setText(self.info[ind][0][2])
        else:
            self.currentPlot[ind] = 0
        if self.todo == 0:
            self.status.setText('Done Graphing')
        for box in [box for box in self.array if box.text(0) == name]:
            box.setText(1, str(len(self.data[ind])))
        self.tabs.setCurrentIndex(ind)
        self.set_num_plots()
        
    def cancel(self):
        pass
        
    def log_error(self, inst, message):
        f = open(self.errorlog, 'a+')
        with f:
            f.write(strftime('%Y-%m-%d %H:%M:%S   Error: ', gmtime()) 
                    + ' [' + str(message) + ']  '
                    + str(type(inst)) 
                    + '  ("' + str(inst) + '")' + '\n\n')
        self.status.setText('Error')
         
    def get_config(self):
        if not path.isfile(self.errorlog):
            open(self.errorlog, 'w+')
        if not path.isfile(self.config):
            open(self.config, 'w+')
            return
        f = open(self.config, 'r')
        variables = {'path: ': self._set_path, 
                     'date: ': self._set_date}
        with f:
            for line in f:
                for key, var in variables.iteritems():
                    if line.startswith(key):
                         var(str(line)[len(key):-1])                    
    def _set_path(self, path):
        self.path = path
    def _set_date(self, date):
        self.date = date
        
    def set_path(self):
        dirname = QtGui.QFileDialog.getExistingDirectory(self)
        if dirname == '':
            return
        dirname = re.sub('\\\\', '/', dirname) + '/'
        self.path = dirname
        f = open(self.config, 'r')
        text = []
        found = False
        with f:
            for line in f:
                if line.startswith('path:'):
                    text.append('path: %s\n' % str(dirname))
                    found = True
                else:
                    text.append(line)
        if not found:
            text.append('\npath: %s\n' % str(dirname))
        f = open(self.config, 'w+')
        with f:
            for line in text:
                f.write(line)
                
    def save_date(self):
        f = open(self.config, 'r')
        text = []
        found = False
        with f:
            for line in f:
                if line.startswith('date:'):
                    text.append('date: %s\n' % str(self.date))
                    found = True
                else:
                    text.append(line)
        if not found:
            text.append('\ndate: %s\n' % str(self.date))
        f = open(self.config, 'w+')
        with f:
            for line in text:
                f.write(line)
        
    def set_lists(self):
        self.bins = [0.002 for x in range(19)]
        self.data = [0 for x in range(19)]
        self.data2m = [0 for x in range(19)]
        self.data20u = [0 for x in range(19)]
        self.info = [0 for x in range(19)]
        self.currentPlot = [0 for x in range(19)]
        self.totalPlots = [0 for x in range(19)]
        
    def tree_clicked(self, item, column):
        if item.text(0) in ['LSU', 'Huntsville', 'Puerto Rico', 'Panama']:
            self.region_clicked(item, column)
        else:
            self.box_clicked(item, column)
            
    def region_clicked(self, item, column):
        pass
    
    def box_clicked(self, item, column):
        pass

    def set_year(self):
        self.date = str(self.yearBox.value()) + self.date[4:10]
        self.dayBox.setRange(1, monthrange(self.yearBox.value(), 
                                           self.monthBox.value())[1])
        self.get_enddate()
        
    def set_month(self):
        if self.monthBox.value() < 10:
            self.date = self.date[0:5] + '0' + str(self.monthBox.value()) + self.date[7:10]
        else:
            self.date = self.date[0:5] + str(self.monthBox.value()) + self.date[7:10]
        self.dayBox.setRange(1, monthrange(self.yearBox.value(), 
                                           self.monthBox.value())[1])
        self.get_enddate()
        
    def set_day(self):
        if self.dayBox.value() < 10:
            self.date = self.date[0:8] + '0' + str(self.dayBox.value())
        else:
            self.date = self.date[0:8] + str(self.dayBox.value())
        self.get_enddate()
        
    def get_enddate(self):
        self.duration = self.durationBox.value()
        
    def set_threshold(self):
        self.threshold = self.threshSlider.value()
        self.threshLbl.setText(str(self.threshold)+u' \u03C3')
        
    def set_bins(self):
        if self.sBinBtn.isChecked():
            self.bins[self.ndx()] = 0.002
            self.data[self.ndx()] = self.data2m[self.ndx()]
        else:
            self.bins[self.ndx()] = 0.00002
            self.data[self.ndx()] = self.data20u[self.ndx()]
        if self.data[self.ndx()]:
            i = self.ndx()
            label = self.tabs.tabText(self.ndx())
            self.tabs.removeTab(i)
            fig = Figure(figsize=(800, 600), dpi=72, 
                         facecolor=(1, 1, 1), edgecolor=(0, 0, 0))
            ax = fig.add_subplot(111)
            ax.bar(self.data[i][self.currentPlot[i]-1][1], 
                   self.data[i][self.currentPlot[i]-1][0], 
                   width=self.bins[i])
            self.tabs.insertTab(i, CanvasWidget(fig), label)
            self.tabs.setCurrentIndex(i)
    
    def changed_tabs(self):
        self.set_num_plots()
        if self.sBinBtn.isChecked() and self.bins[self.ndx()] != 0.002:
            self.set_bins()
        elif self.lBinBtn.isChecked() and self.bins[self.ndx()] != 0.00002:
            self.set_bins()

    def set_num_plots(self):
        pageText = str(self.currentPlot[self.ndx()]) + ' of ' + str(self.totalPlots[self.ndx()])
        self.pageLbl.setText(pageText)
        if (self.info[self.ndx()] != 0) and (self.currentPlot[self.ndx()] != 0):
            self.dateLbl.setText(str(self.info[self.ndx()][self.currentPlot[self.ndx()]-1][2]))
            self.minCountLbl.setText(str(self.info[self.ndx()][self.currentPlot[self.ndx()]-1][1]))
            self.aveCountLbl.setText(str('%.3f' % self.info[self.ndx()][self.currentPlot[self.ndx()]-1][0]))
        else:
            self.dateLbl.setText('--')
            self.minCountLbl.setText('--')
            self.aveCountLbl.setText('--')
            
    def prev_graph(self):
        if self.currentPlot[self.ndx()] > 1:
            i = self.ndx()
            label = self.tabs.tabText(self.ndx())
            self.tabs.removeTab(i)
            fig = Figure(figsize=(800, 600), dpi=72, 
                         facecolor=(1, 1, 1), edgecolor=(0, 0, 0))
            ax = fig.add_subplot(111)
            ax.bar(self.data[i][self.currentPlot[i]-2][1], 
                   self.data[i][self.currentPlot[i]-2][0], 
                   width=self.bins[i])
            self.tabs.insertTab(i, CanvasWidget(fig), label)
            self.tabs.setCurrentIndex(i)
            self.currentPlot[i] = self.currentPlot[i] - 1
            self.set_num_plots()
            
            
    def next_graph(self):
        if self.currentPlot[self.ndx()] < self.totalPlots[self.ndx()]:
            i = self.ndx()
            label = self.tabs.tabText(self.ndx())
            self.tabs.removeTab(i)
            fig = Figure(figsize=(800, 600), dpi=72, 
                         facecolor=(1, 1, 1), edgecolor=(0, 0, 0))
            ax = fig.add_subplot(111)
            ax.bar(self.data[i][self.currentPlot[i]][1], 
                   self.data[i][self.currentPlot[i]][0], 
                   width=self.bins[i])
            self.tabs.insertTab(i, CanvasWidget(fig), label)
            self.tabs.setCurrentIndex(i)
            self.currentPlot[i] = self.currentPlot[i] + 1
            self.set_num_plots()
            

class Window(QtGui.QMainWindow):
    
    """The main window of the program"""
    
    def __init__(self):
        super(Window, self).__init__()
        self.initUI()
        
    def initUI(self): 
        center = RatePlot()
       
        exitAction = QtGui.QAction(QtGui.QIcon('icons/exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)
        
        helpAction = QtGui.QAction('&Help', self)
        helpAction.setShortcut('Ctrl+H')
        helpAction.setStatusTip('Open Help File')
        helpAction.triggered.connect(self.open_help)
        
        pathAction = QtGui.QAction('&Path', self)
        pathAction.setShortcut('Ctrl+P')
        pathAction.setStatusTip('Set Path')
        pathAction.triggered.connect(center.set_path)
        
        dateAction = QtGui.QAction('&Date', self)
        dateAction.setShortcut('Ctrl+D')
        dateAction.setStatusTip('Save current date as default')
        dateAction.triggered.connect(center.save_date)
        
        errorAction = QtGui.QAction('&ErrorLog', self)
        errorAction.setShortcut('Ctrl+E')
        errorAction.setStatusTip('Open Errorlog')
        errorAction.triggered.connect(self.open_errorlog)
        
        self.statusBar()
        
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(pathAction)
        fileMenu.addAction(dateAction)
        fileMenu.addAction(errorAction)
        fileMenu.addAction(exitAction)   
        helpMenu = menubar.addMenu('&Help')
        helpMenu.addAction(helpAction)
        
        self.setCentralWidget(center)
        self.setGeometry(200, 200, 900, 700)  
        self.setWindowTitle('Tetra-II Analysis')
        self.setWindowIcon(QtGui.QIcon('icons/lsu.png'))
        self.show()
        
    def open_help(self):
        try:
            startfile(str(getcwd()) + '/info/help.txt')
        except Exception as inst:
            self.center.log_error(inst, 'could not open help file')
            self.center.status.setText('Error')
            
    def open_errorlog(self):
        try:
            startfile(str(getcwd()) + '/info/errorlog.txt')
        except Exception as inst:
            self.center.log_error(inst, 'could not open help file')
            self.center.status.setText('Error')
        
            
def main():
    app = QtGui.QApplication.instance()
    if not app:
        app = QtGui.QApplication(sys.argv)
    ex = Window()
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()