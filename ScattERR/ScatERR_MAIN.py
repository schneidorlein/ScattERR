# -*- coding: utf-8 -*-
"""
Created on Tue Feb  9 21:53:21 2021

@author: Acer
"""

#from Backend.UI.Positioning_Assistant_GUI5 import Ui_Mouse_Positioning_Interface


from PyQt5.QtWidgets import QApplication as Qapp
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QMainWindow as QMain
from PyQt5 import QtCore
from PyQt5 import QtGui

pyqt_version = 5

from interface import Ui_MainWindow
from PyQt5.QtWidgets import QFileDialog as Qfile
from PyQt5.QtWidgets import QMessageBox as QMessage



import logging
import sys
import os
import numpy as np
import time
import threading
import serial
import configparser
import glob
import ctypes
import re

from Backend.lynxReaderMalte import Lynx

import PyQt5.QtWidgets as QtWidgets









"""
*******************************************************************************
Motor Control
*******************************************************************************
"""





class MotorControl(object):
    """ This class holds holds all basic functionality to control the
        motorized linear axes. """

    def __init__(self, GUI=None):

        # Variables
        self.pos = []  # Unit: mm
        self.Step2MM = np.array([1E4, 1E4, 0.5E5])

        # IDs of PS10 elements in bus
#        self.MasterID = None
#        self.SlaveID = None
        self.slaves = []

        self.ctrl = serial.Serial()

        # Set default logging of serial communication to false
        self.verbose = False
        
        self.GUI = GUI
        self.mode = 'absolute'
        self.limits =[210, 210, 12]

        # First: Find available COM ports and add to ComboBox
        self.ScanCOMPorts()
       

    def ScanCOMPorts(self):
        """Scans list of COM ports and adds to List of Ports in GUI"""
        self.portlist = self.get_serial_ports()         


    def moveTable(self, vector=[0, 0, 0]):
        """
        Basic executer function to move table by/to selected value
        """
        vector=np.asarray(vector)

        try:
            if self.GUI is not None:
                val = np.array((self.GUI.SpinBoxTablex.value(),
                                self.GUI.SpinBoxTabley.value()))
            else:
                val = vector

            # get current position
            curpos = self.get_Position()


            if self.mode == 'absolute':
                dest = val
            elif self.mode == 'relative':
                dest = curpos + val

                
            # convert to motor steps
            dest = np.multiply(self.Step2MM, dest)  # convert to motor steps        


            # write to Axis
            for i,slaves in enumerate(self.slaves):
                self.serial_write(slaves, 1, 'PSET', dest[i])  # Watch out here: Depends on cable connections!!!!
                self.serial_write(slaves, 1, 'PGO')
                

        except Exception:
            print()
        


    def get_Position(self):
        " get current position of selected axis via USB"

        # Watch out here: y@ Master and x@SLave!
        # may be different in other beamtimes!!!
        x = float(self.serial_query(self.slaves[0], 1, 'CNT'))/self.Step2MM[0]
        y = float(self.serial_query(self.slaves[1],  1, 'CNT'))/self.Step2MM[1]
        z = float(self.serial_query(self.slaves[2],  1, 'CNT'))/self.Step2MM[2]

        return np.array((x, y, z))


    def setPositioningMode(self):
        """When Mode in absolute/relative combo box changes, write to motor"""

        for slave in self.slaves:
            if self.mode == 'absolute':
                self.serial_write(slave, 1, 'ABSOL')
            elif self.mode == 'relative':
                self.serial_write(slave, 1, 'RELAT')
            



    # Initialization
    def InitMotor(self):
        """
        function that executes everything that is necessary to initialize
        the motor
        """

        port = 'COM6'
        self.InitializeCOM(port)


        # Find Slaves
        self.find_slaves(10)

        # Next: set all motorvalues
        for slave in self.slaves:
            self.config_motor(slave)
            self.serial_write(slave, 1, 'INIT')
            print(self.serial_query(slave,  1, 'ASTAT'))
            
        self.setPositioningMode()
        self.Calibrate_Motor()
        
        logging.info('Scatterer are calibrated and sit in parking position.')



    def Calibrate_Motor(self):
        """execute reference run of object table"""

        # Ask User if calibration is desired
        Hint = QMessage()
        Hint.setIcon(QMessage.Information)
        Hint.setStandardButtons(QMessage.Ok)
        Hint.setText("Calibration starts now!")
        proceed = Hint.exec_()

        # Execute Calib
        if proceed == QMessage.Ok:
            for slave in self.slaves:
                self.serial_write(slave, 1, 'REF', 4)
            
        #logging.info('Table calibration running.')

    def on_calib(self, flag):
        "gets called when reference motion is finished"
        if flag is True:
            GUI.BoxTableLimits.setStyleSheet("background-color: green;")
            GUI.LabelREF.setText('Calibrated')

    # basic communication stuff
    def serial_write(self, slaveID, nAxis, command, value=''):
        """ will format and send the given command through the COM port.
            -- command: serial command to be sent.
        """

        # write request to COM
        if value == '':
            command = ("{:02d}{:s}{:d}\r\n".format(slaveID, command, nAxis))
        else:
            command = ("{:02d}{:s}{:d}={:s}\r\n"
                       .format(slaveID, command, nAxis, str(value)))

        command = command.encode(encoding="ASCII")

        self.ctrl.write(command)

        # Read answer from COM and print full command  + reply
        asw = (self.ctrl.read(1024)).decode()

        return asw


    def serial_query(self, slaveID, nAxis, request):
        """ will format and send the given query through the COM port.
            -- command: serial command to be sent.
        """

        if slaveID is None or nAxis is None:
            return 0

        # write request to COM
        request =  ("{:02d}?{:s}{:d}\r\n".format(slaveID, request, nAxis))
        request = request.encode(encoding="ASCII")
        #if self.verbose: logging.debug(request)
        self.ctrl.write(request)

        # Read answer from COM and return
        asw = (self.ctrl.read(1024)).decode()
        return asw


    def config_motor(self, slaveID, filename = os.path.join(os.getcwd(), 'owis.ini')):
        """configures motor parameters of owis axis based oon data in given
            .ini file
            -- filename: full path of .ini containing necessary information
            -- slaveID: slaveID of motor the settings of which should be written
            """

        # read config file
        config = configparser.RawConfigParser()
        config.read(filename)


        #write values to axis
        self.serial_write(slaveID, 1, 'SMK',       config.get('MOTOR', 'SMK'))
        self.serial_write(slaveID, 1, 'SMK',       config.get('MOTOR', 'SMK'))
        self.serial_write(slaveID, 1, 'SPL',       config.get('MOTOR', 'SPL'))
        self.serial_write(slaveID, 1, 'RMK',       config.get('MOTOR', 'RMK'))
        self.serial_write(slaveID, 1, 'RPL',       config.get('MOTOR', 'RPL'))
        self.serial_write(slaveID, 1, 'RVELF',     config.get('MOTOR', 'RVELF'))
        self.serial_write(slaveID, 1, 'RVELS',     config.get('MOTOR', 'RVELS'))
        self.serial_write(slaveID, 1, 'ACC',       config.get('MOTOR', 'ACC'))
        self.serial_write(slaveID, 1, 'PVEL',      config.get('MOTOR', 'PVEL'))
        self.serial_write(slaveID, 1, 'FVEL',      config.get('MOTOR', 'FVEL'))
        self.serial_write(slaveID, 1, 'PHINTIM',   config.get('MOTOR', 'PHINTIM'))
        self.serial_write(slaveID, 1, 'MCSTP',     config.get('MOTOR', 'MCSTP'))
        self.serial_write(slaveID, 1, 'DRICUR',    config.get('MOTOR', 'DRICUR'))
        self.serial_write(slaveID, 1, 'HOLCUR',    config.get('MOTOR', 'HOLCUR'))
        self.serial_write(slaveID, 1, 'ATOT',      config.get('MOTOR', 'ATOT'))
        self.serial_write(slaveID, 1, 'MOTYPE',    config.get('MOTOR', 'MOTYPE'))
        self.serial_write(slaveID, 1, 'MAXOUT',    config.get('MOTOR', 'MAXOUT'))
        self.serial_write(slaveID, 1, 'AMPSHNT',   config.get('MOTOR', 'AMPSHNT'))
        self.serial_write(slaveID, 1, 'AMPPWMF',   config.get('MOTOR', 'AMPPWMF'))
        self.serial_write(slaveID, 1, 'ABSOL')  # default setting: absolute positioning


    def find_slaves(self, Range):
        """sends a testmessage to all slaves in range 0 to Range and listens
            for an answer. """

        self.MasterID = 0  # MasterID is always 00 - right?
        # check if serial port is open
        if not self.ctrl.is_open:
            return -1

        # Otherwise, browse all slaveIDs in given range
        for I in range(1, Range):
            asw = self.serial_query(I, 1, 'ASTAT') # request status
            time.sleep(1)

            # check if an answer came
            if asw == '':
                if I == Range -1:
                    # If maximum number of IDs have been checked, throw error
                    #logging.error('No Master/Slave structure found')
                    return -1
                else:
                    continue

            # If reply comes:
            else:
                # break loop
                self.slaves.append(I)
                #logging.debug('Found Slave at ID={:d}'.format(I))

        try:
            self.StatusWatchDog.MID = self.MasterID
            self.StatusWatchDog.SID = self.SlaveID
        except Exception:
            pass



    def get_serial_ports(self):

        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """

        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result


    def InitializeCOM(self, port, baudrate = 9600, bytesize = serial.EIGHTBITS,
                      parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                      rtscts=False, xonxoff=True, timeout=0.05, writeTimeout=0.05):

        """Function to initialize the serial communication
            - port: Set COM-Port that is connected to the OWIS components
            - all other necessary parameters are default parameters
        """
        #logging.debug('Trying to open serial connection.')
        self.ctrl.port          = port
        self.ctrl.baudrate      = baudrate
        self.ctrl.bytesize      = bytesize
        self.ctrl.parity        = parity
        self.ctrl.stopbits      = stopbits
        self.ctrl.rtscts        = rtscts
        self.ctrl.xonxoff       = xonxoff
        self.ctrl.timeout       = timeout
        self.ctrl.writeTimeout  = writeTimeout

        try:
            self.ctrl.open()
        except Exception:
            return -1
        
        
        
        
    def get_tablestatus(self):
        
        GUI.enable_buttons(False)
        
        t = threading.Timer(1, self.get_tablestatus)
        t.start()
            
        MID = 1
        SID2 = 2
        SID3 = 3
        self.MState = self.serial_query(MID, 1, 'ASTAT')[0]
        self.SState2 = self.serial_query(SID2, 1, 'ASTAT')[0]
        self.SState3 = self.serial_query(SID3, 1, 'ASTAT')[0]
            
            
            
        #if self.MState == 'T' or self.SState2 == 'T' or self.SState3 == 'T':
        cur_pos = self.get_Position()
        
        GUI.edit_s1_cur_x.setText('{:4.2f}'.format(cur_pos[1])) #s1h
        GUI.edit_s2_cur_x.setText('{:4.2f}'.format(cur_pos[0]))
        GUI.edit_s2_cur_y.setText('{:4.2f}'.format(cur_pos[2]))
                
        
        if self.MState == 'R' and self.SState2 == 'R' and self.SState3 == 'R':
            #print('motor stopped')
            t.cancel()
            GUI.enable_buttons(True)
            



"""
*******************************************************************************
Main Window
*******************************************************************************
"""
class MainWindow(QMain, Ui_MainWindow):
    """
      Initialisierung Graphischer Benutzeroberfläche
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.corr = []
        #Initialize GUI and load stylesheet
        self.setupUi(self)

        # park and beam buttons
        # Set up Combo box for positioning mode and connect
          
        self.CBoxPARKBEAM_s1.addItem('PARK')
        self.CBoxPARKBEAM_s1.addItem('BEAM')
    
        self.CBoxPARKBEAM_s1.currentIndexChanged.connect(self.parkposition_s1)
        self.CBoxPARKBEAM_s1.currentIndexChanged.connect(self.beamposition_s1)
        
        
        self.CBoxPARKBEAM_s2.addItem('PARK')
        self.CBoxPARKBEAM_s2.addItem('BEAM')
        
        self.CBoxPARKBEAM_s2.currentIndexChanged.connect(self.parkposition_s2)
        self.CBoxPARKBEAM_s2.currentIndexChanged.connect(self.beamposition_s2)
        
        #adjust button
        self.button_s2_adjust.clicked.connect(self.adjust_s2)
        
        #in vivo/vitro buttons
        self.button_in_vivo.clicked.connect(self.vivoposition)
        self.button_in_vitro.clicked.connect(self.vitroposition)
        
        # button for manual movement
        self.Button_MoveTable.clicked.connect(self.manual_move)

        # button to load dcm image
        self.button_load_dcm_image.clicked.connect(self.load_Image)      
        
    
    def enable_buttons(self, enable):
        # disables every button when scatterer is moving and enables when standing still
        self.CBoxPARKBEAM_s1.setEnabled(enable)
        self.CBoxPARKBEAM_s2.setEnabled(enable)
        self.button_s2_adjust.setEnabled(enable)
        self.button_in_vivo.setEnabled(enable)
        self.button_in_vitro.setEnabled(enable)
        self.Button_MoveTable.setEnabled(enable)
        self.button_load_dcm_image.setEnabled(enable)
        
        
    
    def parkposition_s1(self):
        
        position = GUI.CBoxPARKBEAM_s1.currentText()
        self.SState2 = Motor.serial_query(2, 1, 'ASTAT')[0]
        if position == 'PARK':
            if self.SState2 == 'R':
                Motor.mode = 'absolute'
                pos = Motor.get_Position()
                target = [pos[0], 0, pos[2]]
                #print target coordinates
                self.target_coordinates(target)
                #move table to target destination
                Motor.moveTable(vector=target)
                #get current coordinates
                Motor.get_tablestatus()
                
                logging.info('\'Park\' option for 1st scatterer chosen. Scatterer is now moving to parking position. Scatterer position: x_s1 = {} mm,'
                     'x_s2 = {} mm, y_s2 = {} mm'.format(target[1], target[0], target[2]))
                        
       

    def beamposition_s1(self):
        """ 6. nut == 180 mm
        """
        
        position = GUI.CBoxPARKBEAM_s1.currentText()
        self.SState2 = Motor.serial_query(2, 1, 'ASTAT')[0]
        if position == 'BEAM':
             if self.SState2 == 'R':
                Motor.mode = 'absolute'
                pos = Motor.get_Position()
                target = [pos[0], 181, pos[2]]
                #print target coordinates
                self.target_coordinates(target)
                #move table to target destination
                Motor.moveTable(vector=target)
                #get current coordinates
                Motor.get_tablestatus()
                
                logging.info('\'Beam\' option for 1st scatterer chosen. Scatterer is now moving to beam position. Scatterer position: x_s1 = {} mm,'
                     'x_s2 = {} mm, y_s2 = {} mm'.format(target[1], target[0], target[2]))
        
        
        
    def parkposition_s2(self):
        position = GUI.CBoxPARKBEAM_s2.currentText()
        self.MState = Motor.serial_query(1, 1, 'ASTAT')[0]
        self.SState3 = Motor.serial_query(3, 1, 'ASTAT')[0]
        if position == 'PARK':
            if self.MState == 'R' and self.SState3 == 'R':
                Motor.mode = 'absolute'
                pos = Motor.get_Position()
                target = [0, pos[1], 0]
                #print target coordinates
                self.target_coordinates(target)
                #move table to target destination
                Motor.moveTable(vector=target)
                #get current coordinates
                Motor.get_tablestatus()
                
                logging.info('\'Park\' option for 2nd scatterer chosen. Scatterer is now moving to parking position. Scatterer position: x_s1 = {} mm,'
                     'x_s2 = {} mm, y_s2 = {} mm'.format(target[1], target[0], target[2]))
            
        
    def beamposition_s2(self):
        """ horizontal: 6. nut == 180 mm
        vertical: 6mm
        """
        position = GUI.CBoxPARKBEAM_s2.currentText()
        self.MState = Motor.serial_query(1, 1, 'ASTAT')[0]
        self.SState3 = Motor.serial_query(3, 1, 'ASTAT')[0]
        if position == 'BEAM':
            if self.MState == 'R' and self.SState3 == 'R':
                Motor.mode = 'absolute'
                pos = Motor.get_Position()
                target = [181, pos[1], 6]
                #print target coordinates
                self.target_coordinates(target)
                #move table to target destination
                Motor.moveTable(vector=target)
                #get current coordinates
                Motor.get_tablestatus()
                
                logging.info('\'Beam\' option for 2nd scatterer chosen. Scatterer is now moving to beam position. Scatterer position: x_s1 = {} mm, '
                     'x_s2 = {} mm, y_s2 = {} mm'.format(target[1], target[0], target[2]))
        
    
    def adjust_s2(self):
        Motor.mode = 'relative'
        pos = Motor.get_Position()
        target = [self.corr[0], 0, self.corr[1]]
        #print target coordinates
        log_target = pos+target
        self.target_coordinates(log_target)
        #move table to target destination
        Motor.moveTable(vector=target)     
        #get current coordinates
        Motor.get_tablestatus()         
        
        logging.info('\'Adjust\' button for 2nd scatterer pressed. Moving table by: dx = {:.2f} mm, '
                     'dy = {:.2f} mm. Scatterer position: x_s1 = {:.2f} mm, x_s2 = {:.2f} mm, y_s2 = {:.2f} mm'.format(self.corr[0], self.corr[1], log_target[1],
                     log_target[0], log_target[2]))
        
        log_text = self.LogBox.itemAt(0).widget().toPlainText()
        f= open(self.base+"/logfile.txt","w+")
        f.write(log_text)
        f.close() 
    

    def vivoposition(self):
        
        Motor.mode = 'absolute'
        target = [0, 0, 0]
        #print target coordinates
        self.target_coordinates(target)
        #change dropdown button to beam position
