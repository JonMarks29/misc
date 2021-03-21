# -*- coding: utf-8 -*-
"""
author: Jonathan Machin

A class to read the main and stream headers of single-stream AVI RIFF format .avi movies
Implements basic cross-header verification of: time-per-frame, width/height, buffer size, frame number
Allows rewriting of the .avi movie into the mjpg format with tunable frames-per-second and pixel binning using cv2.


Usage:

v = AVI(pathin)  # read the .avi video at the location pathin
v.print_headers() # print the main and stream headers as read from the video
v.verify_headers() # do basic cross-header verification checks to ensure same data
v.rewrite(pathout,rebin_factor=1, greyscale=True, fps=None) # rewrite at location pathout as a 2x-binned greyscale .avi (with mjpg codec).
    # if fps=None the function will try to infer the fps from the stream header information, this can be overidden by passing a value

vnew = AVI(pathout) # read in the rewritten .avi video
vnew.print_headers() # print the headers of the new video
vnew.verify_headers() # cross-header verify the new videos

"""

import cv2
from numpy import int32, float32, array, frombuffer
import numpy as np

i32 = int32
f32 = float32


class AVI():
    def __init__(self, fi):
        self.file = fi
        with open(self.file, 'rb') as file:
            self.read_avi(file)
       
    def read_avi(self,file):
        self.read_header(file)
        #self.read_data(file)
          
    def read_header(self, file):
        self.main_header = {}
        file.seek(32)
       
        # READ MAIN HEADER
        self.main_header['tpf'] = self.read_values(file, i32, 1) # int32 is correct decoding
        self.main_header['datarate'] = self.read_values(file, i32, 1) # int32 is probably correct decoding
        
        # this 1 x4 byte block should reserved - but takes a value in these files, may represent padding granularity
        self.main_header['padding'] = self.read_values(file, i32, 1)
        self.main_header['flags'] = self.read_values(file, i32, 1)
        self.main_header['frame_number'] = self.read_values(file, i32, 1) # int32 is correct decoding
        self.main_header['initial_frames'] = self.read_values(file, i32, 1) # int32 is correct decoding, for audio/visual interleaving
        self.main_header['data_streams'] = self.read_values(file, i32, 1) # int32 is correct decoding
        self.main_header['buffer_size'] = self.read_values(file, i32, 1) # int32 is probably correct decoding, represents a single frame of the data to read into buffer
        self.main_header['width'] = self.read_values(file, i32, 1) # int32 is correct decoding
        self.main_header['height'] = self.read_values(file, i32, 1) # int32 is correct decoding
        
        # these values are reserved (4 x 4 bytes)
        reserved = self.read_values(file, i32, 4)
        
        # AVI STREAM HEADER
        self.stream_header = {}
        file.seek(108)
        
        self.stream_header['fcctype'] = self.read_letters(file, np.byte, 4)
        self.stream_header['ffchandler'] = self.read_letters(file, np.byte, 4)
        
        self.stream_header['flags']  = self.read_values(file, i32, 1)
        self.stream_header['priority']  = self.read_values(file, i32, 1)
        self.stream_header['initial_frames']  = self.read_values(file, i32, 1)
        self.stream_header['scale'] = self.read_values(file, i32, 1)
        self.stream_header['rate'] = (self.read_values(file, i32, 1))
        self.stream_header['start_time']  = self.read_values(file, i32, 1)
        self.stream_header['frame_number'] = self.read_values(file, i32, 1)
        self.stream_header['buffer_size']  = self.read_values(file, i32, 1)
        self.stream_header['quality']  = self.read_values(file, i32, 1)
        self.stream_header['sample_size']  = self.read_values(file, i32, 1)
        self.stream_header['frame']  = self.read_values(file, i32, 7)
    
    
    # check that the two headers agree with each other: frame_number, time-per-frame, height/width, buffer size
    def verify_headers(self):
        # check frame numbers are the same
        if self.stream_header['frame_number'] == self.main_header['frame_number']:
            print('frame number agrees between the headers\n')
        else:
            print('WARNING: the frame numbers disagree between the headers')
            print('Main Header:', self.main_header['frame_number'], '\tStream Header:', self.stream_header['frame_number'],'\n')
        
        # check that time-per-frame and rate/scale agree
        stream_tpf = int(1000000/(self.stream_header['rate']/self.stream_header['scale']))
        if stream_tpf == self.main_header['tpf']:
            print('time-per-frame and inferred time-per-frame agrees between the headers\n')
        else:
            print('WARNING: the time-per-frame and inferred time-per-frame disagrees between the headers')
            print('Main Header:', self.main_header['tpf'], '\tStream Header:', stream_tpf,'\n')
            
        # check that frame height/width agree
        if self.main_header['height']==self.stream_header['frame'][6] and self.main_header['width']==self.stream_header['frame'][5]:
            print('width and height data agree between the headers\n')
        else:
            print('WARNING: the height/width values disagree between the headers')
            print('Main Header:', self.main_header['width'], self.main_header['height'], '\tStream Header:', self.stream_header['frame'][5:7],'\n')
            
        # check buffer sizes agrees
        if self.main_header['buffer_size'] == self.stream_header['buffer_size']:
            print('buffer sizes agree between the headers\n')
        else:
            print('WARNING: the buffer size disagrees betweens the two headers, this is PROBABLY harmless')
            print('Main Header:', self.main_header['buffer_size'], '\tStream Header', self.stream_header['buffer_size'],'\n')


    def read_values(self, file, t, count):
        size = array((), t).itemsize
        string = file.read(size * count)
        if len(string) < size * count:
            print('failed to access header values')
        
        values = frombuffer(string, t)
        if count == 1:
            return values[0]
        return values
    
    
    def read_letters(self,file,t,count):
        size = array((), t).itemsize
        string = file.read(size * count)
        if len(string) < size * count:
            print('failed to access header values')
        
        values = frombuffer(string, t)
        s = ''
        for v in values:
            s += chr(v)
        return s
        
    
    def print_headers(self):
        print('\n---Headers of file:', self.file,'---')
        print('AVI MAIN HEADER')
        for k,v in self.main_header.items():
            print(k,v)
        print('\nAVI STREAM HEADER')
        for k,v in self.stream_header.items():
            print(k,v)
        print('\n')


    def rewrite(self,output,rebin_factor=1, fps=None, greyscale=True):
        if fps == None:
            fps = self.stream_header['rate']/self.stream_header['scale']
            print('fps  of',fps, 'inferred from the Stream Header. Passing an fps arguement to rewrite() will override this.\n')
            
        cap = cv2.VideoCapture(self.file)
        out = None
        
        count = 0
        while (cap.isOpened()) and count < 20:
            # Capture each frame
            ret, frame = cap.read()
            if ret == True:
                print('Processing frame', count+1)
                if greyscale == True:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    y,x = frame.shape
                else:
                    y,x,channels = frame.shape
                
                if rebin_factor != 1:
                    new_size = (int(x/rebin_factor), int(y/rebin_factor))
                    frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_CUBIC)
    
                if not out:
                    height,width, channels = frame.shape
                    fourcc = cv2.VideoWriter_fourcc(*'mjpg')
                    
                    if greyscale == True:
                        out = cv2.VideoWriter(output, fourcc, fps, (width, height), 0)
                    else:
                        out = cv2.VideoWriter(output, fourcc, fps, (width, height))
    
                out.write(frame)
                count+=1
    
            else:
                print('Frame after frame', count, 'could not be read, it is likely the end of the file. \nIf you expected more frames then it likely that the read failed on this frame.')
                break
    
        # release the capture and output object
        cap.release()
        out.release()
        cv2.destroyAllWindows()


