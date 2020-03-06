#!/usr/bin/env python3

import os
import threading
import configparser
import cv2
import numpy as np
from networktables import NetworkTables

config_parser = configparser.ConfigParser()
config_parser.read('config.conf')
config = config_parser['SETTINGS']
verbosity = config.getint('VERBOSITY')
target_list = list(config_parser.sections())
target_list.remove('SETTINGS')

cap = cv2.VideoCapture(-1)
cap.set(cv2.CAP_PROP_FPS, config.getint('FPS'))
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
cap.set(cv2.CAP_PROP_EXPOSURE, config.getint('EXPOSURE'))

kernel = np.ones((5, 5), np.uint8)
minLineLength = config.getint('MIN_LINE_LENGTH')
maxLineGap = config.getint('MAX_LINE_GAP')
min_color = tuple(map(int, config['MIN_COLOR'].split()))
max_color = tuple(map(int, config['MAX_COLOR'].split()))

left_angle_stat = {'present': False, 'counter': 0}
right_angle_stat = {'present': False, 'counter': 0}
bottom_angle_stat = {'present': False, 'counter': 0}

def get_slope(x1, y1, x2, y2):
    global config
    if abs(x2-x1) < config.getint('VERTICAL_CHANGE'):
        return 99
    return (y2-y1)/(x2-x1)


def check_slope(target, cur_slope, check_slope, counter):
    """Returns acceptability and whether that run was truely valid"""
    if cur_slope >= (check_slope-target['angle_tolerance']) and cur_slope <= (check_slope+target['angle_tolerance']):
        global verbosity
        if verbosity >= 3:
            print(f'matches {check_slope} at {cur_slope}')
        return ({'present': True, 'counter': target['max_hold']}, True)
    elif counter > 0:
        return ({'present': True, 'counter': counter-1}, False)
    else:
        return ({'present': False, 'counter': 0}, False)


def connect():
    cond = threading.Condition()
    notified = [False]

    def connectionListener(connected, info):
        print(info, '; Connected=%s' % connected)
        with cond:
            notified[0] = True
            cond.notify()

    NetworkTables.initialize(server='roborio-2643-frc.local')
    NetworkTables.addConnectionListener(
        connectionListener, immediateNotify=True)

    with cond:
        print("Waiting")
        if not notified[0]:
            cond.wait()

    return NetworkTables.getTable('vision-movement')



if config.getboolean('CONNECT_TO_SERVER'):
    table = connect()

x_size = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
y_size = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f'The current image is {x_size}, {y_size}')

targets = {}
for target in target_list:
    targets[target] = {}
    targets[target]['angle_names'] = config_parser[target]['ANGLE_NAMES'].split()
    targets[target]['angle_tolerance'] = config_parser[target].getfloat(
        'ANGLE_TOLERANCE')
    targets[target]['max_hold'] = config_parser[target].getint('MAX_HOLD')
    targets[target]['x_target'] = config_parser[target].getint('X_TARGET')
    targets[target]['y_target'] = config_parser[target].getint('Y_TARGET')
    targets[target]['half_target'] = config_parser[target].getboolean('HALF_TARGET')
    targets[target]['offset_direction'] = config_parser[target]['OFFSET_DIRECTION'].lower()
    targets[target]['target_color'] = tuple(map(int, config_parser[target]['TARGET_COLOR'].split()))
    targets[target]['found_center_color'] = tuple(map(int, config_parser[target]['FOUND_CENTER_COLOR'].split()))
    for angle_name in targets[target]['angle_names']:
        targets[target][angle_name] = {'angle': config_parser[target].getfloat(
            angle_name), 'present': False, 'counter': 0, 'valid_points': {'x': [], 'y': []}}
            
