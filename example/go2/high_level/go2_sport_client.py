import time
import sys
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.default import unitree_go_msg_dds__SportModeState_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_
from unitree_sdk2py.go2.sport.sport_client import (
    SportClient,
    PathPoint,
    SPORT_PATH_POINT_SIZE,
)
import math
from dataclasses import dataclass
from unitree_sdk2py.go2.robot_state.robot_state_client import RobotStateClient

@dataclass
class TestOption:
    name: str
    id: int


class RobotStateMonitor:
    def __init__(self):
        self.sport_mode_state = None
        self.state_subscriber = None
        self.robot_state_client = None
        self.is_monitoring = False

    def init_state_monitoring(self):
        print("Initializing robot state monitoring...")

        self.state_subscriber = ChannelSubscriber("rt/sportmodestate", SportModeState_)
        self.state_subscriber.Init(self.state_message_handler, 10)

        self.robot_state_client = RobotStateClient()
        self.robot_state_client.Init()

        self.is_monitoring = True
        print("Robot state monitoring initialized!")

    def state_message_handler(self, msg: SportModeState_):
        """Handle incoming state messages"""
        self.sport_mode_state = msg

    def get_current_position(self):
        """Get robot's current position [x, y, z]"""
        if self.sport_mode_state:
            return list(self.sport_mode_state.position)
        return None

    def get_current_velocity(self):
        """Get robot's current velocity [vx, vy, vyaw]"""
        if self.sport_mode_state:
            return list(self.sport_mode_state.velocity)
        return None

    def get_body_height(self):
        """Get robot's current body height"""
        if self.sport_mode_state:
            return self.sport_mode_state.body_height
        return None

    def get_imu_data(self):
        """Get IMU data (roll, pitch, yaw)"""
        if self.sport_mode_state and self.sport_mode_state.imu_state:
            return {
                'rpy': list(self.sport_mode_state.imu_state.rpy),
                'gyroscope': list(self.sport_mode_state.imu_state.gyroscope),
                'accelerometer': list(self.sport_mode_state.imu_state.accelerometer)
            }
        return None

    def get_foot_forces(self):
        """Get foot force sensors data"""
        if self.sport_mode_state:
            return list(self.sport_mode_state.foot_force)
        return None

    def get_mode_info(self):
        """Get current mode and progress"""
        if self.sport_mode_state:
            return {
                'mode': self.sport_mode_state.mode,
                'progress': self.sport_mode_state.progress,
                'gait_type': self.sport_mode_state.gait_type
            }
        return None

    def print_state_summary(self):
        """Print a summary of current robot state"""
        if not self.sport_mode_state:
            print("No state data available")
            return

        print("Robot State Summary:")
        print(f"   Position: {self.get_current_position()}")
        print(f"   Velocity: {self.get_current_velocity()}")
        print(f"   Body Height: {self.get_body_height():.3f}m")

        imu = self.get_imu_data()
        if imu:
            print(f"   IMU (R,P,Y): {[round(x, 2) for x in imu['rpy']]}")

        mode_info = self.get_mode_info()
        if mode_info:
            print(f"   Mode: {mode_info['mode']}, Progress: {mode_info['progress']:.2f}")

        foot_forces = self.get_foot_forces()
        if foot_forces:
            print(f"   Foot Forces: {foot_forces}")


