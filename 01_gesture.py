import cv2
import time
import numpy as np
import threading

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient
from unitree_sdk2py.go2.sport.sport_client import SportClient

from modules.gesture import GestureRecognizer

print("Starting Gesture Recognition")

ChannelFactoryInitialize(0)

video_client = VideoClient()
video_client.SetTimeout(3.0)
video_client.Init()

sport_client = SportClient()
sport_client.SetTimeout(10.0)
sport_client.Init()

detector = GestureRecognizer()

gesture_actions = {
    "Thumb_Up": sport_client.StandUp,
    "Thumb_Down": sport_client.StandDown,
    "Open_Palm": sport_client.Hello,
    "Closed_Fist": "NONE",
    "ILoveYou": sport_client.Hello,
    "Victory": "None",
    "Pointing_Up": "NONE",
}

last_time = time.time()
delay = 1

code, data = video_client.GetImageSample()

def process_gesture(gesture):
    if gesture in gesture_actions:
        action = gesture_actions[gesture]
        action_thread = threading.Thread(target=action)
        action_thread.start()
        print(f"FOUND GESTURE {gesture}")


if __name__ == "__main__":
    while code == 0:
        code, data = video_client.GetImageSample()


        if not data:
            print("Warning: received empty image data")
            frame = None
        else:
            image_data = np.frombuffer(bytes(data), dtype=np.uint8)
            frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
            if frame is None:
                print("Warning: failed to decode frame")

        # image_data = np.frombuffer(bytes(data), dtype=np.uint8)
        # frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

        if frame is not None:
            frame, current_gesture, results = detector.detect_gesture(frame)
        else:
            continue
            

        print(current_gesture, "=========================")
        # frame, current_gesture, _ = detector.detect_gesture(frame)

        current_time = time.time()

        # print a snapshot of detected gestures once per delay interval
        if current_gesture is None:
            left_g, right_g = "None", "None"
        else:
            left_g = current_gesture.get("Left", "None")
            right_g = current_gesture.get("Right", "None")

        if current_time - last_time >= delay:
            # informative prints so you can see what is being recognized
            print(f"[gesture] Left: {left_g} | Right: {right_g}  (t={int(current_time)})")

            process_gesture(left_g)
            process_gesture(right_g)

            last_time = current_time

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        cv2.imshow('Gesture Recognition', frame)

    cv2.destroyAllWindows()