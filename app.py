#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import copy
import argparse
from collections import Counter
from collections import deque

import cv2 as cv
import mediapipe as mp
import numpy as np

from utils import (
    CvFpsCalc,
    draw_info,
    draw_point_history,
    draw_info_text,
    pre_process_point_history,
    select_mode,
    calc_bounding_rect,
    calc_landmark_list,
    pre_process_landmark,
    logging_csv,
    draw_bounding_rect,
    draw_landmarks,
)
from model import KeyPointClassifier
from model import PointHistoryClassifier
import time


from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient
from unitree_sdk2py.go2.sport.sport_client import SportClient


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--width", help="cap width", type=int, default=960)
    parser.add_argument("--height", help="cap height", type=int, default=540)

    parser.add_argument("--use_static_image_mode", action="store_true")
    parser.add_argument(
        "--min_detection_confidence",
        help="min_detection_confidence",
        type=float,
        default=0.7,
    )
    parser.add_argument(
        "--min_tracking_confidence",
        help="min_tracking_confidence",
        type=int,
        default=0.5,
    )

    args = parser.parse_args()

    return args


def main():
    # Argument parsing #################################################################
    args = get_args()

    cap_device = args.device
    cap_width = args.width
    cap_height = args.height

    use_static_image_mode = args.use_static_image_mode
    min_detection_confidence = args.min_detection_confidence
    min_tracking_confidence = args.min_tracking_confidence

    use_brect = True

    # Camera preparation ###############################################################
    # cap = cv.VideoCapture(cap_device)
    # cap.set(cv.CAP_PROP_FRAME_WIDTH, cap_width)
    # cap.set(cv.CAP_PROP_FRAME_HEIGHT, cap_height)

    # Camera preparation Debug Video ###############################################################
    # cap = cv.VideoCapture("debug_video.mp4")
    # cap.set(cv.CAP_PROP_FRAME_WIDTH, cap_width)
    # cap.set(cv.CAP_PROP_FRAME_HEIGHT, cap_height)

    # Model load #############################################################
    mp_hands = mp.solutions.hands  # type: ignore[attr-defined]
    hands = mp_hands.Hands(
        static_image_mode=use_static_image_mode,
        max_num_hands=4,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )

    keypoint_classifier = KeyPointClassifier()

    point_history_classifier = PointHistoryClassifier()

    # Read labels ###########################################################
    with open(
        "model/keypoint_classifier/keypoint_classifier_label.csv", encoding="utf-8-sig"
    ) as f:
        keypoint_classifier_labels = csv.reader(f)
        keypoint_classifier_labels = [row[0] for row in keypoint_classifier_labels]
    with open(
        "model/point_history_classifier/point_history_classifier_label.csv",
        encoding="utf-8-sig",
    ) as f:
        point_history_classifier_labels = csv.reader(f)
        point_history_classifier_labels = [
            row[0] for row in point_history_classifier_labels
        ]

    # Enable OpenCV optimizations
    try:
        cv.setUseOptimized(True)
        # Use at least 4 threads for SIMD ops if available
        cv.setNumThreads(max(cv.getNumThreads(), 4))
    except Exception:
        pass

    # FPS Measurement ########################################################
    cvFpsCalc = CvFpsCalc(buffer_len=10)
    perf_last = 0.0
    perf_frames = 0

    # Coordinate history #################################################################
    history_length = 16
    point_history = deque(maxlen=history_length)

    # Finger gesture history ################################################
    finger_gesture_history = deque(maxlen=history_length)

    #  ########################################################################
    mode = 0

    # Initialize Unitree communications & clients once (moving out of loop improves FPS)
    ChannelFactoryInitialize(0)
    # Create Sport client after ChannelFactoryInitialize to avoid DDS NoneType errors
    sport_client = SportClient()
    sport_client.SetTimeout(10.0)
    sport_client.Init()
    video_client = VideoClient()
    video_client.SetTimeout(3.0)
    video_client.Init()

    while True:
        fps = cvFpsCalc.get()

        # Process Key (ESC: end) #################################################
        key = cv.waitKey(1)
        if key == 27:  # ESC
            break
        number, mode = select_mode(key, mode)

        # Camera capture #####################################################
        # ret, image = cap.read()
        # if not ret:
        #     break
        # # image = cv.flip(image, 1)  # Mirror display
        # debug_image = copy.deepcopy(image)

        # GO2 CAMERA #####################################################
        code, data = video_client.GetImageSample()

        # image = cv.flip(image, 1)  # Mirror display
        # debug_image = copy.deepcopy(image)

        # image = cv.flip(image, 1)  # Mirror display
        # debug_image = copy.deepcopy(image)

        image = None
        debug_image = None
        if code != 0 or not data:
            print("Warning: received empty image data")
        else:
            image_data = np.frombuffer(bytes(data), dtype=np.uint8)
            # Decode JPEG; prefer full color for model accuracy
            image = cv.imdecode(image_data, cv.IMREAD_COLOR)
            if image is None:
                print("Warning: failed to decode frame")
            else:
                # Optional resize to target width/height from args to reduce compute
                h, w = image.shape[:2]
                if (cap_width and cap_height) and (w != cap_width or h != cap_height):
                    image = cv.resize(image, (cap_width, cap_height), interpolation=cv.INTER_AREA)
                # Prepare debug image without expensive deepcopy
                debug_image = image.copy()

        # Detection implementation #############################################################
        if image is not None:
            image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

            image.flags.writeable = False
            results = hands.process(image)
            image.flags.writeable = True
        else:
            continue

        #  ####################################################################
        if results.multi_hand_landmarks is not None:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                # Bounding box calculation
                brect = calc_bounding_rect(debug_image, hand_landmarks)
                # Landmark calculation
                landmark_list = calc_landmark_list(debug_image, hand_landmarks)

                # Conversion to relative coordinates / normalized coordinates
                pre_processed_landmark_list = pre_process_landmark(landmark_list)
                pre_processed_point_history_list = pre_process_point_history(
                    debug_image, point_history
                )
                # Write to the dataset file
                logging_csv(
                    number,
                    mode,
                    pre_processed_landmark_list,
                    pre_processed_point_history_list,
                )

                # Hand sign classification
                hand_sign_id = keypoint_classifier(pre_processed_landmark_list)
                if (
                    hand_sign_id == "Change to pointer id in the future"
                ):  # Point gesture
                    point_history.append(landmark_list[8])
                else:
                    point_history.append([0, 0])

                # Finger gesture classification
                finger_gesture_id = 0
                point_history_len = len(pre_processed_point_history_list)
                if point_history_len == (history_length * 2):
                    finger_gesture_id = point_history_classifier(
                        pre_processed_point_history_list
                    )

                # Calculates the gesture IDs in the latest detection
                finger_gesture_history.append(finger_gesture_id)
                most_common_fg_id = Counter(finger_gesture_history).most_common()

                # Drawing part (avoid heavy per-frame prints to keep FPS high)
                print(keypoint_classifier_labels[hand_sign_id], hand_sign_id)


                if hand_sign_id == 5:  # Pointing_Up
                    sport_client.StandUp()
                    time.sleep(2)
                if hand_sign_id == 6:  # Pointing_Up
                    sport_client.StandDown()
                    time.sleep(2)

                if hand_sign_id == 0:  # Pointing_Up
                    sport_client.Hello()
                    time.sleep(2)





                debug_image = draw_bounding_rect(use_brect, debug_image, brect)
                debug_image = draw_landmarks(debug_image, landmark_list)
                debug_image = draw_info_text(
                    debug_image,
                    brect,
                    handedness,
                    keypoint_classifier_labels[hand_sign_id],
                    point_history_classifier_labels[most_common_fg_id[0][0]],
                )
        else:
            point_history.append([0, 0])

        if debug_image is not None:
            debug_image = draw_point_history(debug_image, point_history)
            debug_image = draw_info(debug_image, fps, mode, number)

        # Simple FPS counter once per second
        perf_frames += 1
        now = cv.getTickCount() / cv.getTickFrequency()
        if perf_last == 0.0:
            perf_last = now
        elif now - perf_last >= 1.0:
            # Uncomment for performance logging
            # print(f"[perf] ~{perf_frames} FPS")
            perf_frames = 0
            perf_last = now

        # Screen reflection #############################################################
        if debug_image is not None:
            cv.imshow("Hand Gesture Recognition", debug_image)

    # cap.release()
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
