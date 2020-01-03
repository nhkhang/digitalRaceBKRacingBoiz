import cv2
import numpy as np
import process
import time
from collections import deque


def lane_pos(right, left):
    if right[0][1] - left[0][1] < 0:
        return -1
    return right[0][1] - left[0][1] > 0


def dodge(left, right, obs):
    straight = (np.arctan(mode(left)) + np.arctan(mode(right))) / 2

    if not (obs[0] ^ obs[1]):
        return straight

    turn = 0.2

    if obs[0]:
        if lane_pos(right, left) == 1:
            return straight
        return straight + turn

    if lane_pos(right, left) == -1:
        return straight
    return straight - turn


def detect_lane_contour(img):
    height, width = img.shape[:2]
    padding = []
    for i in range(height):
        padding.append([0])

    img_padding = np.hstack((padding, img, padding))

    right_lane = []
    left_lane = []

    for i in range(width):
        if img_padding[height - 1][width - i] != 0:
            if i > 0:
                right_lane.append([height - 1, width - i])
                break

            for j in range(2, height):
                if img_padding[height - j][width] == 0:
                    right_lane.append([height - j + 1, width])
                    break

            if len(right_lane) == 0:
                right_lane.append([1, width])

            break

    for i in range(1, width):
        if img_padding[height-1][i] != 0:
            if i > 1:
                left_lane.append([height-1, i])
                break

            for j in range(2, height):
                if img_padding[height - j][1] == 0:
                    left_lane.append([height - j + 1, 1])
                    break

            if len(left_lane) == 0:
                left_lane.append([1, 1])

            break

    # right and left lane
    while left_lane[-1][0] > 0 and left_lane[-1][1] < right_lane[-1][1]:
        yy = min(right_lane[-1][0], left_lane[-1][0])

        right_lane.append(right_lane[-1])
        left_lane.append(left_lane[-1])

        while right_lane[-1][1] != left_lane[-1][1] and right_lane[-1][0] >= yy:
            right_lane[-1] = choose_with_kernel(img_padding, "right", right_lane[-1][0], right_lane[-1][1])

        while left_lane[-1][1] != right_lane[-1][1] and left_lane[-1][0] >= yy:
            left_lane[-1] = choose_with_kernel(img_padding, "left", left_lane[-1][0], left_lane[-1][1])

    right_lane.pop(0)
    left_lane.pop(0)

    if right_lane[-1][0] < left_lane[-1][0]:
        right_lane.pop(-1)
    elif right_lane[-1][0] > left_lane[-1][0]:
        left_lane.pop(-1)

    return left_lane, right_lane


def choose_with_kernel(img, position, y, x):
    if position == "right":
        if img[y - 1][x]:
            return y - 1, x
        if img[y - 1][x + 1]:
            return y - 1, x + 1
        if img[y - 1][x - 1]:
            return y - 1, x - 1
        return y, x - 1

    if position == "left":
        if img[y - 1][x]:
            return y - 1, x
        if img[y - 1][x - 1]:
            return y - 1, x - 1
        if img[y - 1][x + 1]:
            return y - 1, x + 1
        return y, x + 1


