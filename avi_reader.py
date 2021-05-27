# -*- coding: utf-8 -*-
"""
author: Jonathan Machin

A class to read the main and stream headers of single-stream AVI RIFF format .avi movies
Implements basic cross-header verification of: time-per-frame, width/height, buffer size, frame number
Allows rewriting of the .avi movie into the .avi format with mpjg compression with tunable frames-per-second and pixel binning using cv2.


Usage:
    
v = AVI(pathin)  # read the .avi video at the location pathin
v.print_headers() # print the main and stream headers as read from the video
v.verify_headers() # do basic cross-header verification checks to ensure same data
v.rewrite(pathout,rebin_factor=2, greyscale=True) # rewrite at location pathout as a 2x-binned greyscale .avi (with mjpg codec)

vnew = AVI(pathout) # read in the rewritten .avi video
vnew.print_headers() # print the headers of the new video
vnew.verify_headers() # cross-header verify the new videos


main() implements a CLI for the conversion, usage:
run in directory with the .avi videos you want to convert
The console will then guide you through the process

"""

from cv2 import destroyAllWindows, VideoCapture, cvtColor, COLOR_BGR2GRAY, resize, INTER_CUBIC, VideoWriter_fourcc, VideoWriter
from numpy import int32, float32, array, frombuffer
import numpy as np
import os

i32 = int32
f32 = float32

bad_files = []

# AVI class
class AVI():
    def __init__(self, fi):
        self.file = fi
        with open(self.file, 'rb') as file:
            self.read_avi(file)
            
        
       
    def read_avi(self,file):
        self.read_header(file)
        tpf_stream = int(1000000/(self.stream_header['rate']/self.stream_header['scale']))
        self.stream_tpf = tpf_stream


          
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
    def verify_headers(self,v=True):
        verify_list = []
        # check frame numbers are the same
        if self.stream_header['frame_number'] == self.main_header['frame_number']:
            if v == True:
                print('frame number agrees between the headers\n')
        else:
            if v == True:
                print('WARNING: the frame numbers disagree between the headers')
                print('Main Header:', self.main_header['frame_number'], '\tStream Header:', self.stream_header['frame_number'],'\n')
                verify_list.append('frame_numbers')
                
        # check that time-per-frame and rate/scale agree
        stream_tpf = int(1000000/(self.stream_header['rate']/self.stream_header['scale']))
        if stream_tpf == self.main_header['tpf']:
            if v == True:
                print('time-per-frame and inferred time-per-frame agrees between the headers\n')
        else:
            if v == True:
                print('WARNING: the time-per-frame and inferred time-per-frame disagrees between the headers')
                print('Main Header:', self.main_header['tpf'], '\tStream Header:', stream_tpf,'\n')
                verify_list.append('time-per-frame')
            
        # check that frame height/width agree
        if self.main_header['height']==self.stream_header['frame'][6] and self.main_header['width']==self.stream_header['frame'][5]:
            if v == True:
                print('width and height data agree between the headers\n')
        else:
            if v == True:
                print('WARNING: the height/width values disagree between the headers')
                print('Main Header:', self.main_header['width'], self.main_header['height'], '\tStream Header:', self.stream_header['frame'][5:7],'\n')
                verify_list.append('pixel height/width')            

        # check buffer sizes agrees
        if self.main_header['buffer_size'] == self.stream_header['buffer_size']:
            if v == True:
                print('buffer sizes agree between the headers\n')
        else:
            if v == True:
                print('WARNING: the buffer size disagrees betweens the two headers, this is PROBABLY harmless')
                print('Main Header:', self.main_header['buffer_size'], '\tStream Header', self.stream_header['buffer_size'],'\n')

        tpf_stream = int(1000000/(self.stream_header['rate']/self.stream_header['scale']))
        print('the inferred video length from the Stream Header is', self.stream_header['frame_number']*tpf_stream/1000000, 's\n')        
        if len(verify_list) == 0:
            print('main header and stream header agree in converted video')
        else:
            print('WARNING: this video has header disagreements:', verify_list)
            bad_files.append(self.file)
                
    
    def show_info(self):
        print(self.file, '('+str(self.main_header['width'])+'x'+str(self.main_header['height'])+')')
        print('Time-per-Frame, \u03bcs (main header, stream header): ', self.main_header['tpf'], '\t', self.stream_tpf)
        print('Number of Frames (main header, stream header): ', self.main_header['frame_number'], '\t', self.stream_header['frame_number'])
        print('\n')


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
        tpf_stream = int(1000000/(self.stream_header['rate']/self.stream_header['scale']))
        print(tpf_stream)
        print('the inferred video length is', self.stream_header['frame_number']*tpf_stream/1000000, 's\n')


    def rewrite(self,output,rebin_factor=1, fps=None, greyscale=True):
        if fps == None:
            fps = self.stream_header['rate']/self.stream_header['scale']
            print('fps  of',fps, 'inferred from the Stream Header for', self.file) #, '. This can be overridden by passing the fps arguement to rewrite().\n')
            
        else:
            print('fps of', fps, 'set by user and will be used')
            
        cap = VideoCapture(self.file)
        out = None

        
        count = 0
        print('processing', self.file)
        while (cap.isOpened()): # and count < 20:
            # Capture each frame
            ret, frame = cap.read()
            if ret == True:
                if greyscale == True:
                    frame = cvtColor(frame, COLOR_BGR2GRAY)
                    y,x = frame.shape
                else:
                    y,x,channels = frame.shape
                
                if rebin_factor != 1:
                    new_size = (int(x/rebin_factor), int(y/rebin_factor))
                    frame = resize(frame, new_size, interpolation=INTER_CUBIC)
    
                if not out:
                    fourcc = VideoWriter_fourcc(*'MJPG')
                    
                    if greyscale == True:
                        height,width = frame.shape
                        out = VideoWriter(output, fourcc, fps, (width, height), 0)
                    else:
                        height,width,channels = frame.shape
                        out = VideoWriter(output, fourcc, fps, (width, height))
    
                out.write(frame)
                count+=1
    
            else:
                print('Frame after frame', count, 'could not be read, it is likely the end of the file. \nIf you expected more frames then it likely that the read failed on this frame.')
                break
    
        # release the capture and output object
        cap.release()
        out.release()
        destroyAllWindows()


