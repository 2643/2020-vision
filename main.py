#!/usr/bin/env python3

import math
import os
import dotenv
import cv2
import numpy as np
from pathlib import Path
from networktables import NetworkTables

dotenv.load_dotenv()

cap = cv2.VideoCapture(-1)
cap.set(cv2.CAP_PROP_FPS, 1)
cap.set(cv2.CAP_PROP_EXPOSURE, 10)

kernel = np.ones((5,5),np.uint8)
minLineLength = 5
maxLineGap = 20

left_angle_stat = {'present': False, 'counter': 0}
right_angle_stat = {'present': False, 'counter': 0}
bottom_angle_stat = {'present': False, 'counter': 0}

def get_slope(x1, y1, x2, y2):
    return (y2-y1)/(x2-x1)

def check_slope(cur_slope, check_slope, counter):
    if cur_slope >= (check_slope-float(os.getenv('ANGLE_TOLERANCE'))) and cur_slope <= (check_slope+float(os.getenv('ANGLE_TOLERANCE'))):
        print(f'matches {check_slope} at {cur_slope}')
        return {'present': True, 'counter': int(os.getenv('MAX_HOLD'))}
    elif counter > 0:
        return {'present': True, 'counter': counter-1}
    else:
        return {'present': False, 'counter': 0}

while True:
    left_angle = float(os.getenv('LEFT_ANGLE'))
    right_angle = float(os.getenv('RIGHT_ANGLE')) 
    bottom_angle = float(os.getenv('BOTTOM_ANGLE'))
    stats = [left_angle_stat, right_angle_stat, bottom_angle_stat]
    
    frame = cap.read()[1]
    #TODO inRange for our UV wavelength
    thresh = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    xsize = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    ysize = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    black = np.zeros((ysize,xsize,3), np.uint8)
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    edges = cv2.Canny(opened, 100, 200)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 10, minLineLength, maxLineGap)

    if type(lines) != type(None):
        for unpacked_line in lines:
            for x1, y1, x2, y2 in unpacked_line:
                cv2.line(black, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cur_slope = get_slope(x1, y1, x2, y2)
                left_angle_stat = check_slope(cur_slope, left_angle, left_angle_stat['counter'])
                right_angle_stat = check_slope(cur_slope, right_angle, right_angle_stat['counter'])
                bottom_angle_stat = check_slope(cur_slope, bottom_angle, bottom_angle_stat['counter'])
    else:
        for stat in stats:
            if stat['counter'] > 0:
                stat['counter'] -= 1
            else:
                stat['present'] = False
                stat['counter'] = 0
    if all(item['present'] for item in stats):
        print('Target Found.')
    else: print('Not found.')            
    
    cv2.imshow('raw_image', frame)
    cv2.imshow('processed_image', edges)
    cv2.imshow('lines', black)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
