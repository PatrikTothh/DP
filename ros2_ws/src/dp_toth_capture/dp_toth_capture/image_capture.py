import os
import select
import termios
import time
import tty

import cv2

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CompressedImage
from std_srvs.srv import Trigger, SetBool
from cv_bridge import CvBridge, CvBridgeError

from dp_toth_capture.image_storage import ImageStorage


# --------------------------------------------------
# Ovladanie priamo z terminalu
# --------------------------------------------------

class TerminalKeyboard:

    def __init__(self):

        self.fd = None
        self.original_settings = None

        try:
            # Priamy pristup k terminalu, v ktorom bezi ros2 launch
            self.fd = os.open(
                '/dev/tty',
                os.O_RDONLY | os.O_NONBLOCK
            )

            # Ulozenie povodnych nastaveni terminalu
            self.original_settings = termios.tcgetattr(self.fd)

            # Nacitanie klavesov bez potreby stlacit Enter
            tty.setcbreak(self.fd)

        except (OSError, termios.error):
            self.close()

    def read_key(self):

        if self.fd is None:
            return None

        try:
            ready, _, _ = select.select(
                [self.fd], [], [], 0
            )

            if ready:
                data = os.read(self.fd, 1)

                if data:
                    return data.decode(
                        'utf-8',
                        errors='ignore'
                    ).lower()

        except (OSError, ValueError):
            pass

        return None

    def close(self):

        if self.fd is not None:

            if self.original_settings is not None:

                try:
                    termios.tcsetattr(
                        self.fd,
                        termios.TCSADRAIN,
                        self.original_settings
                    )

                except (OSError, termios.error):
                    pass

            os.close(self.fd)
            self.fd = None


# --------------------------------------------------
# ROS2 Image Capture
# --------------------------------------------------