def draw_contour(img, lane):
    left, right = detect_lane_contour(lane)
    height, width = img.shape[:2]

    for i in range(len(left) - 1):
        img[left[i][0] + height//3, left[i][1]] = (255, 0, 0)
    for i in range(len(right) - 1):
        img[right[i][0] + height//3, right[i][1]-1] = (0, 255, 0)

    obs_left, obs_right = detect_obs(left, right)
    for i in obs_left:
        img[left[i][0] + int(height/3), left[i][1]] = (255, 0, 255)
    for i in obs_right:
        img[right[i][0] + int(height/3), right[i][1] - 1] = (255, 0, 255)

    cv2.imshow('lane', lane)
    cv2.imshow("contour", img)
    #
    cv2.waitKey(0)


def detect_obs(left, right):
    r = 40

    obs_left = []
    for i in range(r, len(left)):
        dy = (left[i - r][0] - left[i][0]) / (left[i][1] - left[i - r][1] + 0.01)

        if dy < 0.2:
            obs_left.append(left[i])

    obs_right = []
    for i in range(r, len(right)):
        dy = (right[i - r][0] - right[i][0]) / (right[i - r][1] - right[i][1] + 0.01)

        if dy < 0.2:
            obs_right.append(right[i])

    return obs_left, obs_right


def switch_lane(obs_left, obs_right, lane):
    new_angle = 0
    if obs_right:
        new_angle += -1
    elif obs_left:
        new_angle += -1
    return new_angle


def angle_calculate(right, left):
    left_grad = left[-1] - left[0]
    right_grad = right[-1] - right[0]
    grad = left_grad + right_grad

    return np.arctan(grad[1] / grad[0])


def mode(lst):
    r = 5
    grad =[]
    for i in range(r, len(lst)):
        grad.append((lst[i][0] - lst[i-r][0]) / (lst[i][1] - lst[i-r][1] + 0.01))

    grad.sort()

    res = [0, 0]
    idx = 0
    for i, val in enumerate(grad):
        if abs(val - grad[idx]) > 0.1:
            if i - idx > res[1] - res[0]:
                res = [idx, i]
            while abs(val - grad[idx]) > 0.1:
                idx = idx + 1
    if len(grad) - idx > res[1] - res[0]:
        res = [idx, len(grad)]

    return grad[(res[0] + res[1]) // 2]

# CALCULATE ANGLE COMPARE TO MID_LANE
def mid_vector(mid):
    if len(mid) > 1:
        A = [1, 0]
        for i in range(1, len(mid)):
            A[1] += (mid[0][1] - mid[i][1]) / (mid[0][0] - mid[i][0])

        A[1] /= len(mid) - 1
    else:
        A = [1, 0]

    # (1, dx/dy)
    return A


def position_from_mid(mid_eq, standing_pos):
    C = 400

    y = mid_eq[0][0] - standing_pos[0]
    x = mid_eq[0][1] - standing_pos[1]

    temp = x * mid_eq[1][0] + y * mid_eq[1][1]

    # (y, x) / C
    y = (y - temp * mid_eq[1][0])
    x = (x - temp * mid_eq[1][1])

    return [y/C, x/C]


def angle_mid(A, delta):
    C = 1.5

    y = A[0] + delta[0]
    x = A[1] + delta[1]

    print('A = ' + str(A))
    print('d = ' + str(delta))

    print('x = ' + str(x) + ' y= ' + str(y))

    # C * atan(A + d)
    return -C * np.arctan2(x, y)


def mid_lane(left_lane, right_lane, img):
    height, width = img.shape[:2]
    mid = []

    for i in range(len(left_lane)):
        mid.append(((left_lane[i][0] + right_lane[i][0]) / 2, (left_lane[i][1] + right_lane[i][1]) / 2))

    return mid
# END CALCULATE ANGLE COMPARE TO MID_LANE

# TURN TRAFFIC SIGN
def turn_traffic_sign(sign):
    # sign: left = 0, right = 1
    start_turn = time.time()
    # velo reduce
    velo = 0
    angle = 0
    while time.time() - start_turn < 2.1:
        angle = 30
        velo = 40
    return velo, angle


def decision(img):
    lane = process.detect_lane(img)
    left, right = detect_lane_contour(lane)

    mid = mid_lane(left, right, img)

    if len(mid) != 0:
        road_vector = mid_vector(mid)
        delta = position_from_mid((mid[0], road_vector), (img.shape[0], img.shape[1] / 2))
    else:
        road_vector = [1, 0]
        delta = [0, 0]

    angle = angle_mid(road_vector, delta)
    velo = 50

    return velo, angle