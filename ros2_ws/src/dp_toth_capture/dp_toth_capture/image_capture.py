import time

import cv2

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

from dp_toth_capture.image_storage import ImageStorage


class ImageCapture(Node):

    def __init__(self):

        super().__init__('image_capture')

        # ROS2 parametre
        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('output_dir', '~/DP/datasets/captured')
        self.declare_parameter('capture_interval', 0.5)
        self.declare_parameter('auto_capture', False)
        self.declare_parameter('show_preview', True)
        self.declare_parameter('image_format', 'jpg')
        self.declare_parameter('jpeg_quality', 95)
        self.declare_parameter('session_name', 'default')

        # Nacitanie parametrov
        image_topic = self.get_parameter('image_topic').value
        output_dir = self.get_parameter('output_dir').value
        session_name = self.get_parameter('session_name').value

        self.capture_interval = self.get_parameter(
            'capture_interval'
        ).value

        self.auto_capture = self.get_parameter(
            'auto_capture'
        ).value

        self.show_preview = self.get_parameter(
            'show_preview'
        ).value

        image_format = self.get_parameter('image_format').value
        jpeg_quality = self.get_parameter('jpeg_quality').value

        if self.capture_interval <= 0:
            raise ValueError("capture_interval musi byt vacsi ako 0.")

        # Inicializacia ukladania
        self.storage = ImageStorage(
            output_dir=output_dir,
            image_format=image_format,
            jpeg_quality=jpeg_quality
        )

        # ROS2 - OpenCV konverzia
        self.bridge = CvBridge()

        # Cas posledneho automatickeho ulozenia
        self.last_capture_time = None

        # Ukoncenie aplikacie
        self.exit_requested = False

        # Nazov okna
        self.window_name = "DP Toth - Image Capture"

        if self.show_preview:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

        # ROS2 subscriber
        self.subscription = self.create_subscription(
            Image,
            image_topic,
            self.image_callback,
            qos_profile_sensor_data
        )

        self.get_logger().info(
            f"Image capture spusteny. Topic: {image_topic}"
        )

        self.get_logger().info(
            f"Ukladanie do: {self.storage.session_dir}"
        )

        self.get_logger().info(
            "Ovladanie: C - ulozit, A - auto ON, "
            "D - auto OFF, Q - koniec"
        )

    def save_frame(self, frame, capture_mode):

        try:
            path = self.storage.save(
                frame,
                capture_mode=capture_mode
            )

            self.get_logger().info(
                f"Ulozeny obrazok: {path.name}"
            )

            return True

        except Exception as error:

            self.get_logger().error(
                f"Chyba pri ukladani: {error}"
            )

            return False

    def image_callback(self, msg):

        # Prevod ROS2 Image na OpenCV
        try:
            frame = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding='bgr8'
            )

        except CvBridgeError as error:

            self.get_logger().error(str(error))
            return

        # Automaticke zachytavanie
        current_time = time.monotonic()

        if self.auto_capture:

            if (
                self.last_capture_time is None
                or current_time - self.last_capture_time
                >= self.capture_interval
            ):

                if self.save_frame(frame, "auto"):
                    self.last_capture_time = current_time

        # Graficke rozhranie
        if self.show_preview:

            # Kopia obrazu iba pre zobrazenie
            preview = frame.copy()

            status = "AUTO ON" if self.auto_capture else "AUTO OFF"

            cv2.rectangle(
                preview,
                (0, 0),
                (preview.shape[1], 65),
                (0, 0, 0),
                -1
            )

            cv2.putText(
                preview,
                f"Capture: {status}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0) if self.auto_capture else (255, 255, 255),
                2
            )

            cv2.putText(
                preview,
                "C: Save | A: Auto ON | D: Auto OFF | Q: Quit",
                (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1
            )

            cv2.imshow(self.window_name, preview)

            # Nacitanie klavesy
            key = cv2.waitKey(1) & 0xFF

            if key in (ord('c'), ord('C')):

                self.save_frame(frame, "manual")

            elif key in (ord('a'), ord('A')):

                self.auto_capture = True
                self.last_capture_time = None

                self.get_logger().info(
                    "Automaticke zachytavanie zapnute."
                )

            elif key in (ord('d'), ord('D')):

                self.auto_capture = False

                self.get_logger().info(
                    "Automaticke zachytavanie vypnute."
                )

            elif key in (ord('q'), ord('Q')):

                self.exit_requested = True

    def cleanup(self):

        if self.show_preview:
            cv2.destroyAllWindows()


def main(args=None):

    rclpy.init(args=args)

    node = None

    try:

        node = ImageCapture()

        while rclpy.ok() and not node.exit_requested:

            rclpy.spin_once(
                node,
                timeout_sec=0.1
            )

    except KeyboardInterrupt:
        pass

    finally:

        if node is not None:

            node.cleanup()
            node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()