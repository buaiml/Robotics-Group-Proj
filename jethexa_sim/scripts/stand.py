#!/usr/bin/env python3
"""Smoke test: push the robot into a static tripod-ready stance and hold it.

    ros2 run jethexa_sim stand.py

If the robot settles on six feet without sinking or sliding, the model,
controllers and contact parameters are wired up correctly. This is the only
motion shipped in the starter env - gaits are the students' job.
"""
import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

# Joint order must match config/controllers.yaml
LEGS = ["lf", "lm", "lr", "rf", "rm", "rr"]

COXA = 0.0
FEMUR = math.radians(-35.0)
TIBIA = math.radians(75.0)


class Stand(Node):
    def __init__(self):
        super().__init__("jethexa_stand")
        self.pub = self.create_publisher(
            Float64MultiArray, "/joint_group_position_controller/commands", 10
        )
        self.msg = Float64MultiArray()
        self.msg.data = [COXA, FEMUR, TIBIA] * len(LEGS)
        self.create_timer(0.05, lambda: self.pub.publish(self.msg))
        self.get_logger().info("holding stance: coxa=%.2f femur=%.2f tibia=%.2f rad"
                               % (COXA, FEMUR, TIBIA))


def main():
    rclpy.init()
    node = Stand()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
