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
cap.set(cv2.CAP_PROP_FPS, 1)
cap.set(cv2.CAP_PROP_EXPOSURE, 10)

kernel = np.ones((5, 5), np.uint8)
minLineLength = 5
maxLineGap = 20

left_angle_stat = {'present': False, 'counter': 0}
right_angle_stat = {'present': False, 'counter': 0}
bottom_angle_stat = {'present': False, 'counter': 0}
validpts = [{'x': [], 'y':[]}, {'x': [], 'y':[]}, {'x': [], 'y':[]}]
target_position = (-1, -1)


def get_slope(x1, y1, x2, y2):
    return (y2-y1)/(x2-x1)


def check_slope(target, cur_slope, check_slope, counter):
    """Returns acceptability and whether that run was truely valid"""
    if cur_slope >= (check_slope-target['ANGLE_TOLERANCE']) and cur_slope <= (check_slope+target.getfloat('ANGLE_TOLERANCE')):
        global verbosity
        if verbosity >= 3:
            print(f'matches {check_slope} at {cur_slope}')
        return ({'present': True, 'counter': target.getint('MAX_HOLD')}, True)
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

    NetworkTables.initialize(server='10.26.43.2')
    NetworkTables.addConnectionListener(
        connectionListener, immediateNotify=True)

    with cond:
        print("Waiting")
        if not notified[0]:
            cond.wait()

    return NetworkTables.getTable('Vision')


if config.getboolean('CONNECT_TO_SERVER'):
    table = connect()

x_size = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
y_size = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f'The current image is {x_size}, {y_size}')

targets = {}
for target in target_list:
    targets[target] = {}
    targets[target]['angle_names'] = config_parser[target]['ANGLE_NAMES'].split()
    targets[target]['angle_tolerance'] = config_parser[target].getfloat('ANGLE_TOLERANCE')
    targets[target]['max_hold'] = config_parser[target].getint('MAX_HOLD')
    targets[target]['x_target'] = config_parser[target].getint('X_TARGET')
    targets[target]['y_target'] = config_parser[target].getint('Y_TARGET')
    targets[target]['valid_points'] = {}
    for angle_name in targets[target]['angle_names']:
        targets[target][angle_name] = {'angle': config_parser[target].getfloat(
            angle_name), 'counter': 0}

while True:
    frame = cap.read()[1]
    # TODO inRange for our UV wavelength
    # thresh = cv2.inRange(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV),
    #                              (113, 89, 0), # These values are for 4
    #                              (123, 255, 80))
    thresh = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    x_size = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    y_size = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    black = np.zeros((y_size, x_size, 3), np.uint8)
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    edges = cv2.Canny(opened, 100, 200)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 10, minLineLength, maxLineGap)

    if type(lines) != type(None):
        for unpacked_line in lines:
            for x1, y1, x2, y2 in unpacked_line:
                cv2.line(black, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cur_slope = get_slope(x1, y1, x2, y2)
                for target in targets:
                    for angle in target['angle_names']:
                        check_slope(
                            target, cur_slope, target[angle], target[angle]['counter'])
                        stats[index] = return_value[0]
                        if return_value[1]:
                            validpts[index]['x'].extend((x1, x2))
                            validpts[index]['y'].extend((y1, y2))
                        elif not stats[index]['present']:
                            validpts[index] = {'x': [], 'y': []}

    else:
        for stat in stats:
            if stat['counter'] > 0:
                stat['counter'] -= 1
            else:
                stat['present']=False
                stat['counter']=0
    if all(item['present'] for item in stats):
        if verbosity >= 2:
            print('Target Found.')

        x_vals=[validpts[index]['x'][index_two] for index in range(
            len(validpts)) for index_two in range(len(validpts[index]['x']))]
        x_avg=int(sum(x_vals)/len(x_vals))
        y_vals=[validpts[index]['y'][index_two] for index in range(
            len(validpts)) for index_two in range(len(validpts[index]['y']))]
        offset_to_middle=int(max(y_vals)-min(y_vals))
        y_avg=int(sum(y_vals)/len(y_vals))
        target_position=(x_avg, y_avg-offset_to_middle)

        if config.getboolean('CONNECT_TO_SERVER'):
            table.putBoolean('valid', True)
            table.putNumber('x', target_position[0])
            table.putNumber('y', target_position[1])
            table.putNumber('x_offset', (target_position[0]-x_target))
            table.putNumber('y_offset', (target_position[1]-y_target))

        cv2.circle(black, target_position, 5, (0, 255, 0))
    elif verbosity >= 2:
        print('Not found.')
        if target.getboolean('CONNECT_TO_SERVER'):
            table.putBoolean('valid', False)

    cv2.circle(black, (x_target, y_target), 5, (0, 0, 255))
    if verbosity >= 1:
        cv2.imshow('raw_image', frame)
        cv2.imshow('processed_image', edges)
        cv2.imshow('lines', black)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()