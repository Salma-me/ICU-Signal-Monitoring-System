import os
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QColorDialog, QMessageBox
from PyQt5.QtGui import QPixmap, QPainter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
import statistics

from pyqtgraph.widgets import PlotWidget
import sys
import newui
from Classes import FileBrowser

class MainApp(QtWidgets.QMainWindow, newui.Ui_MainWindow):
    def __init__(self):
        super(MainApp, self).__init__()
        self.setupUi(self)
        
        self.actionGraph_1.triggered.connect(lambda: self.plot_data(self.plotWidget_L))
        self.actionGraph_2.triggered.connect(lambda: self.plot_data(self.plotWidget_R))
        
        self.fileBrowser = FileBrowser(self)
        self.snapshot_images_lst = []
        self.pdf_count = 0
        self.plotsL = {}
        self.plotsR = {}
        self.plotsDataL = {} # dictionary to store time and amplitude values of each plot
        self.plotsDataR = {} # dictionary to store time and amplitude values of each plot
        self.timers_L = {}  # dictionary to store timers of the graph on the left
        self.timers_R = {}  # dictionary to store timers of the graph on the right
        self.update_data_dict = {}
        self.isPlayingL = True
        self.isPlayingR = True
        self.rewindPlotL = False
        self.rewindPlotR = False
        self.PlotsFinishedL = {} # dictionary to check if all signals are completely plotted
        self.PlotsFinishedR = {} # dictionary to check if all signals are completely plotted
        
        self.graph1ViewBox = self.plotWidget_L.getViewBox()
        self.graph2ViewBox = self.plotWidget_R.getViewBox()
        
        self.horizontalScrollBar_L.valueChanged.connect(self.scroll_plot_x_L)
        self.verticalScrollBar_L.valueChanged.connect(self.scroll_plot_y_L)
        self.horizontalScrollBar_R.valueChanged.connect(self.scroll_plot_x_R)
        self.verticalScrollBar_R.valueChanged.connect(self.scroll_plot_y_R)
        
        self.legend_L = self.plotWidget_L.addLegend()
        self.legend_R = self.plotWidget_R.addLegend()
        
        self.pushButton_L_color.clicked.connect(self.showColorDialog_L)
        self.pushButton_R_color.clicked.connect(self.showColorDialog_R)
        
        self.lineEdit_L_editLabel.returnPressed.connect(self.update_legend_and_item_L)
        self.lineEdit_R_editLabel.returnPressed.connect(self.update_legend_and_item_R)

        self.pushButton_L_take_snapshot.clicked.connect(self.take_snapshot_L)
        self.pushButton_R_take_snapshot.clicked.connect(self.take_snapshot_R)

        self.pushButton_move_plot_L.clicked.connect(self.move_plot_L_to_R)
        self.pushButton_move_plot_R.clicked.connect(self.move_plot_R_to_L)

        self.pushButton_L_zoomIn.clicked.connect(lambda: self.zoomIn(graphNumber = 1))
        self.pushButton_R_zoomIn.clicked.connect(lambda: self.zoomIn(graphNumber = 2))
        self.pushButton_L_zoomOut.clicked.connect(lambda: self.zoomOut(graphNumber = 1))
        self.pushButton_R_zoomOut.clicked.connect(lambda: self.zoomOut(graphNumber = 2))

        # initialize cine speed sliders settings
        self.horizontalSlider_L_speed.setRange(5, 20)
        self.horizontalSlider_L_speed.setValue(10)
        self.horizontalSlider_L_speed.setInvertedAppearance(True)
        self.horizontalSlider_R_speed.setRange(5, 20)
        self.horizontalSlider_R_speed.setValue(10)
        self.horizontalSlider_R_speed.setInvertedAppearance(True)
        self.horizontalSlider_L_speed.valueChanged.connect(self.updateCineSpeedL)
        self.horizontalSlider_R_speed.valueChanged.connect(self.updateCineSpeedR)

        self.pushButton_L_playPause.setText("Play")
        self.pushButton_R_playPause.setText("Play")
        self.pushButton_L_playPause.clicked.connect(self.togglePlayPauseL)
        self.pushButton_R_playPause.clicked.connect(self.togglePlayPauseR)
        
        # unenable stop and rewind buttons
        self.pushButton_L_stop.setEnabled(False)
        self.pushButton_R_stop.setEnabled(False)

        self.pushButton_L_rewind.setEnabled(False)
        self.pushButton_R_rewind.setEnabled(False)

        self.pushButton_L_stop.clicked.connect(self.stopPlotL)
        self.pushButton_R_stop.clicked.connect(self.stopPlotR)

        self.pushButton_L_rewind.clicked.connect(lambda: self.handleRewindPlot(self.plotWidget_L))
        self.pushButton_R_rewind.clicked.connect(lambda: self.handleRewindPlot(self.plotWidget_R))

        self.checkBox_linkGraphs.stateChanged.connect(self.toggleLinkGraphs)
        self.pushButton_export.clicked.connect(self.export_to_pdf)

        self.rewindTimerL = QtCore.QTimer()
        self.rewindTimerR = QtCore.QTimer()

        self.viewBoxStepX_L = 0
        self.viewBoxStepX_R = 0

        # boolean variables to catch cases of
        # moving a plot from one graph to the other 
        self.movingLtoR = False
        self.movingRtoL = False

        self.new_max_x_L = 0.001
        self.new_max_x_R = 0.001
        self.max_offset_R = 0
        self.max_offset_L = 0

    def plot_data(self, widget):
        time, amplitude = self.fileBrowser.browse_file() 
        index = 0
        if time is not None and amplitude is not None:
            i = 0  # Initialize counter inside a list
            timer = QtCore.QTimer()
        
            if widget is self.plotWidget_L:
                # Create a new plot on the passed widget
                plot = widget.plot()

                # Add the plot to the appropriate legend and combo box
                signal_name = 'Signal {}'.format(len(self.plotsL) + len(self.plotsR) + 1)

                index = len(self.plotsL) + len(self.plotsR)

                self.plotsL[signal_name] = plot

                # store the plots' original data before shifting
                self.plotsDataL[signal_name] = [time, amplitude]

                # Offset the amplitude of the new signal
                offset = len(self.plotsL) * 2
                amplitude = amplitude - offset

                self.update_data_dict[index] = {
                    "time": time,
                    "amplitude": amplitude,
                    "plot": plot,
                    "widget": widget,
                    "signal_name": signal_name,
                    "indexTrack":i
                }

                # unenable rewind and stop buttons
                self.pushButton_L_stop.setEnabled(False)
                self.pushButton_L_rewind.setEnabled(False)

                self.legend_L.addItem(plot, signal_name)
                self.comboBox_L_channels.addItem(signal_name)
                self.timers_L[signal_name] = timer  # Store timer in the dictionary
                if self.isPlayingL:
                    self.pushButton_L_playPause.setText("Pause")
                    speed = self.horizontalSlider_L_speed.value()
                    timer.start(speed)  # Update every 50 ms by default
                
            elif widget is self.plotWidget_R:
                # Create a new plot on the passed widget
                plot = widget.plot()

                # Add the plot to the appropriate legend and combo box
                signal_name = 'Signal {}'.format(len(self.plotsR) + len(self.plotsL) + 1)

                index = len(self.plotsL) + len(self.plotsR)
                
                self.plotsR[signal_name] = plot

                # store the plots' original data before shifting
                self.plotsDataR[signal_name] = [time, amplitude]

                # Offset the amplitude of the new signal
                offset = len(self.plotsR) * 2  # Adjust the value '10' as needed
                amplitude = amplitude - offset

                self.update_data_dict[index] = {
                    "time": time,
                    "amplitude": amplitude,
                    "plot": plot,
                    "widget": widget,
                    "signal_name": signal_name,
                    "indexTrack": i
                }

                # unenable rewind and stop buttons
                self.pushButton_R_stop.setEnabled(False)
                self.pushButton_R_rewind.setEnabled(False)

                self.legend_R.addItem(plot, signal_name)
                self.comboBox_R_channels.addItem(signal_name)
                self.timers_R[signal_name] = timer  # Store timer in the dictionary
                if self.isPlayingR:
                    self.pushButton_R_playPause.setText("Pause")
                    speed = self.horizontalSlider_R_speed.value()
                    timer.start(speed)  # Update every 50 ms by default

            timer.timeout.connect(lambda: self.update_plot_data(index, self.update_data_dict))
            # Enable scrolling in the PlotWidget
            widget.getViewBox().setMouseEnabled(x=True, y=True)


    def update_plot_data(self,index, dataDict):
        # calculate the offset considering different cases
        # if self.movingLtoR:
        #     self.movingLtoR = False
        #     offset = len(self.plotsR) * 2
        # elif self.movingRtoL:
        #     self.movingRtoL = False
        #     offset = len(self.plotsL) * 2
        # else:
        #     offset = 0
        # # update the amplitude
        # amplitude -= offset
        signal_name = dataDict[index]["signal_name"]
        widget = dataDict[index]["widget"]
        plot = dataDict[index]["plot"]
        time = dataDict[index]["time"]
        amplitude = dataDict[index]["amplitude"]
        i = dataDict[index]["indexTrack"]

        min_y, max_Y = self.get_min_max_y_for_widget(widget)
        # widget.setYRange(-5, 5)
        if i < len(time):
            if widget is self.plotWidget_L:
                if signal_name in self.plotsDataL:
                    if i > 600:
                        self.graph1ViewBox.setXRange(self.plotsDataL[signal_name][0][i-600], time[i])
                        self.graph1ViewBox.setLimits(xMin=-0.02, xMax=time[i] + 0.2, yMin=min_y - 0.01, yMax=max_Y + 0.01)
                    else:
                        self.graph1ViewBox.setXRange(0, self.plotsDataL[signal_name][0][600])
                        self.graph1ViewBox.setLimits(xMin=-0.02, xMax=(self.plotsDataL[signal_name][0][600]) + 0.2,  yMin=min_y - 0.01, yMax=max_Y + 0.01)
            else:
                if signal_name in self.plotsDataR:
                    if i > 600:
                        self.graph2ViewBox.setXRange(self.plotsDataR[signal_name][0][i-600], time[i])
                        self.graph2ViewBox.setLimits(xMin=-0.02, xMax=time[i], yMin=min_y - 0.01, yMax=max_Y + 0.01)
                    else:
                        self.graph2ViewBox.setXRange(0, self.plotsDataR[signal_name][0][600])
                        self.graph2ViewBox.setLimits(xMin=-0.02, xMax=(self.plotsDataR[signal_name][0][600]),  yMin=min_y - 0.01, yMax=max_Y + 0.01)

        # continue plotting
        if i < len(time):
            plot.setData(time[:i], amplitude[:i])
            i += 1
            dataDict[index]["indexTrack"] = i
        else:
            if signal_name in self.timers_L:
                self.timers_L[signal_name].stop()  # Stop updating after all data is plotted
            elif signal_name in self.timers_R:
                self.timers_R[signal_name].stop()  # Stop updating after all data is plotted
            
            if widget is self.plotWidget_L:
                self.PlotsFinishedL[signal_name] = True  # change plotting progress state
            else:
                self.PlotsFinishedR[signal_name] = True  # change plotting progress state
        # check if all signals in one graph finished plotting
        if all(self.PlotsFinishedL.values()) and len(self.PlotsFinishedL) != 0:
            self.pushButton_L_stop.setEnabled(True)  # enable stop viewing button
            self.pushButton_L_rewind.setEnabled(True) # enable rewind button
            # toggle to stop playing
            # self.togglePlayPauseL()
            self.pushButton_L_playPause.setText("Play")
            self.isPlayingL = False
        elif all(self.PlotsFinishedR.values()) and len(self.PlotsFinishedR) != 0:
            self.pushButton_R_stop.setEnabled(True)  # enable stop viewing button
            self.pushButton_R_rewind.setEnabled(True) # enable rewind button
            # toggle to stop playing
            # self.togglePlayPauseR()
            self.pushButton_R_playPause.setText("Play")
            self.isPlayingR = False


    def updateCineSpeedL(self):
        speed = self.horizontalSlider_L_speed.value()
        if not self.checkBox_linkGraphs.isChecked():
            if not self.rewindPlotL:
                for signal_name in self.timers_L:
                    timer = self.timers_L[signal_name]
                    timer.setInterval(speed)
            else:
                self.rewindTimerL.setInterval(speed)
        else:
            self.updateCineSpeedBoth(speed)
            

    def updateCineSpeedR(self):
        speed = self.horizontalSlider_R_speed.value()
        if not self.checkBox_linkGraphs.isChecked():
            if not self.rewindPlotR:
                for signal_name in self.timers_R:
                    timer = self.timers_R[signal_name]
                    timer.setInterval(speed)
            else:
                self.rewindTimerR.setInterval(speed)
        else:
            self.updateCineSpeedBoth(speed)
    
    def updateCineSpeedBoth(self, value):
        # Update the cine speed for both plot widgets
        self.horizontalSlider_L_speed.setValue(value)
        self.horizontalSlider_R_speed.setValue(value)

        # Now, update the actual cine speed for both widgets.
        speed = value

        for timer in self.timers_L.values():
            timer.setInterval(speed)

        for timer in self.timers_R.values():
            timer.setInterval(speed)

    def togglePlayPauseL(self):
        if not self.checkBox_linkGraphs.isChecked():
            if not self.rewindPlotL:
                if self.isPlayingL:
                    self.isPlayingL = False
                    self.pushButton_L_playPause.setText("Play")
                    # Pause the timer of the left plot
                    self.pauseTimer(self.timers_L)
                else:
                    self.isPlayingL = True
                    self.pushButton_L_playPause.setText("Pause")
                    # Start the timer of the left plot
                    self.startTimer(self.timers_L)
            else:
                if self.isPlayingL:
                    self.isPlayingL = False
                    self.pushButton_L_playPause.setText("Play")
                    # Pause the rewind timer of the left plot
                    self.rewindTimerL.stop()
                else:
                    self.isPlayingL = True
                    self.pushButton_L_playPause.setText("Pause")
                    # Start the rewind timer of the left plot
                    self.rewindTimerL.start()
        else:
            self.togglePlayPauseBoth()

    def togglePlayPauseR(self):
        if not self.checkBox_linkGraphs.isChecked():
            if not self.rewindPlotR:
                if self.isPlayingR:
                    self.isPlayingR = False
                    self.pushButton_R_playPause.setText("Play")
                    # Pause the timer of the left plot
                    self.pauseTimer(self.timers_R)
                else:
                    self.isPlayingR = True
                    self.pushButton_R_playPause.setText("Pause")
                    # Start the timer of the left plot
                    self.startTimer(self.timers_R)
            else:
                if self.isPlayingR:
                    self.isPlayingR = False
                    self.pushButton_R_playPause.setText("Play")
                    # Pause the rewind timer of the left plot
                    self.rewindTimerR.stop()
                else:
                    self.isPlayingR = True
                    self.pushButton_R_playPause.setText("Pause")
                    # Start the rewind timer of the left plot
                    self.rewindTimerR.start()
        else:
            self.togglePlayPauseBoth()

    def togglePlayPauseBoth(self):
        # both graphs are not rewinding
        if not self.rewindPlotL and not self.rewindPlotR:
            if self.isPlayingL:
                self.isPlayingL = False
                self.isPlayingR = False
                self.pushButton_L_playPause.setText("Play")
                self.pushButton_R_playPause.setText("Play")
                # Pause the timer of both plot
                self.pauseTimer(self.timers_L)
                self.pauseTimer(self.timers_R)
            else:
                self.isPlayingL = True
                self.isPlayingR = True
                self.pushButton_L_playPause.setText("Pause")
                self.pushButton_R_playPause.setText("Pause")
                # Start the timer of both plot
                self.startTimer(self.timers_L)
                self.startTimer(self.timers_R)
        # both graphs are rewinding
        elif self.rewindPlotL and self.rewindPlotR:
            if self.isPlayingL:
                self.isPlayingL = False
                self.isPlayingR = False
                self.pushButton_L_playPause.setText("Play")
                self.pushButton_R_playPause.setText("Play")
                # Pause the rewind timer of both plot
                self.rewindTimerL.stop()
                self.rewindTimerR.stop()
            else:
                self.isPlayingL = True
                self.isPlayingR = True
                self.pushButton_L_playPause.setText("Pause")
                self.pushButton_R_playPause.setText("Pause")
                # Start the rewind timer of both plots
                self.rewindTimerL.start()
                self.rewindTimerR.start()
        # only right graph is rewinding
        elif self.rewindPlotL and not self.rewindPlotR:
            if self.isPlayingL:
                self.isPlayingL = False
                self.isPlayingR = False
                self.pushButton_L_playPause.setText("Play")
                self.pushButton_R_playPause.setText("Play")
                # Pause timers
                self.rewindTimerL.stop()
                self.pauseTimer(self.timers_R)
            else:
                self.isPlayingL = True
                self.isPlayingR = True
                self.pushButton_L_playPause.setText("Pause")
                self.pushButton_R_playPause.setText("Pause")
                # Start timers
                self.rewindTimerL.start()
                self.startTimer(self.timers_R)
        # only left graph is rewinding
        else:
            if self.isPlayingL:
                self.isPlayingL = False
                self.isPlayingR = False
                self.pushButton_L_playPause.setText("Play")
                self.pushButton_R_playPause.setText("Play")
                # Pause timers
                self.pauseTimer(self.timers_L)
                self.rewindTimerR.stop()
            else:
                self.isPlayingL = True
                self.isPlayingR = True
                self.pushButton_L_playPause.setText("Pause")
                self.pushButton_R_playPause.setText("Pause")
                # Start timers
                self.startTimer(self.timers_L)
                self.rewindTimerR.start()

    def startTimer(self, timersDict):
        for timer in timersDict.values():
            timer.start()

    def pauseTimer(self, timersDict):
        for timer in timersDict.values():
            timer.stop()

    def get_min_max_x_for_widget(self, widget):
        min_x = float('inf')
        max_x = float('-inf')

        for plot in widget.getPlotItem().listDataItems():
            x_data = plot.xData
            if x_data is not None:
                min_x = min(min_x, min(x_data))
                max_x = max(max_x, max(x_data))

        return min_x, max_x
    
    def get_min_max_y_for_widget(self, widget):
        min_y = float('inf')
        max_y = float('-inf')

        for plot in widget.getPlotItem().listDataItems():
            y_data = plot.yData
            if y_data is not None:
                min_y = min(min_y, min(y_data))
                max_y = max(max_y, max(y_data))

        return min_y, max_y
    
    def handleRewindPlot(self, widget):
        if not self.checkBox_linkGraphs.isChecked():
            if widget is self.plotWidget_L:
                self.rewindPlotL = True
                self.pushButton_L_rewind.setEnabled(False)
                self.resetL(self.plotWidget_L)
            else:
                self.rewindPlotR = True
                self.pushButton_R_rewind.setEnabled(False)
                self.resetR(self.plotWidget_R)
        else:
            self.handleRewindBothPlots()

    def handleRewindBothPlots(self):
        if self.pushButton_L_rewind.isEnabled() and self.pushButton_R_rewind.isEnabled():
            # start rewinding both graphs
            self.rewindPlotL = True
            self.pushButton_L_rewind.setEnabled(False)
            self.resetL(self.plotWidget_L)

            self.rewindPlotR = True
            self.pushButton_R_rewind.setEnabled(False)
            self.resetR(self.plotWidget_R)
        else:
            # Create a QMessageBox and display the critical error dialog
            msg_box = QtWidgets.QMessageBox()
            msg_box.setIcon(QtWidgets.QMessageBox.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("This action is not available, You must uncheck the link checkbox first")
            msg_box.exec_()

    def resetL(self, widget):
        self.pushButton_L_stop.setEnabled(False)
        self.pushButton_move_plot_L.setEnabled(False)
        self.new_max_x_L = 0.001
        # resetting x-axis range with
        min_x_L, max_x_L = self.get_min_max_x_for_widget(self.plotWidget_L)
        self.graph1ViewBox.setXRange(0, 0.001)
        # timer settings
        self.rewindTimerL.timeout.connect(lambda: self.animateXAxisReset(widget, self.graph1ViewBox, min_x_L, max_x_L))
        # get cine speed
        speed = self.horizontalSlider_L_speed.value()
        self.rewindTimerL.setInterval(speed * 10)
        # start rewinding
        self.rewindTimerL.start()
        self.isPlayingL = True
        self.pushButton_L_playPause.setText("Pause")

    def resetR(self, widget):
        self.pushButton_R_stop.setEnabled(False)
        self.pushButton_move_plot_R.setEnabled(False)
        self.new_max_x_R = 0.001
        #  resetting x-axis range with
        min_x_R, max_x_R = self.get_min_max_x_for_widget(self.plotWidget_R)
        self.graph2ViewBox.setXRange(0, 0.001)
        # timer settings
        self.rewindTimerR.timeout.connect(lambda: self.animateXAxisReset(widget, self.graph2ViewBox, min_x_R, max_x_R))
        # get cine speed
        speed = self.horizontalSlider_R_speed.value()
        self.rewindTimerR.setInterval(speed * 10)
        # start rewinding
        self.rewindTimerR.start()
        self.isPlayingR = True
        self.pushButton_R_playPause.setText("Pause")

    def animateXAxisReset(self, widget, view_box, min_x, max_x):
        if widget is self.plotWidget_L:
            if self.new_max_x_L < max_x:
                # increase view range by a step of 0.001
                self.new_max_x_L += 0.001
                if (self.new_max_x_L < 0.05):
                    view_box.setXRange(min_x, self.new_max_x_L)
                else:
                    self.viewBoxStepX_L += 0.001 
                    view_box.setXRange(min_x + self.viewBoxStepX_L, self.new_max_x_L)
            else:
                    # stop and reset rewind
                    self.rewindTimerL.stop()
                    self.new_max_x_L = 0
                    self.rewindPlotL = False
                    self.pushButton_L_rewind.setEnabled(True)
                    self.pushButton_L_stop.setEnabled(True)
                    self.isPlayingL = False
                    self.pushButton_L_playPause.setText("Play")       
        else:
            if self.new_max_x_R < max_x:
                # increase view range by a step of 0.001
                self.new_max_x_R += 0.001
                if (self.new_max_x_R < 0.05):
                    view_box.setXRange(min_x, self.new_max_x_R)
                else:
                    self.viewBoxStepX_R += 0.001 
                    view_box.setXRange(min_x + self.viewBoxStepX_R, self.new_max_x_R)
            else:
                    # stop and reset rewind
                    self.rewindTimerR.stop()
                    self.new_max_x_R = 0
                    self.rewindPlotR = False
                    self.pushButton_R_rewind.setEnabled(True)
                    self.pushButton_R_stop.setEnabled(True)
                    self.isPlayingR = False
                    self.pushButton_R_playPause.setText("Play")                  

    def scroll_plot_x_L(self, value):
        ###### method 1 ################
        # window_size = 10
        # min_x = max(0, value - window_size / 2)
        # max_x = min_x + window_size
        # self.graph1ViewBox.setXRange(min_x, max_x)
        ###### method 2 ################
        # min_x, max_x = self.get_min_max_x_for_widget(self.plotWidget_L)
        # step = max_x - min_x
        # self.verticalScrollBar_L.setMinimum(0)
        # self.verticalScrollBar_L.setMaximum(int(max_x + 0.5))
        # self.verticalScrollBar_L.setPageStep(int(step))
        # new_min_x = max(0, value)
        # new_max_x = value + self.plotWidget_L.plotItem.viewRange()[1][1]
        # self.graph1ViewBox.setXRange(int(new_min_x), int(new_max_x))
        ###### method 3 ################
        selectedSignal = self.comboBox_L_channels.currentText()
        length = len(self.plotsDataL[selectedSignal][1])
        min_x, max_x = self.get_min_max_x_for_widget(self.plotWidget_L)

        # Set the minimum and maximum values for the vertical scroll bar
        self.horizontalScrollBar_L.setMinimum(0)
        self.horizontalScrollBar_L.setMaximum(length)  

        # Set the single step value for the vertical scroll bar
        self.verticalScrollBar_L.setSingleStep(20)

        my_range = (max_x - min_x) / 5
    
        if 0 <= value <= length * (1/5):
            self.plotWidget_L.setXRange(max_x - my_range, max_x)
        elif length * (1/5) < value <= length * (2/5):
            self.plotWidget_L.setXRange(max_x - my_range * 2, max_x - my_range)
        elif length * (2/5) < value <= length * (3/5):
            self.plotWidget_L.setXRange(max_x - my_range * 3, max_x - my_range * 2)
        elif length * (3/5) < value <= length * (4/5):
            self.plotWidget_L.setXRange(max_x - my_range * 4, max_x - my_range * 3)
        else:
            self.plotWidget_L.setXRange(min_x, max_x - my_range * 4)

    def scroll_plot_y_L(self, value):
        ###### method 1 ################
        # window_size = 10
        # min_y = max(0, value - window_size / 2)
        # max_y = min_y + window_size
        # self.graph1ViewBox.setYRange(min_y, max_y)
        ###### method 2 ################
        # min_y, max_y = self.get_min_max_y_for_widget(self.plotWidget_L)
        # step = max_y - min_y
        # self.verticalScrollBar_L.setMinimum(int(min_y - 0.5))
        # self.verticalScrollBar_L.setMaximum(int(max_y + 0.5))
        # self.verticalScrollBar_L.setPageStep(int(step))
        # new_min_y = value
        # new_max_y = value + self.plotWidget_L.plotItem.viewRange()[1][1]
        # self.graph1ViewBox.setYRange(int(new_min_y), int(new_max_y))
        ########### method 4 ##################
        selectedSignal = self.comboBox_L_channels.currentText()
        length = len(self.plotsDataL[selectedSignal][1])
        min_y, max_y = self.get_min_max_y_for_widget(self.plotWidget_L)

        # Set the minimum and maximum values for the vertical scroll bar
        self.verticalScrollBar_L.setMinimum(0)
        self.verticalScrollBar_L.setMaximum(length)  

        # Set the single step value for the vertical scroll bar
        self.verticalScrollBar_L.setSingleStep(20)

        my_range = (max_y - min_y) / 5
    
        if 0 <= value <= length * (1/5):
            self.plotWidget_L.setYRange(max_y - my_range, max_y)
        elif length * (1/5) < value <= length * (2/5):
            self.plotWidget_L.setYRange(max_y - my_range * 2, max_y - my_range)
        elif length * (2/5) < value <= length * (3/5):
            self.plotWidget_L.setYRange(max_y - my_range * 3, max_y - my_range * 2)
        elif length * (3/5) < value <= length * (4/5):
            self.plotWidget_L.setYRange(max_y - my_range * 4, max_y - my_range * 3)
        else:
            self.plotWidget_L.setYRange(min_y, max_y - my_range * 4)
        

    def scroll_plot_x_R(self, value):
        ###### method 1 ################
        # window_size = 10
        # min_x = max(0, value - window_size / 2)
        # max_x = min_x + window_size
        # self.graph2ViewBox.setXRange(min_x, max_x)
        ###### method 2 ################
        # min_x, max_x = self.get_min_max_x_for_widget(self.plotWidget_R)
        # step = max_x - min_x
        # self.verticalScrollBar_R.setMinimum(int(min_x - 0.5))
        # self.verticalScrollBar_R.setMaximum(int(max_x + 0.5))
        # self.verticalScrollBar_R.setPageStep(int(step))
        # new_min_x = max(0, value)
        # new_max_x = value + self.plotWidget_R.plotItem.viewRange()[1][1]
        # self.graph2ViewBox.setXRange(int(new_min_x), int(new_max_x))
        ###### method 3 ################
        selectedSignal = self.comboBox_L_channels.currentText()
        length = len(self.plotsDataR[selectedSignal][1])
        min_x, max_x = self.get_min_max_x_for_widget(self.plotWidget_R)

        # Set the minimum and maximum values for the vertical scroll bar
        self.horizontalScrollBar_R.setMinimum(0)
        self.horizontalScrollBar_R.setMaximum(length)  

        # Set the single step value for the vertical scroll bar
        self.verticalScrollBar_R.setSingleStep(20)

        my_range = (max_x - min_x) / 5
    
        if 0 <= value <= length * (1/5):
            self.plotWidget_R.setXRange(max_x - my_range, max_x)
        elif length * (1/5) < value <= length * (2/5):
            self.plotWidget_R.setXRange(max_x - my_range * 2, max_x - my_range)
        elif length * (2/5) < value <= length * (3/5):
            self.plotWidget_R.setXRange(max_x - my_range * 3, max_x - my_range * 2)
        elif length * (3/5) < value <= length * (4/5):
            self.plotWidget_R.setXRange(max_x - my_range * 4, max_x - my_range * 3)
        else:
            self.plotWidget_R.setXRange(min_x, max_x - my_range * 4)

    def scroll_plot_y_R(self, value):
        ###### method 1 ################
        # window_size = 10
        # min_y = max(0, value - window_size / 2)
        # max_y = min_y + window_size
        # self.graph2ViewBox.setYRange(min_y, max_y)
        ###### method 2 ################
        # min_y, max_y = self.get_min_max_y_for_widget(self.plotWidget_R)
        # step = max_y - min_y
        # self.verticalScrollBar_R.setMinimum(int(min_y - 0.5))
        # self.verticalScrollBar_R.setMaximum(int(max_y + 0.5))
        # self.verticalScrollBar_R.setPageStep(int(step))
        # new_min_y = value
        # new_max_y = value + self.plotWidget_R.plotItem.viewRange()[1][1]
        # self.graph2ViewBox.setYRange(int(new_min_y), int(new_max_y))
        ###### method 4 ################ 
        selectedSignal = self.comboBox_R_channels.currentText()
        length = len(self.plotsDataR[selectedSignal][1])
        min_y, max_y = self.get_min_max_y_for_widget(self.plotWidget_R)

        # Set the minimum and maximum values for the vertical scroll bar
        self.verticalScrollBar_R.setMinimum(0)
        self.verticalScrollBar_R.setMaximum(length)  

        # Set the single step value for the vertical scroll bar
        self.verticalScrollBar_R.setSingleStep(20)

        my_range = (max_y - min_y) / 5
    
        if 0 <= value <= length * (1/5):
            self.plotWidget_R.setYRange(max_y - my_range, max_y)
        elif length * (1/5) < value <= length * (2/5):
            self.plotWidget_R.setYRange(max_y - my_range * 2, max_y - my_range)
        elif length * (2/5) < value <= length * (3/5):
            self.plotWidget_R.setYRange(max_y - my_range * 3, max_y - my_range * 2)
        elif length * (3/5) < value <= length * (4/5):
            self.plotWidget_R.setYRange(max_y - my_range * 4, max_y - my_range * 3)
        else:
            self.plotWidget_R.setYRange(min_y, max_y - my_range * 4)

    def showColorDialog_L(self):
        color = QColorDialog.getColor()
        if color.isValid():
            # Apply the color to the signal associated with the current item in comboBox_L_channels
            signal_name = self.comboBox_L_channels.currentText()
            # Assuming self.plots is a dictionary that maps signal names to plot objects
            plot = self.plotsL[signal_name]
            plot.setPen(color.name())

    def showColorDialog_R(self):
        color = QColorDialog.getColor()
        if color.isValid():
            # Apply the color to the signal associated with the current item in comboBox_R_channels
            signal_name = self.comboBox_R_channels.currentText()
            # Assuming self.plots is a dictionary that maps signal names to plot objects
            plot = self.plotsR[signal_name]
            plot.setPen(color.name())

    def update_legend_and_item_L(self):
        # Get the new label from the QLineEdit
        new_label = self.lineEdit_L_editLabel.text()

        # Get the current signal name from the combo box
        signal_name = self.comboBox_L_channels.currentText()

        # Update the legend
        plot = self.plotsL[signal_name]
        self.legend_L.removeItem(signal_name)
        self.legend_L.addItem(plot, new_label)

        # Update the combo box item
        index = self.comboBox_L_channels.currentIndex()
        self.comboBox_L_channels.setItemText(index, new_label)

        # Update the signal name in self.plots
        self.plotsL[new_label] = self.plotsL.pop(signal_name)

        # Update the signal name in self.plotsDataL
        self.plotsDataL[new_label] = self.plotsDataL.pop(signal_name)
        matching_key = [key for key, value in self.update_data_dict.items() if value["signal_name"] == signal_name]
        self.update_data_dict[matching_key[0]]["signal_name"] = new_label

        # Update the signal name in self.timers_L
        self.timers_L[new_label] = self.timers_L.pop(signal_name)

        # Clear the QLineEdit
        self.lineEdit_L_editLabel.clear()

    def update_legend_and_item_R(self):
        # Get the new label from the QLineEdit
        new_label = self.lineEdit_R_editLabel.text()

        # Get the current signal name from the combo box
        signal_name = self.comboBox_R_channels.currentText()

        # Update the legend
        plot = self.plotsR[signal_name]
        self.legend_R.removeItem(signal_name)
        self.legend_R.addItem(plot, new_label)

        # Update the combo box item
        index = self.comboBox_R_channels.currentIndex()
        self.comboBox_R_channels.setItemText(index, new_label)

        # Update the signal name in self.plots
        self.plotsR[new_label] = self.plotsR.pop(signal_name)

        # Update the signal name in self.plotsDataR
        self.plotsDataR[new_label] = self.plotsDataR.pop(signal_name)

        matching_key = [key for key, value in self.update_data_dict.items() if value["signal_name"] == signal_name]
        self.update_data_dict[matching_key[0]]["signal_name"] = new_label

        # Update the signal name in self.timers_R
        self.timers_R[new_label] = self.timers_R.pop(signal_name)

        # Clear the QLineEdit
        self.lineEdit_R_editLabel.clear()

    def zoomIn(self, graphNumber):
        ########### method 1 ###################
        # if graphNumber == 1 and not self.checkBox_linkGraphs.isChecked():
        #     self.graph1ViewBox.scaleBy((0.5, 0.5))
        # elif graphNumber == 2 and not self.checkBox_linkGraphs.isChecked():
        #     self.graph2ViewBox.scaleBy((0.5, 0.5))
        # else:
        #     self.graph1ViewBox.scaleBy((0.5, 0.5))
        #     self.graph2ViewBox.scaleBy((0.5, 0.5))
        ############ method 2 ##################
        if graphNumber == 1:
            self.graph1ViewBox.scaleBy((0.5, 0.5))
        else:
            self.graph2ViewBox.scaleBy((0.5, 0.5))


    def zoomOut(self, graphNumber):
        ######## method 1 ###################
        # if graphNumber == 1 and not self.checkBox_linkGraphs.isChecked():
        #     self.graph1ViewBox.scaleBy((1/0.5, 1/0.5))
        # elif graphNumber == 2 and not self.checkBox_linkGraphs.isChecked():
        #     self.graph2ViewBox.scaleBy((1/0.5, 1/0.5))
        # else:
        #     self.graph1ViewBox.scaleBy((1/0.5, 1/0.5))
        #     self.graph2ViewBox.scaleBy((1/0.5, 1/0.5))
        ######## method 2 ###################
        if graphNumber == 1:
            self.graph1ViewBox.scaleBy((1/0.5, 1/0.5))
        else:
            self.graph2ViewBox.scaleBy((1/0.5, 1/0.5))

    def move_plot_L_to_R(self):
        self.movingLtoR = True
        # Get the current signal name from comboBox_L_channels
        signal_name = self.comboBox_L_channels.currentText()
        if signal_name == '':
            self.movingLtoR = False
            return
        
        time = self.plotsDataL[signal_name][0]
        amplitude = self.plotsDataL[signal_name][1]

        # Remove the signal from the left plot and legend
        plot = self.plotsL[signal_name]
        del self.plotsL[signal_name]
        del self.plotsDataL[signal_name]
        self.plotWidget_L.removeItem(plot)
        self.legend_L.removeItem(signal_name)
        self.comboBox_L_channels.removeItem(self.comboBox_L_channels.currentIndex())
        timer = self.timers_L[signal_name]
        del self.timers_L[signal_name]

        # Add the signal to the right plot and legend
        self.plotsR[signal_name] = plot
        self.plotsDataR[signal_name] = [time, amplitude]
        self.plotWidget_R.addItem(plot)
        self.legend_R.addItem(plot, signal_name)
        self.comboBox_R_channels.addItem(signal_name)
        self.timers_R[signal_name] = timer

        offset = max(self.max_offset_R, len(self.plotsR) * 10)
        self.max_offset_R += 10
        offset = self.max_offset_R
        new_amplitude = amplitude - offset
        plot.setData(time, new_amplitude)
        matching_key = [key for key, value in self.update_data_dict.items() if value["signal_name"] == signal_name]
        self.update_data_dict[matching_key[0]]["amplitude"] = new_amplitude
        self.update_data_dict[matching_key[0]]["plot"] = plot
        self.update_data_dict[matching_key[0]]["widget"] = self.plotWidget_R

        # handle timer state depending on play/pause state of the move to plot
        speed = self.horizontalSlider_R_speed.value()
        timer.setInterval(speed * 10)
        if self.isPlayingR:
            timer.start() 
        else:
            timer.stop()

    def move_plot_R_to_L(self):
        self.movingRtoL = True
        # Get the current signal name from comboBox_R_channels
        signal_name = self.comboBox_R_channels.currentText()
        if signal_name == '':
            self.movingRtoL = False
            return
        
        time = self.plotsDataR[signal_name][0]
        amplitude = self.plotsDataR[signal_name][1]

        # Remove the signal from the right plot and legend
        plot = self.plotsR[signal_name]
        del self.plotsR[signal_name]
        del self.plotsDataR[signal_name]
        self.plotWidget_R.removeItem(plot)
        self.legend_R.removeItem(signal_name)
        self.comboBox_R_channels.removeItem(self.comboBox_R_channels.currentIndex())
        timer = self.timers_R[signal_name]
        del self.timers_R[signal_name]

        # Add the signal to the left plot and legend
        self.plotsL[signal_name] = plot
        self.plotsDataL[signal_name] = [time, amplitude]
        self.plotWidget_L.addItem(plot)
        self.legend_L.addItem(plot, signal_name)
        self.comboBox_L_channels.addItem(signal_name)
        self.timers_L[signal_name] = timer

        offset = max(self.max_offset_L, len(self.plotsL) * 10)
        self.max_offset_L += 10
        offset = self.max_offset_L
        new_amplitude = amplitude - offset
        plot.setData(time, new_amplitude)
        matching_key = [key for key, value in self.update_data_dict.items() if value["signal_name"] == signal_name]
        self.update_data_dict[matching_key[0]]["amplitude"] = new_amplitude
        self.update_data_dict[matching_key[0]]["plot"] = plot
        self.update_data_dict[matching_key[0]]["widget"] = self.plotWidget_L

        # handle timer state depending on play/pause state of the move to plot
        speed = self.horizontalSlider_L_speed.value()
        timer.setInterval(speed * 10)
        if self.isPlayingL:
            timer.start() 
        else:
            timer.stop()

    def toggleLinkGraphs(self, state):
        if state == QtCore.Qt.Checked:  # Checkbox is checked
            # self.graph1ViewBox.setXLink(self.graph2ViewBox)
            self.graph1ViewBox.setYLink(self.graph2ViewBox)
            if self.isPlayingL and not self.isPlayingR:
                self.togglePlayPauseR()
            elif not self.isPlayingL and self.isPlayingR:
                self.togglePlayPauseL()
        else:
            # Unlink the ViewBoxes if the checkbox is unchecked
            self.graph1ViewBox.setXLink(None)
            self.graph1ViewBox.setYLink(None)
            self.graph2ViewBox.setXLink(None)
            self.graph2ViewBox.setYLink(None)


    def clearTimers(self, timersDict):
        for timer in timersDict.values():
            timer.stop()
            timer = None


    def stopPlotL(self):
        if not self.checkBox_linkGraphs.isChecked():
            # self.removeFromHiddenStateDict(self.plotWidget_L)
            self.plotWidget_L.clear()
            self.legend_L.clear()
            self.plotsL.clear()
            self.comboBox_L_channels.clear()
            self.pushButton_move_plot_L.setEnabled(True)
            self.isPlayingL = True
            self.pushButton_L_playPause.setText("Pause")
            self.rewindPlotL = False
            self.rewindTimerL.stop()
            # self.rewindTimerL = None
            self.PlotsFinishedL.clear()
            self.clearTimers(self.timers_L)
        else:
            self.stopBothPlots()

    def stopPlotR(self):
        if not self.checkBox_linkGraphs.isChecked():
            # self.removeFromHiddenStateDict(self.plotWidget_R)
            self.plotWidget_R.clear()
            self.legend_R.clear()
            self.plotsR.clear()
            self.comboBox_R_channels.clear()
            self.checkBox_R_Hide.setChecked(False)
            self.pushButton_move_plot_R.setEnabled(True)
            self.isPlayingR = True
            self.pushButton_R_playPause.setText("Pause")
            self.rewindPlotR = False
            self.rewindTimerR.stop()
            # self.rewindTimerR = None
            self.PlotsFinishedR.clear()
            self.clearTimers(self.timers_R)
        else:
            self.stopBothPlots()

    def stopBothPlots(self):
            # all signals in both graphs are plotted completely and their stop buttons are enabled 
            if self.pushButton_L_stop.isEnabled() and self.pushButton_R_stop.isEnabled():
                # stop and reset graph 2
                self.plotWidget_R.clear()
                self.legend_R.clear()
                self.plotsR.clear()
                self.plotsDataR.clear()
                self.comboBox_R_channels.clear()
                self.checkBox_R_Hide.setChecked(False)
                self.pushButton_move_plot_R.setEnabled(True)
                self.isPlayingR = True
                self.pushButton_R_playPause.setText("Pause")
                self.rewindPlotR = False
                self.rewindTimerR.stop()
                # self.rewindTimerR = None
                self.PlotsFinishedR.clear()
                self.clearTimers(self.timers_R)
                self.pushButton_R_stop.setEnabled(False)
                # stop and reset graph 1
                self.plotWidget_L.clear()
                self.legend_L.clear()
                self.plotsL.clear()
                self.plotsDataL.clear()
                self.comboBox_L_channels.clear()
                self.pushButton_move_plot_L.setEnabled(True)
                self.isPlayingL = True
                self.pushButton_L_playPause.setText("Pause")
                self.rewindPlotL = False
                self.rewindTimerL.stop()
                # self.rewindTimerL = None
                self.PlotsFinishedL.clear()
                self.clearTimers(self.timers_L)
                self.pushButton_L_stop.setEnabled(False)
            else:
                # Create a QMessageBox and display the critical error dialog
                msg_box = QtWidgets.QMessageBox()
                msg_box.setIcon(QtWidgets.QMessageBox.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText("This action is not available, You must uncheck the link checkbox first")
                msg_box.exec_()
    
    
    def export_to_pdf(self):
        self.pdf_count += 1
        doc = SimpleDocTemplate(f"BioSignal Report{self.pdf_count}.pdf",
                                pagesize=letter,
                                topMargin=0.5 * inch,
                                bottomMargin=0.5 * inch,
                                leftMargin=0.5 * inch,
                                rightMargin=0.5 * inch
                                )
        pdf_elements = []
        # Add title
        self.add_title_to_pdf(pdf_elements)
        for snapshot in self.snapshot_images_lst:
            pdf_elements.append(Image(snapshot))
            pdf_elements.append(Spacer(1, 25))
            self.pdf_table(pdf_elements, snapshot)
            pdf_elements.append(PageBreak())

        doc.build(pdf_elements)
        self.snapshot_images_lst = []

    def take_snapshot_R(self):
        # capture the widget as an image
        pixmap = QPixmap(self.plotWidget_R.size())
        painter = QPainter(pixmap)
        self.plotWidget_R.render(painter)
        painter.end()
        # Generate a unique filename for the snapshot image
        img_filename = f"snapshot_R{len(self.snapshot_images_lst)}.png"
        # Save the pixmap as an image file
        pixmap.save(img_filename, "PNG")
        # Add the image path to the list of snapshots
        self.snapshot_images_lst.append(img_filename)

    def take_snapshot_L(self):
        # capture the widget as an image
        pixmap = QPixmap(self.plotWidget_L.size())
        painter = QPainter(pixmap)
        self.plotWidget_L.render(painter)
        painter.end()
        # Generate a unique filename for the snapshot image
        img_filename = f"snapshot_L{len(self.snapshot_images_lst)}.png"
        # Save the pixmap as an image file
        pixmap.save(img_filename, "PNG")
        # Add the image path to the list of snapshots
        self.snapshot_images_lst.append(img_filename)

    def add_title_to_pdf(self, elements):
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=24,
            fontName='Helvetica-Bold',
            alignment=1,
        )
        # Add logos and title to the elements
        logo1 = Image(
            os.path.abspath(r'Eng logo1.png'),
            width=1.5 * inch, height=1 * inch)
        logo2 = Image(
            os.path.abspath(r'SBME logo.png'),
            width=1.5 * inch, height=1 * inch)
        title = Paragraph("Patient Biosignals Analysis and Statistical Summary", title_style)

        table_data = [[logo1, title, logo2]]
        col_widths = [1.5 * inch, 4.5 * inch, 1.5 * inch]
        row_heights = [1 * inch]  # Adjust the row height as needed to center vertically
        table_style = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]  # Center all cells vertically

        table = Table(table_data, colWidths=col_widths, rowHeights=row_heights, style=table_style)

        elements.append(table)
        # elements.append(title)
        elements.append(Spacer(1, 50))

    def calc_statistics(self, img_filename):
        heading = ['']
        means = ["Mean"]
        stds = ["Standard Deviation"]
        maxs = ["Max"]
        mins = ["Min"]
        durations = ["Duration"]

        if 'R' in img_filename:
            for key in self.plotsDataR.keys():
                heading.append(key)
            for data in self.plotsDataR.values():
                means.append(round(statistics.mean(data[1]), 3))
                stds.append(round(statistics.stdev(data[1]), 3))
                maxs.append(round(max(data[1]), 3))
                mins.append(round(min(data[1]), 3))
                durations.append(round(max(data[0]), 3))
        else:
            for key in self.plotsDataL.keys():
                heading.append(key)
            for data in self.plotsDataL.values():
                means.append(round(statistics.mean(data[1]), 3))
                stds.append(round(statistics.stdev(data[1]), 3))
                maxs.append(round(max(data[1]), 3))
                mins.append(round(min(data[1]), 3))
                durations.append(round(max(data[0]), 3))

        table_data = [heading, means, stds, maxs, mins, durations]
        return table_data

    def pdf_table(self, elements, file_name):
        table_data = self.calc_statistics(file_name)
        # Calculate the width of each column based on the page width and the number of columns
        page_width, _ = letter  # Get the width of the page
        left_right_margins = 2.5 * inch
        table_width = page_width - (3 * left_right_margins)
        num_cols = len(table_data[0])
        num_rows = len(table_data)
        # table_width = num_cols
        # column_width = table_width / num_cols
        if num_cols <= 6:
            column_width = [130] + [80] * (num_cols - 1)
        elif num_cols <= 9:
            column_width = [130] + [60] * (num_cols - 1)
        else:
            table_data[2][0] = 'STD'
            table_data[0][1:] = [str(sig_count) for sig_count in range(len(table_data[0]))]
            column_width = [60] + [50] * (num_cols - 1)

        table = Table(table_data, colWidths=column_width, rowHeights=[30] * num_rows)
        # table = Table(table_data, colWidths=[150] * num_cols, rowHeights=[30] * num_rows)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
        ]))
        elements.append(table)
        # return table
    
    




    

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())