while True:
    frame = cap.read()[1]
    #frame = cv2.blur(frame, (5,5))
    # TODO inRange for our UV wavelength
    thresh = cv2.inRange(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV), min_color, max_color)
    #thresh = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    x_size = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    y_size = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    black = np.zeros((y_size, x_size, 3), np.uint8)
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    dilate = cv2.morphologyEx(opened, cv2.MORPH_DILATE, kernel)
    edges = cv2.Canny(dilate, 10, 100)
    lines = cv2.HoughLinesP(edges, 1, np.pi/360, 20, minLineLength=minLineLength, maxLineGap=maxLineGap)

    if type(lines) != type(None):
        for unpacked_line in lines:
            for x1, y1, x2, y2 in unpacked_line:
                cv2.line(black, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cur_slope = get_slope(x1, y1, x2, y2)
                for target_name in targets:
                    target = targets[target_name]
                    for angle_name in target['angle_names']:
                        #print(cur_slope)
                        return_value = check_slope(
                            target, cur_slope, target[angle_name]['angle'], target[angle_name]['counter'])
                        target[angle_name].update(return_value[0])
                        if return_value[1]:
                            target[angle_name]['valid_points']['x'].extend(
                                (x1, x2))
                            target[angle_name]['valid_points']['y'].extend(
                                (y1, y2))
                        elif not return_value[0]['present']:
                            target[angle_name]['valid_points'].update(
                                {'x': [], 'y': []})
    else:
        for target_name in targets:
            target = targets[target_name]
            for angle_name in target['angle_names']:
                if target[angle_name]['counter'] > 0:
                    target[angle_name]['counter'] -= 1
                else:
                    target[angle_name]['present'] = False
                    target[angle_name]['counter'] = 0
    #print(targets)
    for target_name in targets:
        target = targets[target_name]
        prev_sum = 0
        if all(target[angle_name]['present'] for angle_name in target['angle_names']):
            [item for angle_name in target['angle_names'] for item in target[angle_name]['valid_points']['x']]
            if verbosity >= 2:
                print(f'{target_name} found.')
            x_vals = [item for angle_name in target['angle_names'] for item in target[angle_name]['valid_points']['x']]
            x_avg = int(sum(x_vals)/len(x_vals))
            y_vals = [item for angle_name in target['angle_names'] for item in target[angle_name]['valid_points']['y']]
            y_avg = int(sum(y_vals)/len(y_vals))
            
            if target['half_target']:
                if target['offset_direction'] == 'up':
                    offset_to_middle = int(max(y_vals)-min(y_vals))
                    target_position = (x_avg, y_avg-offset_to_middle)
                if target['offset_direction'] == 'down':
                    offset_to_middle = int(max(y_vals)-min(y_vals))
                    target_position = (x_avg, y_avg+offset_to_middle)
                if target['offset_direction'] == 'left':
                    offset_to_middle = int(max(x_vals)-min(x_vals))
                    target_position = (x_avg-offset_to_middle, y_avg)
                if target['offset_direction'] == 'right':
                    offset_to_middle = int(max(y_vals)-min(y_vals))
                    target_position = (x_avg+offset_to_middle, y_avg)
            else:
                target_position = (x_avg, y_avg)

            if config.getboolean('CONNECT_TO_SERVER'):
                table.putBoolean('valid', True)
                table.putNumber(f'{target}_x', target_position[0])
                table.putNumber(f'{target}_y', target_position[1])
                x_offset = target_position[0]-target['x_target']
                table.putNumber(f'{target}_x_offset', x_offset)
                y_offset = target_position[1]-target['y_target']
                table.putNumber(f'{target}_y_offset', y_offset)
                if x_offset > 25:
                    table.putBooleanArray('movement_array', [False, True, False, False])
                if x_offset < 25:
                    table.putBooleanArray('movement_array', [True, False, False, False])

            if verbosity >= 1:
                cv2.circle(black, tuple(map(abs, target_position)), 15, target['found_center_color'])
                print(target_position)
        elif verbosity >= 2:
            print(f'{target_name} not found.')
            if config.getboolean('CONNECT_TO_SERVER'):
                table.putBoolean('valid', False)
        if verbosity >= 1:
            cv2.circle(black, (target['x_target'], target['y_target']), 5, target['target_color'])
    if verbosity >= 1:
        cv2.line(black, (355, 100), (200, 300), (255, 0, 0))
        cv2.imshow('thresh', thresh)
        cv2.imshow('raw_image', frame)
        cv2.imshow('processed_image', edges)
        cv2.imshow('lines', black)
        
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