# CLI interface for converting .avi videos
def main():  
    files = os.listdir('.')
    avi_files = []
    for file in files:
        if file[-4:] == '.avi':
            avi_files.append(file)
    print(len(avi_files), '.avi files found in this folder\n')
    
    for file in avi_files:
        v = AVI(file)
        v.show_info()
        
    convert_video = input('Would you like to convert these videos (y/n): ')
    if convert_video != 'y':
        return

    if 'new_avi' not in files:
        os.mkdir('new_avi')

    #yprint('All avi files will be converted using default settings:\n\n\tpixel binning: no (1)\n\tgreyscale conversion: no\n')
    #cont = input('Are you happy to continue? (y/n/q)  ')
    cont = 'y'
    if cont != 'y' and cont != 'n':
        return

    elif cont == 'y':
        rebin_factor = 1
        greyscale = False

    elif cont == 'n':
        rebin_factor = input('pixel binning factor (integer):  ')
        if not rebin_factor.isnumeric() or len(rebin_factor) != 1:
            return
        rebin_factor = int(rebin_factor)

        greyscale = input('greyscale conversion (y/n):  ')
        if greyscale == 'y':
            greyscale = True
        elif greyscale == 'n':
            greyscale == False 
        else:
            return

    for file in avi_files:
        v = AVI(file)
        pathout = 'new_avi/'+file[:-4]+'_convert.avi'
        v.rewrite(pathout, rebin_factor=rebin_factor, greyscale=greyscale)

        vnew = AVI(pathout)
        vnew.verify_headers(v=False)

    print('file conversion finished')
    if len(bad_files) == 0:
        print('no bad files were identified. NOTE THIS MAY NOT ALWAYS BE RIGHT')
    else:
        print('based on the header information the following file conversions may have failed:\n', bad_files)

    input('\nFinished. Press enter to exit')
    


if __name__ == '__main__':
    main()
    