class ImageCapture(Node):

    def __init__(self):

        super().__init__('image_capture')

        # ROS2 parametre
        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('output_dir', '~/DP/datasets/captured')
        self.declare_parameter('session_name', 'default')
        self.declare_parameter('capture_interval', 0.5)
        self.declare_parameter('auto_capture', False)
        self.declare_parameter('show_preview', False)
        self.declare_parameter('image_format', 'jpg')
        self.declare_parameter('jpeg_quality', 95)

        # Nacitanie parametrov
        self.image_topic = self.get_parameter(
            'image_topic'
        ).value

        output_dir = self.get_parameter(
            'output_dir'
        ).value

        session_name = self.get_parameter(
            'session_name'
        ).value

        self.capture_interval = self.get_parameter(
            'capture_interval'
        ).value

        self.auto_capture = self.get_parameter(
            'auto_capture'
        ).value

        self.show_preview = self.get_parameter(
            'show_preview'
        ).value

        image_format = self.get_parameter(
            'image_format'
        ).value

        jpeg_quality = self.get_parameter(
            'jpeg_quality'
        ).value

        if self.capture_interval <= 0:
            raise ValueError(
                "capture_interval musi byt vacsi ako 0."
            )

        # Inicializacia ukladania
        self.storage = ImageStorage(
            output_dir=output_dir,
            image_format=image_format,
            jpeg_quality=jpeg_quality,
            session_name=session_name
        )

        # ROS2 - OpenCV konverzia
        self.bridge = CvBridge()

        # Posledna prijata snimka
        self.latest_frame = None

        # Stav prijimania obrazu
        self.first_frame_received = False

        # Automaticke zachytavanie
        self.last_capture_time = None

        # Ukoncenie aplikacie
        self.exit_requested = False

        # Graficke rozhranie
        self.window_name = "DP Toth - Image Capture"

        if self.show_preview:

            cv2.namedWindow(
                self.window_name,
                cv2.WINDOW_NORMAL
            )

        # Terminalove ovladanie
        self.keyboard = None

        if not self.show_preview:

            self.keyboard = TerminalKeyboard()

            if self.keyboard.fd is None:

                self.get_logger().warning(
                    "Terminalove ovladanie nie je dostupne. "
                    "Pouzi ROS2 sluzby."
                )

        # --------------------------------------------------
        # ROS2 Subscriber
        # --------------------------------------------------

        # Rozpoznanie komprimovaneho topicu
        self.is_compressed = self.image_topic.rstrip(
            '/'
        ).endswith('/compressed')

        if self.is_compressed:
            message_type = CompressedImage
        else:
            message_type = Image

        self.subscription = self.create_subscription(
            message_type,
            self.image_topic,
            self.image_callback,
            qos_profile_sensor_data
        )

        # Kontrola, ci skutocne prichadzaju snimky
        self.connection_timer = self.create_timer(
            5.0,
            self.check_connection
        )

        # --------------------------------------------------
        # ROS2 Services
        # --------------------------------------------------

        self.save_service = self.create_service(
            Trigger,
            '~/save',
            self.save_callback
        )

        self.auto_service = self.create_service(
            SetBool,
            '~/set_auto',
            self.auto_callback
        )

        # --------------------------------------------------
        # Logovanie
        # --------------------------------------------------

        self.get_logger().info(
            "Image Capture spusteny."
        )

        self.get_logger().info(
            f"Cakam na obraz z topicu: {self.image_topic}"
        )

        self.get_logger().info(
            f"Typ spravy: {message_type.__name__}"
        )

        self.get_logger().info(
            f"Ukladanie do: {self.storage.session_dir}"
        )

        self.get_logger().info(
            f"Interval: {self.capture_interval} s"
        )

        self.get_logger().info(
            f"Auto capture: {self.auto_capture}"
        )

        if self.keyboard is not None and self.keyboard.fd is not None:

            self.get_logger().info(
                "Ovladanie terminalu: "
                "C - Save | A - Auto ON | "
                "D - Auto OFF | Q - Quit"
            )

    # --------------------------------------------------
    # Kontrola spojenia s kamerou
    # --------------------------------------------------

    def check_connection(self):

        if not self.first_frame_received:

            self.get_logger().warning(
                f"Zatial neprisla ziadna snimka "
                f"z topicu: {self.image_topic}"
            )

        else:

            # Po prijati prvej snimky uz kontrolu nepotrebujeme
            self.connection_timer.cancel()

    # --------------------------------------------------
    # Ukladanie obrazkov
    # --------------------------------------------------

    def save_frame(self, frame, capture_mode):

        try:

            path = self.storage.save(
                frame,
                capture_mode=capture_mode
            )

            self.get_logger().info(
                f"Ulozeny obrazok: {path.name}"
            )

            return path

        except Exception as error:

            self.get_logger().error(
                f"Chyba pri ukladani: {error}"
            )

            return None

    # --------------------------------------------------
    # Manualne zachytavanie
    # --------------------------------------------------

    def capture_manual(self):

        if self.latest_frame is None:

            self.get_logger().warning(
                "Nie je dostupna ziadna snimka z kamery."
            )

            return None

        return self.save_frame(
            self.latest_frame,
            "manual"
        )

    # --------------------------------------------------
    # Automaticke zachytavanie
    # --------------------------------------------------

    def set_auto_capture(self, enabled):

        self.auto_capture = enabled

        if enabled:

            self.last_capture_time = None

            self.get_logger().info(
                "Automaticke zachytavanie ZAPNUTE."
            )

        else:

            self.get_logger().info(
                "Automaticke zachytavanie VYPNUTE."
            )

    # --------------------------------------------------
    # Ovladanie cez terminal
    # --------------------------------------------------

    def handle_key(self, key):

        # C - Manualne ulozenie
        if key == 'c':

            self.capture_manual()

        # A - Auto ON
        elif key == 'a':

            self.set_auto_capture(True)

        # D - Auto OFF
        elif key == 'd':

            self.set_auto_capture(False)

        # Q - Ukoncenie
        elif key == 'q':

            self.get_logger().info(
                "Ukoncujem Image Capture..."
            )

            self.exit_requested = True

    # --------------------------------------------------
    # ROS2 Service - Manualne ulozenie
    # --------------------------------------------------

    def save_callback(self, request, response):

        path = self.capture_manual()

        response.success = path is not None

        if response.success:

            response.message = (
                f"Obrazok ulozeny: {path}"
            )

        else:

            response.message = (
                "Obrazok sa nepodarilo ulozit."
            )

        return response

    # --------------------------------------------------
    # ROS2 Service - Auto capture
    # --------------------------------------------------

    def auto_callback(self, request, response):

        self.set_auto_capture(request.data)

        response.success = True

        response.message = (
            "Auto capture ON"
            if self.auto_capture
            else "Auto capture OFF"
        )

        return response

    # --------------------------------------------------
    # Prijimanie obrazu z kamery
    # --------------------------------------------------

    def image_callback(self, msg):

        try:

            # Komprimovany obraz
            if self.is_compressed:

                frame = self.bridge.compressed_imgmsg_to_cv2(
                    msg,
                    desired_encoding='bgr8'
                )

            # Nekomprimovany obraz
            else:

                frame = self.bridge.imgmsg_to_cv2(
                    msg,
                    desired_encoding='bgr8'
                )

        except (CvBridgeError, Exception) as error:

            self.get_logger().error(
                f"Chyba pri konverzii obrazu: {error}"
            )

            return

        if frame is None:

            self.get_logger().warning(
                "Prijata snimka sa nepodarila dekodovat."
            )

            return

        # --------------------------------------------------
        # Potvrdenie prijatia prvej snimky
        # --------------------------------------------------

        if not self.first_frame_received:

            self.first_frame_received = True

            height, width = frame.shape[:2]

            self.get_logger().info(
                f"USPESNE PRIJATY OBRAZ z topicu: "
                f"{self.image_topic}"
            )

            self.get_logger().info(
                f"Rozlisenie obrazu: {width}x{height}"
            )

        # Posledna prijata snimka
        self.latest_frame = frame

        # --------------------------------------------------
        # Automaticke zachytavanie
        # --------------------------------------------------

        current_time = time.monotonic()

        if self.auto_capture:

            if (
                self.last_capture_time is None
                or current_time - self.last_capture_time
                >= self.capture_interval
            ):

                if self.save_frame(frame, "auto") is not None:

                    self.last_capture_time = current_time

        # --------------------------------------------------
        # Graficke rozhranie (volitelne)
        # --------------------------------------------------

        if not self.show_preview:
            return

        preview = frame.copy()

        status = (
            "AUTO ON"
            if self.auto_capture
            else "AUTO OFF"
        )

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
            (0, 255, 0)
            if self.auto_capture
            else (255, 255, 255),
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

        cv2.imshow(
            self.window_name,
            preview
        )

        key = cv2.waitKey(1) & 0xFF

        if key != 255:

            self.handle_key(
                chr(key).lower()
            )

    # --------------------------------------------------
    # Ukoncenie
    # --------------------------------------------------

    def cleanup(self):

        # Obnovenie povodnych nastaveni terminalu
        if self.keyboard is not None:
            self.keyboard.close()

        if self.show_preview:
            cv2.destroyAllWindows()


# --------------------------------------------------
# Main
# --------------------------------------------------

def main(args=None):

    rclpy.init(args=args)

    node = None

    try:

        node = ImageCapture()

        while rclpy.ok() and not node.exit_requested:

            # ROS2 komunikacia
            rclpy.spin_once(
                node,
                timeout_sec=0.05
            )

            # Nacitanie klavesov z terminalu
            if node.keyboard is not None:

                key = node.keyboard.read_key()

                while key is not None:

                    node.handle_key(key)

                    if node.exit_requested:
                        break

                    key = node.keyboard.read_key()

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