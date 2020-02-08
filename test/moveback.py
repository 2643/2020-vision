import  os
import threading
import configparser
import cv2
import numpy as np
from scipy.spatial import cKDTree

cap = cv2.VideoCapture(-1)
cap.set(cv2.CAP_PROP_FPS, 1)
cap.set(cv2.CAP_PROP_EXPOSURE, 10)

#minimumTargetSize: valuse between 0 to 1
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
    #[leftEnd, rightEnd, topEnd, bottomEnd]

    movement = [False, False, False, False]
    #[turnLeft, turnRight, moveBack, moveForward]

    frameAverage = np.average(npFrame)

    #Check in seeable
    if (frameAverage > 0):
        
        #Check the size
        if (frameAverage > minimumTargetSize):

            #Check left end
            if (np.average(npFrame[:, 0]) > 0):
                imagePosition[0] = True
                movement[0] = True

            #Check right end
            if (np.average(npFrame[:, width]) > 0):
                imagePosition[1] = True
                movement[1] = True

            #Check top end
            if (np.average(npFrame[0, :]) > 0):
                imagePosition[2] = True
                movement[3] = True

            #Check bottom end
            if (np.average(npFrame[height, :]) > 0):
                imagePosition[3] = True
                movement[3] = True

        else:
            notSeen = true
            print("Vision target too far away")
    else:
        notSeen = True
        print("No target in sight")

    #Check the movement array
    if (movement[0] == movement[1]):
        movement[0] = False
        movement[1] = False
        movement[3] = True
        print("Too close, move back")

    if (movement[2] == movement[3]):
        print("Bruh, what did you even do")

    #Return the movment list
    return movement


correct_position(cap)






