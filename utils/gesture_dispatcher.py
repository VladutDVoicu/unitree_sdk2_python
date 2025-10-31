import threading
import time


def build_gesture_actions(sport_client):
    return {
        5: sport_client.StandUp,
        6: sport_client.StandDown,
        4: sport_client.Hello,
    }


class GestureDispatcher:
    def __init__(self, gesture_actions, cooldown: float = 2.0):
        self._gesture_actions = gesture_actions
        self._cooldown = cooldown
        self._last_run = {}
        self._lock = threading.Lock()

    def process(self, gesture: int) -> None:
        action = self._gesture_actions.get(gesture)
        if action is None:
            return
        now = time.time()
        with self._lock:
            last = self._last_run.get(gesture, 0.0)
            if now - last < self._cooldown:
                return
            self._last_run[gesture] = now
        threading.Thread(target=action, daemon=True).start()
        print(f"FOUND GESTURE {gesture}")
