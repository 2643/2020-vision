#!/usr/bin/env python3

import math
import os
import dotenv
import cv2
import numpy as np
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
validpts = [{'x':[], 'y':[]},{'x':[], 'y':[]},{'x':[], 'y':[]}]
target_position = (-1, -1)

def get_slope(x1, y1, x2, y2):
    return (y2-y1)/(x2-x1)

def check_slope(cur_slope, check_slope, counter):
    """Returns acceptability and whether that run was truely valid"""
    if cur_slope >= (check_slope-float(os.getenv('ANGLE_TOLERANCE'))) and cur_slope <= (check_slope+float(os.getenv('ANGLE_TOLERANCE'))):
        print(f'matches {check_slope} at {cur_slope}')
        return ({'present': True, 'counter': int(os.getenv('MAX_HOLD'))}, True)
    elif counter > 0:
        return ({'present': True, 'counter': counter-1}, False)
    else:
        return ({'present': False, 'counter': 0}, False)

while True:
    left_angle = float(os.getenv('LEFT_ANGLE'))
    right_angle = float(os.getenv('RIGHT_ANGLE')) 
    bottom_angle = float(os.getenv('BOTTOM_ANGLE'))
    stats = [left_angle_stat, right_angle_stat, bottom_angle_stat]
    check_vals = [left_angle, right_angle, bottom_angle]
    
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
                for index in range(len(stats)):
                    return_value = check_slope(cur_slope, check_vals[index], stats[index]['counter'])
                    stats[index] = return_value[0]
                    if return_value[1]:
                        validpts[index]['x'].extend((x1, x2))
                        validpts[index]['y'].extend((y1, y2))
                    elif not stats[index]['present']:
                        validpts[index] = {'x':[], 'y':[]}


    else:
        for stat in stats:
            if stat['counter'] > 0:
                stat['counter'] -= 1
            else:
                stat['present'] = False
                stat['counter'] = 0
    if all(item['present'] for item in stats):
        print('Target Found.')
        x_vals = [validpts[index]['x'][index_two] for index in range(len(validpts)) for index_two in range(len(validpts[index]['x']))]
        x_avg = int(sum(x_vals)/len(x_vals))
        y_vals = [validpts[index]['y'][index_two] for index in range(len(validpts)) for index_two in range(len(validpts[index]['y']))]
        offset_to_middle = int(max(y_vals)-min(y_vals))
        y_avg = int(sum(y_vals)/len(y_vals))
        target_position = (x_avg, y_avg-offset_to_middle)
        cv2.circle(black, target_position, 5, (0,255,0))
    else:
        print('Not found.')            
    
    cv2.imshow('raw_image', frame)
    cv2.imshow('processed_image', edges)
    cv2.imshow('lines', black) 
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
