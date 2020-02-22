#!/usr/bin/env python3

import os
import threading
import configparser
import networktables
import cv2
import numpy as np
from networktables import NetworkTables

config_parser = configparser.ConfigParser()
config_parser.read('config.conf')
target = config_parser['2020-High-Target']
config = config_parser['SETTINGS']

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

NetworkTables.initialize(server='roborio-2643-frc.local')
network_table = NetworkTables.getTable("vision_movement")


def get_slope(x1, y1, x2, y2):
    return (y2-y1)/(x2-x1)


def correct_position(cap, minimumTargetSize):
    ret, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ret, threshold = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    npFrame = np.array(threshold)

    height = npFrame.shape[0]
    width = npFrame.shape[1]

    notSeen = False
    tooSmall = False

    imagePosition = [False, False, False, False]
    # [leftEnd, rightEnd, topEnd, bottomEnd]
    movement = [False, False, False, False]
    # [turnLeft, turnRight, moveBack, moveForward]
    frameAverage = np.average(npFrame)

    # Check if a target is in sight
    if (frameAverage > 0):

        # Check if the target is large enough
        if (frameAverage > minimumTargetSize):
            # Check the ends of the image to get the target in sight
            # Left end
            if (np.average(npFrame[:, 0]) > 0):
                imagePosition[0] = True
                movement[0] = True

            # Right end
            if (np.average(npFrame[:, width]) > 0):
                imagePosition[1] = True
                movement[1] = True

            # Top end
            if (np.average(npFrame[0, :]) > 0):
                imagePosition[2] = True
                movement[3] = True

            # Bottom end
            if (np.average(npFrame[height, :]) > 0):
                imagePosition[3] = True
                movement[3] = True

        else:
            notSeen = true
            print("Vision target too far away")
    else:
        notSeen = True
        print("No target in sight")

    # Error check the movement list
    if (movement[0] == movement[1]):
        movement[0] = False
        movement[1] = False
        movement[3] = True
        print("Too close, move back")

    if (movement[2] == movement[3]):
        movement[2] = False
        movement[3] = False
        print("There is most likely an obstruction")

    # Return the movment list
    for move in movement:
        movesExist = true
    
    if movesExist == true:
        network_table.putBooleanArray('movement_array', movement)

    return movement


def check_slope(cur_slope, check_slope, counter):
    """Returns acceptability and whether that run was truely valid"""
    if cur_slope >= (check_slope-target.getfloat('ANGLE_TOLERANCE')) and cur_slope <= (check_slope+target.getfloat('ANGLE_TOLERANCE')):
        global verbosity
        if verbosity >= 3:
            print(f'matches {check_slope} at {cur_slope}')
        return ({'present': True, 'counter': target.getint('MAX_HOLD')}, True)
    elif counter > 0:
        return ({'present': True, 'counter': counter-1}, False)
    else:
        return ({'present': False, 'counter': 0}, False)


def connect():
    cond=threading.Condition()
    notified=[False]

    def connectionListener(connected, info):
        print(info, '; Connected=%s' % connected)
        with cond:
            notified[0]=True
            cond.notify()

    NetworkTables.initialize(server = '10.26.43.2')
    NetworkTables.addConnectionListener(
        connectionListener,
        immediateNotify = True
    )

    with cond:
        print("Waiting")
        if not notified[0]:
            cond.wait()

    return NetworkTables.getTable('Vision')


if config.getboolean('CONNECT_TO_SERVER'):
    table=connect()

x_size=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
y_size=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f'The current image is {x_size}, {y_size}')

while True:
    verbosity=config.getint('VERBOSITY')
    left_angle=target.getfloat('LEFT_ANGLE')
    right_angle=target.getfloat('RIGHT_ANGLE')
    bottom_angle=target.getfloat('BOTTOM_ANGLE')
    x_target=target.getint('X_TARGET')
    y_target=target.getint('Y_TARGET')
    stats=[left_angle_stat, right_angle_stat, bottom_angle_stat]
    check_vals=[left_angle, right_angle, bottom_angle]

    frame=cap.read()[1]

    minimumTargetSize = 1 #TARGET SIZE VALUE
    correction = True
    numberOfMoves = 0

    while correction == true:
        correctionMoves = correct_position(minimumTargetSize)
        for move in correctionMoves:
            if move == True:
                numberOfMoves += 1
        if numberOfMoves == 0:
            correction = False

    thresh=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    x_size=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    y_size=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    black=np.zeros((y_size, x_size, 3), np.uint8)
    opened=cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    edges=cv2.Canny(opened, 100, 200)
    lines=cv2.HoughLinesP(edges, 1, np.pi/180, 10, minLineLength, maxLineGap)

    if type(lines) != type(None):
        for unpacked_line in lines:
            for x1, y1, x2, y2 in unpacked_line:
                cv2.line(black, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cur_slope=get_slope(x1, y1, x2, y2)
                for index in range(len(stats)):
                    return_value=check_slope(
                        cur_slope, check_vals[index], stats[index]['counter'])
                    stats[index]=return_value[0]
                    if return_value[1]:
                        validpts[index]['x'].extend((x1, x2))
                        validpts[index]['y'].extend((y1, y2))
                    elif not stats[index]['present']:
                        validpts[index]={'x': [], 'y': []}

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
