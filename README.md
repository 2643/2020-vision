# 2020 Vision Code

FRC Team 2643's code for finding the 2020 high goal target on a co-processor running Python 3.x

---

Libraries currently in use:
 - [OpenCV](https://pypi.org/project/opencv-python/)
 - [Numpy](https://pypi.org/project/numpy/)
 - [Network Tables](https://pypi.org/project/pynetworktables/)

---

Usage of configparser allows for easy configuration:

- Tolerances for angle recognition
- Hold duration (in # of loops which may vary by a few ms)
- Verbosity
- Network connection (using pynetworktables)

*Planned*

- Multiple target aquisition