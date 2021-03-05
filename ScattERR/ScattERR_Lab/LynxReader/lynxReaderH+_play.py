 #! /usr/bin/python
# -*- coding: utf-8 -*-
""" Program to read DICOM data from the IBA Lynx device and support the 
    setup of the double scattering system"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import dicom

import colorsys, sys, csv,  copy,  time, os,  string,  argparse
import Plot
import logging as logg

import scipy.constants as cc
from scipy import interpolate

from mpl_toolkits.mplot3d import Axes3D
from scipy import optimize
Plot.load_defaults(2) #load before all pyplot operations 


class Lynx:
    """Central class representing the measurement from the Lynx device"""
    def __init__(self, filename):
        
        self.filename = os.path.expanduser(filename)                 # get rid of '~' in filename
        self.path = os.path.dirname(self.filename)                   # path to data
        self.filenameBare = os.path.splitext(self.filename)[0]       # filename without suffix
        
        self.protonEnergy = 0
        self.measDepth = 0
        self.measMaterial = ""
        self.comment = ""
        self.fileOK = False
        self.dataOK = False
        
        
        self.xrange = [-np.inf,  np.inf]
        self.yrange = [-np.inf, np.inf]
        
        if not(os.access(self.filename, os.R_OK)):
            print ("ERR: Could not access {0:s} for reading!".format(filename))
            return
        else:
            self.fileOK = True
        
        if  os.path.splitext(filename)[1] == ".dcm":
            print ("INFO: {0:s} seems to be a dicom file ... trying to read".format(os.path.basename(filename)))
      
            self.read_lynxDicom()
      
        
        
        
    def set_xrange(self,low, high):
        """ Set the area of interest, only rectangular ROIs are supported, 
            provide low and high x value
        """
           
        if low > high:  low, high = high, low   # switch variables if provided in the wrong order
        self.xrange[0] = low
        self.xrange[1] = high
    
    def set_yrange(self,low, high):
        """ Set the area of interest, only rectangular ROIs are supported, 
            provide low and high y value
        """
            
        if low > high:  low, high = high, low   # switch variables if provided in the wrong order
        self.yrange[0] = low
        self.yrange[1] = high

    def read_lynxDicom(self):
        """ Import function to actually read the dicom file, 
            uses the filename, which was provided during initialization of the 
            Lynx object.
            Requires a proper installed pydicom package. 
            If you are using Python3, you might be interested in the module 2to3
            to convert pydicom for Pythton 2.7 to Python3
        """
        if not self.fileOK: 
            print ("ERR: Object not initialized (no access to file {0:s}".format(self.filename))
            return
        self.dcmDat = dicom.read_file(self.filename)
        
        self.xsc = float(self.dcmDat.RTImagePosition[0]) + np.arange(0, self.dcmDat.Rows)*float(self.dcmDat.PixelSpacing[0])
        self.ysc = float(self.dcmDat.RTImagePosition[1]) + np.arange(0, self.dcmDat.Columns)*float(self.dcmDat.PixelSpacing[1])

        
        data = self.dcmDat.pixel_array
        data = data.astype("float")
        
        data = np.fliplr(data)
        self.data = data
        
        print ("Importet a matrix of {0:d}x{1:d} from {2:s}".format(self.dcmDat.Rows,self.dcmDat.Columns,  self.filename  ))
        
        self.metaData_fromFilename()
        self.dataOK = True
        
        return
        
        
    def getSelectionData(self,  normaxes = True):
        """ Returns the rectangular area of interest,
            and scaling vectors in x and y direction:
                data, xsc, ysc
            if normaxes is True, the scaling vectors will start with 0
        """
        
        if not self.dataOK:
            print ("ERR: No data in object. Please use read_lynxDicom()")
            return 
        
        xInd = [np.min(np.where(self.xsc > self.xrange[0])), np.max(np.where(self.xsc < self.xrange[1]))]
        yInd = [np.min(np.where(self.ysc > self.yrange[0])), np.max(np.where(self.ysc < self.yrange[1]))]
        
        xsc = copy.deepcopy(self.xsc[xInd[0]:xInd[1]] )
        ysc = copy.deepcopy( self.ysc[yInd[0]:yInd[1]])
        
        data = copy.deepcopy(self.data[yInd[0]:yInd[1], xInd[0]:xInd[1]])
       
        if normaxes:
            xsc -= xsc[0]
            xsc -= xsc[-1] / 2.
            ysc -= ysc[0]
            ysc -= ysc[-1] / 2.
        
        
        return data,  xsc,  ysc
        
    def getFieldSize(self,  threshold = 0.90,  plot = True):
         """ Returns the area of the field with a value > threshold
            Provide the threshold.
            If plot is True, an image with the result will be shown
            """
         data, xsc, ysc = self.getSelectionData()
         
         data /= np.max(data)
         
         pixelSize = (xsc[1]-xsc[0]) * (ysc[1]-ysc[0])
         
         fieldSize = np.sum(data >  threshold) * pixelSize
         
         if plot:
            fig = plt.figure(figsize=(8, 6), dpi=80)
            ax = plt.subplot(111)
            im = ax.imshow(data >  threshold, extent = [xsc[0], xsc[-1], ysc[0], ysc[-1]],  cmap=plt.cm.gnuplot2,  origin = "lower")
        
            plt.colorbar(im,  label = "Intensity")
        
            plt.show()
         
         print ("FIELD SIZE:")
         print ("pixel size = {0:.2f} mm^2".format(pixelSize))
         print ("field size = {0:.2f}".format(fieldSize))
         
        
    def plot(self,  clim = [0., 1.],  deltaMean  =False,  normaxes = True,  savefig = True):
        """ Plot function,
            clim: relative thresholds for data to be plotted
            normaxes: axes will start with 0
            deltaMean: ifTrue: normalize data to mean (else: norm to maximum)
        """

        data, xsc, ysc = self.getSelectionData(normaxes = normaxes)
        
        if deltaMean:
            data = (data - np.nanmean(data)) / np.nanmean(data)
        
            cmap = plt.cm.seismic
        else:
            data /= np.max(data)
            cmap = plt.cm.gnuplot2
        data [data < clim[0]] = clim[0]
        data [data > clim[1]] = clim[1]
        dataRange = clim[1]-clim[0]
        imgMax = np.max(data)


        # HACK AL 2017-02-24
        cmap = 'Greys'
        data = data - .7
        data /= np.max(data) * 0.9
  #      data [data < 0.15] = clim[0]
  #      data /= np.max(data)
  #      data [data > 0.95] = clim[1]
        #data /= np.max(data)
        #data = 1. - data
  #      data /= np.max(data) 
  #      imgMax = np.max(data)

        # END HACK
        
        # customize the colormap
        finingFactor = 1
        bounds =np.concatenate([np.linspace(0.03*dataRange + clim[0] , 0.5*dataRange + clim[0], 100*finingFactor),  
                                np.linspace(0.5*dataRange + clim[0], 1*dataRange + clim [0], 100)])
        norm = colors.BoundaryNorm(boundaries=bounds, ncolors=256)
        
        fig = plt.figure(figsize=(8, 6), dpi=80)
        ax = plt.subplot(111)
      
        im = ax.imshow(data, extent = [xsc[0], xsc[-1], ysc[0], ysc[-1]], 
             cmap=cmap,  origin = "lower",  norm = norm)
        ax.set_xlabel("x / mm")
        ax.set_ylabel("y / mm")

        
        plt.colorbar(im,  label = "relative dose")
        
        plt.show()
        
        # All images will be saved per default
        if savefig:
            filename = self.filenameBare+"2D_x_{0:.2f}_{1:.2f}_y_{2:.2f}_{3:.2f}".format(xsc[0], xsc[-1], ysc[0], ysc[-1])
        
            fig.savefig(filename+".pdf",  dpi=80, facecolor='w', edgecolor='w',
                        orientation='portrait', papertype=None, format=None,
                        transparent=False, bbox_inches='tight', pad_inches=0.03,
                        frameon=False)
            fig.savefig(filename+".svg",  dpi=80, facecolor='w', edgecolor='w',
                        orientation='portrait', papertype=None, format=None,
                        transparent=False, bbox_inches='tight', pad_inches=0.03,
                        frameon=False)
                    
       
    def positionMax(self):
        """ 
        Function that finds the x-y coordinates of the maximum
        and prints them to the screen.           
        """

        data, xsc, ysc = self.getSelectionData(normaxes = normaxes)
           

        dataShape = data.shape
        posMax = np.argmax(data)
        posMax = np.unravel_index(posMax,dataShape)
        
        posMaxX = (posMax[1]+0.5 -(dataShape[1])/2.)/2.
        posMaxY = (np.unravel_index(np.argmax(data),(599,599))[0] - 299.)/2.
        posMaxY = (posMax[0]+0.5 - (dataShape[0])/2.)/2.

        print ("Position of maximum")
        print ("  x   y ")
        print (posMaxX,posMaxY)
        
        
    def autodetectRectField(self,  threshold = 0.3):
        print ("Trying to autodetect the rectangular field")
        data,  xsc,  ysc = self.getSelectionData(normaxes = True)
        
        doseOfX = np.sum(data, axis = 0)
        doseOfY = np.sum(data, axis = 1)
        
        x = np.zeros(2)
        y = np.zeros(2)
        x[0] = xsc[np.min(np.where(doseOfX >= threshold* np.max(doseOfX)))]
        x[1] = xsc[np.max(np.where(doseOfX >= threshold* np.max(doseOfX)))]
        
        y[0] = ysc[ np.min(np.where(doseOfY >= threshold* np.max(doseOfY)))]
        y[1] = ysc[ np.max(np.where(doseOfY >= threshold* np.max(doseOfY)))]
        
        print ("Detected at a threshold of {0:.2f}: ".format(threshold))
        print ("    x: {0:.2f} ... {1:.2f}".format(x[0], x[1]))
        print ("    y: {0:.2f} ... {1:.2f}".format(y[0], y[1]))
        print ("Use option --roiLimit to set the threshold")
        
        a.set_xrange(x[0], x[1])
        a.set_yrange(y[0], y[1])


        
    def eval2DFlatness(self, desiredFieldWidth = 100,  tolerance = 2.,  plot = False):
        """ Evaluate the dose distribution to get flat dose 
            tolerance: maximum allowed relative deviation from 100%
            desiredFieldWidth: field width in which the evaluation is carried out
        
        """
        #  -- get relevant data --
        data,  xsc,  ysc = self.getSelectionData(normaxes = True)
        data /= np.max(data)

        # -- determine plateau's indices --
        doseOfX = np.sum(data, axis = 0)
        doseOfY = np.sum(data, axis = 1)
       
        xSpacing = xsc[1] -xsc [0]
        ySpacing = ysc[1] -ysc [0]
        
        pxInd,  W50,  W90 = self.get_plateauIndices(xsc, doseOfX,  desiredFieldWidth = desiredFieldWidth/xSpacing)
        pyInd,  W50,  W90 = self.get_plateauIndices(ysc, doseOfY,  desiredFieldWidth = desiredFieldWidth/ySpacing)
        
        #  -- prepare dose for further calculations -- 
        doseSelect = data[   pyInd[0]:pyInd[1], pxInd[0]:pxInd[1]]
        doseSelect /= np.mean(doseSelect)
        doseSelect *= 100.
        xx, yy = np.meshgrid( xsc[pxInd[0]:pxInd[1]],  ysc[pyInd[0]:pyInd[1]])
        
        
        # -- fit a plane to the dose -- 
        p0 = [0., 0.0, 1., 1.]
        fitfunc = lambda p,   xx,  yy,  dose: \
            np.sum((p[0]*xx + p[1]*yy + p[2]*dose - p[3])**2)
        
        doseFunc = lambda p, xx, yy:\
            (p[3]- p[0]*xx - p[1]*yy) / p[2]
    
        res = optimize.minimize(fitfunc,  p0 ,args=(xx, yy,  doseSelect),method='SLSQP' )
       
        normalVector = res.x[0:3] / np.sum(np.abs(res.x[0:3])  )
        distanceToOrigin = res.x[3] / np.sum(np.abs(res.x[0:3])  )
        theta = np.degrees(np.arccos ( normalVector[2] / np.sqrt((np.sum([normalVector[0]**2, normalVector[1]**2, normalVector[2]**2])))))
        phi = np.degrees(np.arctan2(normalVector[1], normalVector[0]))
        print ("Normal vector = ({0:.4f},{1:.4f},{2:.4f})".format(*normalVector))
        print ("theta = {0:.4f}, phi = {1:.4f}".format(theta,  phi))
        print ("Distance to origin = {0:.2f}".format(distanceToOrigin))
        


    
            

        # -- plot the fitting procedure and the corrected dose map
       
        doseFit = doseFunc (res.x, xx, yy)
        doseCorr = doseSelect - doseFit 
        
        # -- apply a quality criterion
        
        qualityMatrix = np.ones(np.prod(doseCorr.shape)).reshape(*doseCorr.shape)
        qualityMatrix[(doseCorr <= (tolerance /100.))*(doseCorr >= (-tolerance /100.))] = 0
        nElem = np.prod(qualityMatrix.shape)
        passRate = (nElem-np.sum(qualityMatrix))/float(nElem)
        print ("Quality evaluation:")
        print ("  Tolerance level: {0:.2f} %".format(tolerance))
        print ("  Pass: {0:.0f} of {1:.0f}: {2:.0f} %".format(nElem - np.sum(qualityMatrix), nElem, passRate*100.))

        # -- make a nice little pictue --
        if plot:
            fig = plt.figure(figsize=(15, 6), dpi=80)
            ax = plt.subplot(131, projection='3d')
            im = ax.plot_surface(xx, yy,      doseSelect, alpha = 0.5)
            im = ax.plot_surface(xx, yy,      doseFit,   color = "r",  alpha = 0.5)
            ax.set_xlabel("x / mm")
            ax.set_ylabel("y / mm")
          #  ax.set_title("x = {0:.2f}".format(xsc[xMid]))
          
        
            ax = plt.subplot(132, projection='3d')
            im = ax.plot_surface(xx, yy,      doseCorr , alpha = 0.5)
         
            ax.set_xlabel("x / mm")
            ax.set_ylabel("y / mm")
           
            
            
            ax = plt.subplot(133)
            im = ax.imshow(doseCorr)
         
            ax.set_xlabel("x / mm")
            ax.set_ylabel("y / mm")
            plt.colorbar(im)
            
            plt.show()
        return [self.protonEnergy,  self.measDepth, passRate,  theta,  phi]
   
  
    def plot_centralProfile(self):
        """ Plot profiles through the center of the area of interest
        """
        
        data, xsc, ysc = self.getSelectionData()

        xMid = int(len(xsc) /2)
        yMid = int(len(ysc) /2)
     
        
        data /= np.max(data)
       
      
        fig = plt.figure(figsize=(10, 6), dpi=80)

        ax = plt.subplot(121)
        pl1 = ax.plot(ysc, data [:, xMid])
        ax.set_xlabel("y / mm")
        ax.set_ylabel("D")
        ax.set_title("x = {0:.2f}".format(xsc[xMid]))
        
        
        ax = plt.subplot(122)
        pl1 = ax.plot(xsc, data [yMid,:])
        ax.set_xlabel("x / mm")
        ax.set_ylabel("D")
        ax.set_title("y = {0:.2f}".format(ysc[yMid]))
        plt.show()
        
    
    def get_plateauIndices(self, xx,  dose,  desiredFieldWidth = 0):
        """ Get the indices of the plateau, according to the desired field   
            size (if != 0) or the classic definition
            Returns:
                indices: array (2)
                actual W50 of field
                actual W90 of field
            """
        dose /= np.max(dose)
        W50Li = np.min(np.where(dose > 0.5))
        W50Ri = np.max(np.where(dose > 0.5))
        W50 = xx [W50Ri] - xx [W50Li]
        W90 = xx [np.max(np.where(dose > 0.9))] - xx [np.min(np.where(dose > 0.9))]
            
            
        if desiredFieldWidth == 0:
            # classsic definition of uniformity region
            fallOffLi =  np.min(np.where(dose > 0.8)) - np.min(np.where(dose > 0.2))
            fallOffRi = - np.min(np.where(dose > 0.8))+  np.min(np.where(dose > 0.2))
            fallOffi = np.mean([fallOffLi, fallOffRi])
            plateauInd = [round(W50Li + 2* fallOffi),round(W50Ri - 2* fallOffi) ]
            
        else:
            # definition of uniformity region for desired field
                
            plateauInd = [ round(W50Li + (W50Ri - W50Li)/2. - desiredFieldWidth/2.), 
                             round(W50Li + (W50Ri - W50Li)/2. + desiredFieldWidth/2.)]            
        
        return plateauInd,  W50,  W90

    def calculate_CorrectionVector(self,  tX, tY,  px = [-1.88e-6, -2.37e-7,  6.67e-4,  1.02e-4], 
                                                   py = [1.61e-7, -1.90e-5,  6.75e-4,  3.66e-5], 
                                                  # py = [-1.34e-6, 2.01e-6,  6.36e-4,  -3.99e-4], 
                                                   plotcurve = False):
        """ Calculate the correction vector for the second
            scatterer of the EXPONAT0 system, according to the
            BA Thesis of L. Schreiner, p 22
            tX: tilt of dose distribution in x direction
            tY: tilt of dose distribution in y direction
            
            returns: translation in x and y direction
        """
    
        # define the parameters here
        x = np.linspace(-10., 10., 1000)
        y = np.linspace(-10., 10., 1000)
        
        tiltX = px[0]*x**3 + px[1]*x**2 + px[2]*x**1 + px[3]
        tiltY = px[0]*x**3 + py[1]*x**2 + py[2]*y**1 + py[3]
        
        x0 = x [np.where(np.abs(tiltX -tX) == np.min(np.abs(tiltX -tX)))][0]
        y0 = y [np.where(np.abs(tiltY -tY) == np.min(np.abs(tiltY -tY)))][0]
        
        if plotcurve:
            fig = plt.figure(figsize=(20, 10), dpi=80)
            ax = plt.subplot(111) 
            ax.plot(x, tiltX)
            plt.show()

        return x0,  y0
        
        
    def get_characteristicData(self, desiredFieldWidth = 100,  outFile = None, plot = False):
        """
            Function to get the following parameters from the distribution:
                W50, W90, flatness, plateau tilt, correction of second scatterer
            outFile: file handle to write the data, open and close it yourself!
            
            returns  out[0], out[1]
                     structures containing the calculated parameters
        """
        
        
        data, xsc, ysc = self.getSelectionData()
        xMid = int(len(xsc) /2)
        yMid = int(len(ysc) /2)
        data /= np.max(data)
        
        
        if plot:
            fig = plt.figure(figsize=(16, 10), dpi=80)
        
        

        out = []
        i = 0
        for o in [{"abscissa":xsc,  "dose":data [yMid,:] / np.max(data [yMid,:]),  "label":"","abscissaLabel":"x / mm" },
                {"abscissa":ysc,  "dose":data [:, xMid]/ np.max(data [:, xMid]),   "label":"" ,"abscissaLabel":"y / mm"}]:
            doseItp = interpolate.interp1d(o["abscissa"],  o["dose"])

            xx = np.arange((np.min(o["abscissa"])), (np.max(o["abscissa"])))
            yy = doseItp(xx)
            xxSpacing = xx[1] -xx [0]
            
            plateauInd,  W50,  W90 = self.get_plateauIndices(xx, yy,  desiredFieldWidth = desiredFieldWidth)
            # plateauWidth
            
            plateauWidth = xx [plateauInd[1]] -  xx [plateauInd[0]]
            plateauFit = np.polyfit(xx[plateauInd[0]:plateauInd[1]], yy[plateauInd[0]:plateauInd[1]],  deg = 1 )
            plateauFitFunc = lambda x, p: p[1] +x*p[0]
            plateauTilt = (plateauFitFunc(xx[plateauInd[0]:plateauInd[1]], plateauFit)[-1]-plateauFitFunc(xx[plateauInd[0]:plateauInd[1]], plateauFit)[0]) / plateauFitFunc(xx[plateauInd[0]:plateauInd[1]], plateauFit)[0]
            
            plateauMean = np.mean(yy[plateauInd[0]:plateauInd[1]])
            plateauMin = np.min(yy[plateauInd[0]:plateauInd[1]])
            plateauMax = np.max(yy[plateauInd[0]:plateauInd[1]])
            plateauStd = np.std(yy[plateauInd[0]:plateauInd[1]])
            flatness = plateauMax / plateauMin -1.
            
            
            # now correct uniformity region for tilt
            
            plateauCorr = yy[plateauInd[0]:plateauInd[1]] / plateauFitFunc(xx[plateauInd[0]:plateauInd[1]], (plateauFit))
            flatnessCorr = np.max(plateauCorr) / np.min(plateauCorr) -1 
            
            
            
            #txt = ("{0:s} & {1:.0f} &  {2:.2f} & {3:.2f} & {4:.2f}& {5:.2f} & {6:.2f} & {7:.2f} & {8:.2f} & {9:.2f} & {10:.2f} & {11:s}".
            #       format(o["abscissaLabel"][0], self.protonEnergy, self.measDepth,  desiredFieldWidth,  W50, W90, plateauMean, plateauStd, flatness, flatnessCorr,  plateauTilt,  self.comment))
            #print (txt)
            
            
            
            print ("Characteristic Data of {0:s}: ".format(o["abscissaLabel"]))
            print ("    Plateau tilt:       {0:.3f}".format(plateauTilt))
            print ("    Plateau tilt rel:   {0:.5f}".format(plateauTilt/plateauWidth))
            print ("    Flatness:           {0:.3f}".format(flatness))
            print ("    W50                 {0:.3f}".format(W50))
            
            
            
            if outFile!=None: outFile.write(txt+"\n")
            
            o["protonEnergy"] = self.protonEnergy
            o["measDepth"] = self.measDepth
            o["desiredFieldWidth"] =desiredFieldWidth
            o["W50"] =W50
            o["W90"] =W90
            o["flatness"] =flatness
            o["flatnessCorr"] =flatnessCorr
            o["plateauTilt"] = plateauTilt
            o["plateauWidth"] = plateauWidth
            o["comment"] = self.comment
            
            
            
            out.append( [self.protonEnergy,  self.measDepth, desiredFieldWidth, W50, W90, flatness,flatnessCorr,  plateauTilt,  plateauWidth])
            
            if plot:
                lbl = "{0:.0f} MeV, d = {1:.2f} cm".format(self.protonEnergy, self.measDepth / 10.)
                if self.comment != "": lbl += " {0:s}".format(self.comment)
                
                
                ax = plt.subplot(1, 2, i+1)
                ax.plot(o["abscissa"], o["dose"],  "o-")
                ax.plot(xx[plateauInd[0]:plateauInd[1]], plateauFitFunc(xx[plateauInd[0]:plateauInd[1]], (plateauFit)) ,  
                        "-r", label = lbl )
                ax.plot(xx[plateauInd[0]:plateauInd[1]], plateauCorr ,  "-k")
            
                ax.set_xlabel(o["abscissaLabel"])
                ax.set_ylabel("$D_{rel}$")
                ax.set_ylim([0, 1.05])
                plt.legend(loc = 0)
            i += 1
        plt.show()
        
        # determine translation of second scatterer to obtain a flat field

        corX,  corY = self.calculate_CorrectionVector(out[0][7]/out[0][8], out[1][7]/out[1][8])
        print ("Correction of second scatterer:")
        print ("    x: {0:.3f} mm".format(corX))
        print ("    y: {0:.3f} mm".format(corY))
        return out[0], out[1]
            

    def metaData_fromFilename(self):
        
        filename = os.path.basename(self.filename)
        
        try:
            self.measMaterial = filename.split(".")[0].split('_')[3]
            self.measDepth = float(filename.split(".")[0].split('_')[4]) *7.75    # depth in mm
            self.protonEnergy = float(filename.split(".")[0].split('_')[5])
            
            if (filename.split(".")[0].split('_')[6]).startswith("deltaZ"):
                self.comment = (filename.split(".")[0].split('_')[6])
        
        except:
            print ("Could not decode metadata from file {0:s}".format(filename))



    
    
def depthDependency0127(fileset = 0,  rMax = 80):
    """ Exmaple for a complex evaluation of multiple datasets,
        you might want to read this to get a feeling how to efficiently use
        the program.
        Evaluate the depth dependency of the radiation field using Lynx 
        measurements in different depths"""
     
     
    
    path = os.path.expanduser("~/nozzle/experiment_201601/Lynx/2016-01-27/mitRiFi/")
    datX = []
    datY = []
    dat2D = []
    
    if fileset ==0:
        files = ["lynx_lateral_dose_lexan_00_140_i.dcm", 
                   "lynx_lateral_dose_lexan_03_140_i.dcm", 
                   "lynx_lateral_dose_lexan_05_140_i.dcm", 
                   "lynx_lateral_dose_lexan_07_140_i.dcm", 
                   "lynx_lateral_dose_lexan_09_140_i.dcm", 
                   "lynx_lateral_dose_lexan_10_140_i.dcm", 
                   "lynx_lateral_dose_lexan_11_140_i.dcm"]
        
        for fn in files:
                       
            a = Lynx(path+os.sep+fn)
            a.set_xrange(-70, 90)
            a.set_yrange(-130, 30)
            resX, resY = a.get_characteristicData(plot = False)
            datX.append(resX)
            datY.append(resY)
            dat2D.append(a.eval2DFlatness(desiredFieldWidth = 100,  tolerance = 2.,  plot = True))
            
    elif fileset ==1:
        files = ["lynx_lateral_dose_lexan_00_145_i.dcm",  
                "lynx_lateral_dose_lexan_03_145_i.dcm", 
                "lynx_lateral_dose_lexan_05_145_i.dcm", 
                "lynx_lateral_dose_lexan_07_145_i.dcm", 
                "lynx_lateral_dose_lexan_09_145_i.dcm", 
                "lynx_lateral_dose_lexan_10_145_i.dcm", 
                "lynx_lateral_dose_lexan_11_145_i.dcm", 
                "lynx_lateral_dose_lexan_12_145_i.dcm"]
        
        for fn in files:
                       
            a = Lynx(path+os.sep+fn)
            a.set_xrange(-70, 90)
            a.set_yrange(-130, 30)
            resX, resY = a.get_characteristicData(plot = False) 
            datX.append(resX)
            datY.append(resY)
            dat2D.append(a.eval2DFlatness(desiredFieldWidth = 100,  tolerance = 2.))
    elif fileset ==2:
        files = ["lynx_lateral_dose_lexan_00_150_i.dcm",  
            "lynx_lateral_dose_lexan_03_150_i.dcm", 
            "lynx_lateral_dose_lexan_05_150_i.dcm", 
            "lynx_lateral_dose_lexan_07_150_i.dcm", 
            "lynx_lateral_dose_lexan_09_150_i.dcm", 
            "lynx_lateral_dose_lexan_10_150_i.dcm", 
            "lynx_lateral_dose_lexan_11_150_i.dcm", 
            "lynx_lateral_dose_lexan_12_150_i.dcm"]
    
        for fn in files:
                   
            a = Lynx(path+os.sep+fn)
            a.set_xrange(-70, 90)
            a.set_yrange(-130, 30)
            resX, resY = a.get_characteristicData(plot = False) 
            datX.append(resX)
            datY.append(resY)
            dat2D.append(a.eval2DFlatness(desiredFieldWidth =100,  tolerance = 2.,  plot = True))
    dat = np.array(datX)
    dat = np.swapaxes(dat, 0, 1)
    
    datSort =  dat[:,dat[1,:].argsort()]
    datSelect = dat[:, dat[1, :] < rMax]
    
  #  [self.protonEnergy,  self.measDepth, desiredFieldWidth, W50, W90, flatness, plateauTilt]
    
    fig = plt.figure(figsize=(20, 10), dpi=80)
    ax = plt.subplot(121) 
    im0 = ax.plot(datSelect[1, :], datSelect[3, :], "r",  label = "W50"  )
    im1 = ax.plot(datSelect[1, :], datSelect[4, :], "k",  label = "W90"  )
   

    
    ax.set_ylabel("X width / mm")
    plt.legend(loc = 0)
    ax2 = ax.twinx()
    im2 = ax2.plot(datSelect[1, :], datSelect[5, :], "g",  label = "Flatness"  )
    im2 = ax2.plot(datSelect[1, :], datSelect[6, :], "g--",  label = "Flatness corr"  )
    im2 = ax2.plot(datSelect[1, :], datSelect[7, :], "b",  label = "Plateau Tilt"  )
    ax.set_xlabel("depth / mm")
    ax2.set_ylabel("X flatness, X tilt")
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
           ncol=3, mode="expand", borderaxespad=0.)
   
   
    dat = np.array(datY)
    dat = np.swapaxes(dat, 0, 1)
    
    datSort =  dat[:,dat[1,:].argsort()]
    datSelect = dat[:, dat[1, :] < rMax]
    
    ax = plt.subplot(122)
    
    im0 = ax.plot(datSelect[1, :], datSelect[3, :], "r",  label = "W50"  )
    im1 = ax.plot(datSelect[1, :], datSelect[4, :], "k",  label = "W90"  )
    ax.set_ylim([np.min([np.min(datSelect[3, :]), np.min(datSelect[4, :])]), 
                np.max([np.max(datSelect[3, :]), np.max(datSelect[4, :])])*1.02])
    ax.set_ylabel("Y width / mm")
    plt.legend(loc = 0)
    ax2 = ax.twinx()
    im2 = ax2.plot(datSelect[1, :], datSelect[5, :], "g",  label = "Flatness"  )
    im2 = ax2.plot(datSelect[1, :], datSelect[6, :], "g--",  label = "Flatness corr"  )
    im2 = ax2.plot(datSelect[1, :], datSelect[7, :], "b",  label = "Plateau Tilt"  )
    ax.set_xlabel("depth / mm")
    ax2.set_ylabel("Y flatness, Y tilt")
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
           ncol=3, mode="expand", borderaxespad=0.)
 

    plt.show()
    


    dat = np.array(dat2D)
    dat = np.swapaxes(dat, 0, 1)
    
    datSort =  dat[:,dat[1,:].argsort()]
    datSelect = dat[:, dat[1, :] < rMax]
    
    fig = plt.figure(figsize=(16, 10), dpi=80)
    ax = plt.subplot(111)
    im0 = ax.plot(datSelect[1, :], datSelect[2, :], "r",  label = "Pass rate"  )
    ax.set_ylabel("pass rate")
    plt.legend(loc = 0)
    
    ax2 = ax.twinx()
    im2 = ax2.plot(datSelect[1, :], datSelect[3, :], "g",  label = "theta"  )
    im2 = ax2.plot(datSelect[1, :], datSelect[4, :], "b",  label = "phi"  )
    ax.set_xlabel("depth / mm")
    ax2.set_ylabel("degrees")
    plt.legend(loc = 3)
    plt.show()


if __name__ == "__main__":
    
#    a = Lynx("~/nozzle/experiment_20160706/kalibrierung_02_i.dcm")
#    a.calculate_CorrectionVector(0.003,0.003)
#    exit()

    parser = argparse.ArgumentParser(description = "Read Lynx data and analyze dose distribution")
    parser.add_argument("filename",  help = "Filename of DICOM file from Lynx")
    #parser.add_argument("-t", "--title",  help = "Title of plot")
    parser.add_argument("-a", "--autodetect",  help = "Automatically detect ROI (for rectangular fields only)",  action='store_true')
    parser.add_argument("-x",  help = "limits of ROI in x direction (x_low, x_high)", type = int,  nargs = 2)
    parser.add_argument("-y",  help = "limits of ROI in y direction (y_low, y_high)", type = int,  nargs = 2)
    parser.add_argument("--roiLimit",  help = "Threshold used for automatic ROI detection",  type = float)
    
  
    args = parser.parse_args()
   

    filename = os.path.expanduser ( args.filename)
    filename = os.path.expanduser ( args.filename)

    a = Lynx(filename)
    
    if args.x:
        a.set_xrange(args.x[0], args.x[1])
    if args.y:
        a.set_yrange(args.y[0], args.y[1])
    
    if args.autodetect:
        if args.x or args.y:       
            print ("WRN: Autodetect and manual selected ROI might not be what you want...")
        if args.roiLimit:
            a.autodetectRectField(threshold = args.roiLimit)
        else:
            a.autodetectRectField()
        
    a.plot(savefig = True, deltaMean = False)
    a.get_characteristicData(plot = True)
#    a.eval2DFlatness()
#    a.positionMax()
    
 