#        GUI.CBoxPARKBEAM_s1.setText('Beam')
        #move table to target destination
        Motor.moveTable(vector=target)
        #get current coordinates
        Motor.get_tablestatus()
        
        logging.info('\'In vivo\' button for both scatterer pressed. Scatterer are now moving to parking position. Scatterer position: x_s1 = {} mm, '
                     'x_s2 = {} mm, y_s2 = {} mm'.format(target[1], target[0], target[2]))
        
        self.CBoxPARKBEAM_s1.setCurrentIndex(0)
        self.CBoxPARKBEAM_s2.setCurrentIndex(0)
    
    def vitroposition(self):
        
        Motor.mode = 'absolute'
        target = [181, 181, 6]
        #print target coordinates
        self.target_coordinates(target)
        #move table to target destination
        Motor.moveTable(vector=target)
        #get current coordinates
        Motor.get_tablestatus()
        
        logging.info('\'In vitro\' button for both scatterer pressed. Scatterer are now moving to beam position. Scatterer position: x_s1 = {} mm, '
                     'x_s2 = {} mm, y_s2 = {} mm'.format(target[1], target[0], target[2]))

        self.CBoxPARKBEAM_s1.setCurrentIndex(1)
        self.CBoxPARKBEAM_s2.setCurrentIndex(1)

    def manual_move(self):
        Motor.mode = 'absolute'
        target = np.array((GUI.SpinBoxTablex_s2.value(),
                            GUI.SpinBoxTablex_s1.value(),
                            GUI.SpinBoxTabley_s2.value()))
        #print target coordinates
        self.target_coordinates(target)
        #move table to target destination
        Motor.moveTable(vector=target)
        #get current coordinates
        Motor.get_tablestatus()
        
        logging.info('\'Move\' button for both scatterer pressed. Scatterer are now moving to position: x_s1 = {} mm, '
                     'x_s2 = {} mm, y_s2 = {} mm'.format(target[1], target[0], target[2]))
        
        log_text = self.LogBox.itemAt(0).widget().toPlainText()
        f= open(self.base+"/logfile.txt","w+")
        f.write(log_text)
        f.close() 


    def target_coordinates(self, tar):
        
        self.edit_s1_tar_x.setText('{:4.2f}'.format(tar[1]))
        self.edit_s2_tar_x.setText('{:4.2f}'.format(tar[0]))
        self.edit_s2_tar_y.setText('{:4.2f}'.format(tar[2]))


        
    def load_Image(self):
        """
        Rule: Image is loaded and fliped upside down so that the display
        option origin=lower will result in correct display.
        If the imported image has more than two dimensions (i.e. has an
        additional layer vontaining only the overlayed brain mask),
        then one additional layer is stored in here - only one!
        """
        fname, _ = Qfile.getOpenFileName(self, 'Open file',
                                         "", "(*.dcm)")
        
        self.Lynxdata  = Lynx(fname)
        # If no file is chosen:
        if not fname:
            return 0
        
        
        #img = np.rot90(np.rot90(data.pixel_array))
        self.Display_dcm_image.canvas.axes.imshow(self.Lynxdata.dcmDat.pixel_array)
        #self.Display_dcm_image
        
        self.Display_dcm_image.canvas.axes.set_xlabel("x [mm]")
        self.Display_dcm_image.canvas.axes.set_ylabel("y [mm]", rotation='horizontal')
        self.Display_dcm_image.canvas.axes.yaxis.set_label_coords(-0.24, 1.1)
        self.Display_dcm_image.canvas.axes.xaxis.label.set_size(18)
        self.Display_dcm_image.canvas.axes.yaxis.label.set_size(18)
        self.Display_dcm_image.canvas.axes.xaxis.label.set_color('white')
        self.Display_dcm_image.canvas.axes.yaxis.label.set_color('white')
        self.Display_dcm_image.canvas.axes.tick_params(axis='x', colors='white')
        self.Display_dcm_image.canvas.axes.tick_params(axis='y', colors='white')
        self.Display_dcm_image.canvas.axes.spines['bottom'].set_color('white')
        self.Display_dcm_image.canvas.axes.spines['top'].set_color('white')
        self.Display_dcm_image.canvas.axes.spines['right'].set_color('white')
        self.Display_dcm_image.canvas.axes.spines['left'].set_color('white')
 
        self.Display_dcm_image.canvas.draw()        
        
        # create ticks for the dcm image with the right units
        xticks = self.Display_dcm_image.canvas.axes.get_xticks()
        yticks = self.Display_dcm_image.canvas.axes.get_yticks()
        
        xticklabels = [xtick/2 for xtick in xticks]
        yticklabels = [ytick/2 for ytick in yticks]
        
        self.Display_dcm_image.canvas.axes.set_xticklabels(xticklabels)
        self.Display_dcm_image.canvas.axes.set_yticklabels(yticklabels)
        
        self.Display_dcm_image.canvas.draw()
                
        self.label_dcm_image.setText(fname)
        self.slope()
        
        
        logging.info('Imported Dicom Image: {:s}'.format(fname))

        log_text = self.LogBox.itemAt(0).widget().toPlainText()
        self.base = os.path.dirname(fname)
        f= open(self.base+"/logfile.txt","w+")
        f.write(log_text)
        f.close() 
        
    def slope(self):
        
        #clear dose profiles image when loading the next dcm image
        self.Display_dose_profile_x.canvas.axes.clear()
        self.Display_dose_profile_x.canvas.draw()        
        self.Display_dose_profile_y.canvas.axes.clear()
        self.Display_dose_profile_y.canvas.draw()
        
        self.Lynxdata.autodetectRectField()
        
        axes = [self.Display_dose_profile_x.canvas.axes,
                self.Display_dose_profile_y.canvas.axes]
        
        self.corr = self.Lynxdata.get_characteristicData(axes, plot=True)
        
        self.edit_correction_x.setText('{:4.2f}'.format(self.corr[0]))
        self.edit_correction_y.setText('{:4.2f}'.format(self.corr[1]))
        
        self.Display_dose_profile_x.canvas.draw()
        self.Display_dose_profile_y.canvas.draw()
        
        


    def closeEvent(self, event):
        
        self.close()
        logging.getLogger().handlers = []
        
        print("GUI closed")

        app.quit()
        