class CustomBehaviorExtension:
    def __init__(self, sport_client):
        self.sport_client = sport_client
        self.is_running = False
        self.state_monitor = RobotStateMonitor()

    def init_with_state_monitoring(self):
        """Initialize the extension with state monitoring capabilities"""
        self.state_monitor.init_state_monitoring()

    def wait_for_stable_position(self, timeout=5):
        """Wait for robot to reach a stable position"""
        print("  - Waiting for stable position...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            velocity = self.state_monitor.get_current_velocity()
            if velocity:
                if all(abs(v) < 0.1 for v in velocity):
                    print("Position stabilized")
                    return True
            time.sleep(0.1)

        print("Timeout waiting for stable position")
        return False

    def custom_patrol(self):
        """
        Custom patrol behavior: Move in a rectangular pattern with state monitoring
        """
        print("Starting Custom Patrol Behavior...")

        if self.state_monitor.is_monitoring:
            print("State monitoring enabled - will track position and stability")
            self.state_monitor.print_state_summary()

        # Stand up first
        print("  - Standing up...")
        self.sport_client.StandUp()
        time.sleep(2)

        if self.state_monitor.is_monitoring:
            self.wait_for_stable_position()

        # Move forward
        print("  - Moving forward...")
        start_pos = self.state_monitor.get_current_position() if self.state_monitor.is_monitoring else None
        self.sport_client.Move(0.3, 0, 0)
        time.sleep(3)
        self.sport_client.StopMove()

        if self.state_monitor.is_monitoring:
            end_pos = self.state_monitor.get_current_position()
            if start_pos and end_pos:
                distance = ((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)**0.5
                print(f"Moved {distance:.2f}m from start position")
            self.wait_for_stable_position()
        else:
            time.sleep(1)

        # Turn right
        print("  - Turning right...")
        self.sport_client.Move(0, 0, -0.5)
        time.sleep(2)
        self.sport_client.StopMove()

        if self.state_monitor.is_monitoring:
            self.wait_for_stable_position()
        else:
            time.sleep(1)

        # Move forward again
        print("  - Moving forward...")
        self.sport_client.Move(0.3, 0, 0)
        time.sleep(2)
        self.sport_client.StopMove()

        if self.state_monitor.is_monitoring:
            self.wait_for_stable_position()
        else:
            time.sleep(1)

        # Turn right again
        print("  - Turning right...")
        self.sport_client.Move(0, 0, -0.5)
        time.sleep(2)
        self.sport_client.StopMove()

        if self.state_monitor.is_monitoring:
            self.wait_for_stable_position()
            print("📊 Final state:")
            self.state_monitor.print_state_summary()

        print("Custom patrol completed!")

    def custom_dance(self):
        print("  - Getting ready...")
        self.sport_client.StandUp()
        time.sleep(2)

        print("  - Spinning around...")
        self.sport_client.Move(0, 0, 1.0)
        time.sleep(2)
        self.sport_client.StopMove()
        time.sleep(0.5)

        print("  - Side stepping...")
        self.sport_client.Move(0, 0.3, 0)
        time.sleep(1)
        self.sport_client.Move(0, -0.3, 0)
        time.sleep(1)
        self.sport_client.StopMove()
        time.sleep(0.5)

        print("  - Forward and back...")
        self.sport_client.Move(0.2, 0, 0)
        time.sleep(1)
        self.sport_client.Move(-0.2, 0, 0)
        time.sleep(1)
        self.sport_client.StopMove()

        print("  - Final bow...")
        self.sport_client.Hello()

    def custom_greeting(self):
        self.sport_client.StandUp()
        time.sleep(2)

        print("  - Saying hello...")
        for i in range(3):
            self.sport_client.Hello()
            time.sleep(2)

        # print("  - Showing off with a spin...")
        # self.sport_client.Move(0, 0, 0.8)
        # time.sleep(2)
        # self.sport_client.StopMove()

        print("  - Stretching...")
        self.sport_client.Stretch()

    def custom_circle_walk(self):
        print("Starting Custom Circle Walk...")

        if self.state_monitor.is_monitoring:
            print("Monitoring robot state during circle walk")

        self.sport_client.StandUp()
        time.sleep(2)

        print("  - Walking in a circle...")
        start_pos = self.state_monitor.get_current_position() if self.state_monitor.is_monitoring else None

        self.sport_client.Move(0.2, 0, 0.3)
        time.sleep(8)
        self.sport_client.StopMove()

        if self.state_monitor.is_monitoring:
            end_pos = self.state_monitor.get_current_position()
            if start_pos and end_pos:
                distance = ((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)**0.5
                print(f"Distance from start: {distance:.2f}m")
            print("Final state:")
            self.state_monitor.print_state_summary()

        print("Circle walk completed!")

    def custom_state_aware_behavior(self):
        """
        State-aware behavior that adapts based on robot's current state
        """
        print("Starting State-Aware Behavior...")

        if not self.state_monitor.is_monitoring:
            print("State monitoring required for this behavior")
            return

        self.sport_client.StandUp()
        time.sleep(2)

        # Get initial state
        initial_height = self.state_monitor.get_body_height()
        print(f"Initial body height: {initial_height:.3f}m")

        # Adapt behavior based on current height
        if initial_height and initial_height < 0.25:
            print("  - Robot is low, performing high steps")
            # Higher, more careful movements
            for i in range(3):
                print(f"    Step {i+1}/3")
                self.sport_client.Move(0.1, 0, 0)
                time.sleep(1)
                self.sport_client.StopMove()
                self.wait_for_stable_position(2)
        else:
            print("  - Robot is at normal height, performing normal walk")
            self.sport_client.Move(0.3, 0, 0)
            time.sleep(2)
            self.sport_client.StopMove()
            self.wait_for_stable_position()

        # Check foot forces to determine if robot needs to adjust
        foot_forces = self.state_monitor.get_foot_forces()
        if foot_forces:
            max_force = max(foot_forces)
            print(f"Max foot force: {max_force}")

            if max_force > 100:  # Arbitrary threshold
                print("  - High foot pressure detected, performing stretch")
                self.sport_client.Stretch()
                time.sleep(3)

        # Final state report
        print("Behavior complete - Final state:")
        self.state_monitor.print_state_summary()

    def test_state_monitor_only(self):
        """
        Test robot state monitoring without any movement
        Just reads and displays current robot state information
        """
        print("Testing Robot State Monitor")
        print("=" * 50)

        if not self.state_monitor.is_monitoring:
            print("   State monitoring not initialized!")
            print("   State monitoring is required for this test.")
            return

        print("Collecting robot state data...")

        # Wait a moment for state data to be received
        time.sleep(1)

        if not self.state_monitor.sport_mode_state:
            print("No state data received yet. Waiting longer...")
            time.sleep(3)

        if not self.state_monitor.sport_mode_state:
            print("Unable to receive robot state data.")
            print("Make sure the robot is connected and powered on.")
            return

        print("State data received! Here's what we can monitor:")
        print()

        # Test all state monitoring functions
        print("POSITION DATA:")
        position = self.state_monitor.get_current_position()
        if position:
            print(f"   Current Position (X,Y,Z): {[round(p, 3) for p in position]} m")
        else:
            print("   Position data not available")

        body_height = self.state_monitor.get_body_height()
        if body_height is not None:
            print(f"   Body Height: {body_height:.3f} m")
        else:
            print("   Body height data not available")

        print()
        print("🏃 MOTION DATA:")
        velocity = self.state_monitor.get_current_velocity()
        if velocity:
            print(f"   Current Velocity (vx,vy,vyaw): {[round(v, 3) for v in velocity]} m/s")
            is_stationary = all(abs(v) < 0.05 for v in velocity)
            print(f"   Robot Status: {'🟢 Stationary' if is_stationary else '🔴 Moving'}")
        else:
            print("   Velocity data not available")

        print()
        print("IMU SENSOR DATA:")
        imu_data = self.state_monitor.get_imu_data()
        if imu_data:
            rpy = imu_data.get('rpy', [0, 0, 0])
            print(f"   Orientation (R,P,Y): {[round(angle, 2) for angle in rpy]} rad")
            print(f"   Orientation (R,P,Y): {[round(angle*57.3, 1) for angle in rpy]} deg")

            gyro = imu_data.get('gyroscope', [0, 0, 0])
            print(f"   Gyroscope: {[round(g, 3) for g in gyro]} rad/s")

            accel = imu_data.get('accelerometer', [0, 0, 0])
            print(f"   Accelerometer: {[round(a, 2) for a in accel]} m/s²")
        else:
            print("   IMU data not available")

        print()
        print("FOOT SENSOR DATA:")
        foot_forces = self.state_monitor.get_foot_forces()
        if foot_forces:
            foot_names = ['FL', 'FR', 'RL', 'RR']  # Front Left, Front Right, Rear Left, Rear Right
            print("   Foot Forces:")
            for i, (name, force) in enumerate(zip(foot_names, foot_forces)):
                print(f"     {name}: {force:4d} N")

            total_force = sum(foot_forces)
            avg_force = total_force / 4
            print(f"   Total Force: {total_force} N")
            print(f"   Average per foot: {avg_force:.1f} N")

            # Check balance
            max_diff = max(foot_forces) - min(foot_forces)
            balance_status = "🟢 Well balanced" if max_diff < 50 else "⚠️ Uneven weight distribution"
            print(f"   Balance Status: {balance_status}")
        else:
            print("   Foot force data not available")

        print()
        print("ROBOT STATUS:")
        mode_info = self.state_monitor.get_mode_info()
        if mode_info:
            mode_names = {0: "Idle", 1: "Standing", 2: "Walking", 3: "Running"}  # Example mappings
            mode_name = mode_names.get(mode_info['mode'], f"Mode {mode_info['mode']}")
            print(f"   Current Mode: {mode_name}")
            print(f"   Progress: {mode_info['progress']:.1f}%")
            print(f"   Gait Type: {mode_info['gait_type']}")
        else:
            print("   Mode information not available")

        # Check if there are any error codes
        if hasattr(self.state_monitor.sport_mode_state, 'error_code'):
            error_code = self.state_monitor.sport_mode_state.error_code
            if error_code != 0:
                print(f"   ⚠️ Error Code: {error_code}")
            else:
                print("   ✅ No errors detected")

        print()
        print("=" * 50)
        print("STATE MONITOR TEST COMPLETE")
        print("All robot sensors are readable via state monitoring!")
        print("This data can be used to make smart behavioral decisions.")
        print("You can now build adaptive behaviors based on real robot state.")


option_list = [
    TestOption(name="damp", id=0),         
    TestOption(name="stand_up", id=1),     
    TestOption(name="stand_down", id=2),   
    TestOption(name="move forward", id=3),         
    TestOption(name="move lateral", id=4),    
    TestOption(name="move rotate", id=5),  
    TestOption(name="stop_move", id=6),  
    TestOption(name="custom_patrol", id=7),  # Custom patrol behavior
    TestOption(name="hand stand", id=8),
    TestOption(name="balanced stand", id=9),     
    TestOption(name="recovery", id=10),       
    TestOption(name="left flip", id=11),      
    TestOption(name="back flip", id=12),
    TestOption(name="free walk", id=13),  
    TestOption(name="free bound", id=14), 
    TestOption(name="free avoid", id=15),  
    TestOption(name="custom_dance", id=16),   # Custom dance sequence
    TestOption(name="walk upright", id=17),
    TestOption(name="cross step", id=18),
    TestOption(name="free jump", id=19),
    TestOption(name="custom_greeting", id=20), # Custom greeting sequence
    TestOption(name="custom_circle_walk", id=21), # Custom circle walk
    TestOption(name="state_aware_behavior", id=22), # State-aware adaptive behavior
    TestOption(name="test_state_monitor", id=23) # Test state monitoring (no movement)
]


class UserInterface:
    def __init__(self):
        self.test_option_ = None

    def convert_to_int(self, input_str):
        try:
            return int(input_str)
        except ValueError:
            return None

    def terminal_handle(self):
        input_str = input("Enter id or name: \n")

        if input_str == "list":
            self.test_option_.name = None
            self.test_option_.id = None
            for option in option_list:
                print(f"{option.name}, id: {option.id}")
            return

        for option in option_list:
            if input_str == option.name or self.convert_to_int(input_str) == option.id:
                self.test_option_.name = option.name
                self.test_option_.id = option.id
                print(f"Test: {self.test_option_.name}, test_id: {self.test_option_.id}")
                return

        print("No matching test option found.")


if __name__ == "__main__":

    print("WARNING: Please ensure there are no obstacles around the robot while running this example.")
    input("Press Enter to continue...")
    if len(sys.argv)>1:
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        ChannelFactoryInitialize(0)

    test_option = TestOption(name=None, id=None) 
    user_interface = UserInterface()
    user_interface.test_option_ = test_option

    sport_client = SportClient()  
    sport_client.SetTimeout(10.0)
    sport_client.Init()

    custom_behaviors = CustomBehaviorExtension(sport_client)
    
    # Initialize state monitoring (optional - comment out if you don't want it)
    print("  Initializing state monitoring...")
    try:
        custom_behaviors.init_with_state_monitoring()
        print("   State monitoring available for enhanced behaviors!")
    except Exception as e:
        print(f"   State monitoring failed to initialize: {e}")
        print("   Custom behaviors will work without state monitoring.")

    while True:

        user_interface.terminal_handle()

        print(f"Updated Test Option: Name = {test_option.name}, ID = {test_option.id}\n")

        if test_option.id == 0:
            sport_client.Damp()
        elif test_option.id == 1:
            sport_client.StandUp()
        elif test_option.id == 2:
            sport_client.StandDown()
        elif test_option.id == 3:
            sport_client.Move(0.2, 0, 0)
            time.sleep(3)
            sport_client.StopMove()
        elif test_option.id == 4:
            sport_client.Move(-0.2, 0, 0)
            time.sleep(3)
            sport_client.StopMove()
        elif test_option.id == 5:
            sport_client.Move(0, 0, 0.5)
        elif test_option.id == 6:
            sport_client.StopMove()
        elif test_option.id == 7:
            # Custom patrol behavior
            custom_behaviors.custom_patrol()
        # elif test_option.id == 8:
        #     sport_client.HandStand(True)
        #     time.sleep(4)
        #     sport_client.HandStand(False)
        # elif test_option.id == 9:
        #     sport_client.BalanceStand()
        # elif test_option.id == 10:
        #     sport_client.RecoveryStand()
        # elif test_option.id == 11:
        #     ret = sport_client.LeftFlip()
        #     print("ret: ",ret)
        # elif test_option.id == 12:
        #     ret = sport_client.BackFlip()
        #     print("ret: ",ret)
        # elif test_option.id == 13:
        #     ret = sport_client.FreeWalk()
        #     print("ret: ",ret)
        # elif test_option.id == 14:
        #     ret = sport_client.FreeBound(True)
        #     print("ret: ",ret)
        #     time.sleep(2)
        #     ret = sport_client.FreeBound(False)
        #     print("ret: ",ret)
        # elif test_option.id == 15:
        #     ret = sport_client.FreeAvoid(True)
        #     print("ret: ",ret)
        #     time.sleep(2)
        #     ret = sport_client.FreeAvoid(False)
        #     print("ret: ",ret)
        # elif test_option.id == 17:
        #     ret = sport_client.WalkUpright(True)
        #     print("ret: ",ret)
        #     time.sleep(4)
        #     ret = sport_client.WalkUpright(False)
        #     print("ret: ",ret)
        # elif test_option.id == 18:
        #     ret = sport_client.CrossStep(True)
        #     print("ret: ",ret)
        #     time.sleep(4)
        #     ret = sport_client.CrossStep(False)
        #     print("ret: ",ret)
        elif test_option.id == 16:
            # Custom dance sequence
            # custom_behaviors.custom_dance()
            pass
        # elif test_option.id == 19:
        #     ret = sport_client.FreeJump(True)
        #     print("ret: ",ret)
        #     time.sleep(4)
        #     ret = sport_client.FreeJump(False)
        #     print("ret: ",ret)
        elif test_option.id == 20:
            # Custom greeting sequence
            custom_behaviors.custom_greeting()
        elif test_option.id == 21:
            # Custom circle walk
            custom_behaviors.custom_circle_walk()
        elif test_option.id == 22:
            # State-aware adaptive behavior
            custom_behaviors.custom_state_aware_behavior()
        elif test_option.id == 23:
            # Test state monitoring without movement
            custom_behaviors.test_state_monitor_only()

        time.sleep(1)