class QTextEditLogger(logging.Handler):
    """ class that subclasses the logging Handler to forward the logging
    information to any widget of the owning object"""
    def __init__(self, parent):
        super().__init__()
        
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)


class MyDialog(object):
    def __init__(self):
        "installs everything to display propper Logger"
        
        logTextBox = QTextEditLogger(GUI)
        # You can format what is printed to text box
        logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(logTextBox)
        # You can control the logging level
        logging.getLogger().setLevel(logging.DEBUG)

        # Add the new logging box widget to the layout
        GUI.LogBox.addWidget(logTextBox.widget)

        logging.info('========== GUI STARTED ==============')
        logging.info('Propper Logger installed.')

        # Remove unnecessary logs from matlotlib
        mpl_logger = logging.getLogger('matplotlib')
        mpl_logger.setLevel(logging.WARNING)
    
   
        
if __name__=="__main__":
    
    root = os.getcwd()
    stylefile = os.path.join(root, 'Backend', 'Style', 'stylefile.qss')
    
    # check if instance of app is known to OS
    app = QCoreApplication.instance()
    if app is None:
        app = Qapp(sys.argv)
    else:
        pass
    
    # Create App-ID: Otherwise, the software's icon will not display propperly.
    appid = 'OncoRay.Preclinical.RadiAiDD'  # for TaskManager
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
    app.setWindowIcon(QtGui.QIcon('Backend/icon.jpeg'))
    
    # create interface        
    GUI = MainWindow()
    GUI.setStyleSheet(open(stylefile, "r").read())
    GUI.show()
    
    dlg=MyDialog()
    
    Motor = MotorControl()
    Motor.InitMotor()
    Motor.get_tablestatus()
    

    app.exec()