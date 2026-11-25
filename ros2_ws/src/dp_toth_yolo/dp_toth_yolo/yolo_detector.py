from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image
from vision_msgs.msg import (
    Detection2D,
    Detection2DArray,
    ObjectHypothesisWithPose
)

from cv_bridge import CvBridge, CvBridgeError

from dp_toth_yolo.yolo_inference import YoloInference


class YoloDetector(Node):

    def __init__(self):

        super().__init__('yolo_detector')

        # ROS2 parametre
        self.declare_parameter('model_path', '')
        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('confidence', 0.35)
        self.declare_parameter('image_size', 512)
        self.declare_parameter('device', '0')

        # Nacitanie parametrov
        model_path = self.get_parameter('model_path').value
        image_topic = self.get_parameter('image_topic').value
        confidence = self.get_parameter('confidence').value
        image_size = self.get_parameter('image_size').value
        device = self.get_parameter('device').value

        # Kontrola modelu
        if not model_path or not Path(model_path).is_file():
            raise FileNotFoundError(
                f"YOLO model neexistuje: {model_path}"
            )

        # Inicializacia YOLO
        self.detector = YoloInference(
            model_path=model_path,
            confidence=confidence,
            image_size=image_size,
            device=device
        )

        # ROS2 - OpenCV konverzia
        self.bridge = CvBridge()

        # Publisher pre obraz s detekciami
        self.image_publisher = self.create_publisher(
            Image,
            '/yolo/annotated_image',
            10
        )

        # Publisher pre detegovane objekty
        self.detection_publisher = self.create_publisher(
            Detection2DArray,
            '/yolo/detections',
            10
        )

        # Subscriber na obraz z kamery
        self.subscription = self.create_subscription(
            Image,
            image_topic,
            self.image_callback,
            qos_profile_sensor_data
        )

        self.get_logger().info(
            f"YOLO detector spusteny. Model: {model_path}"
        )

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

        # Detekcia objektov
        result = self.detector.predict(frame)

        # Vytvorenie spravy s detekciami
        detections_msg = Detection2DArray()
        detections_msg.header = msg.header

        if result.boxes is not None:

            for box in result.boxes:

                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())

                x1, y1, x2, y2 = box.xyxy[0].tolist()

                # Vytvorenie detekcie
                detection = Detection2D()
                detection.header = msg.header

                # Bounding box
                detection.bbox.center.position.x = (x1 + x2) / 2
                detection.bbox.center.position.y = (y1 + y2) / 2

                detection.bbox.size_x = x2 - x1
                detection.bbox.size_y = y2 - y1

                # Klasifikacia
                hypothesis = ObjectHypothesisWithPose()

                hypothesis.hypothesis.class_id = str(class_id)
                hypothesis.hypothesis.score = confidence

                detection.results.append(hypothesis)
                detections_msg.detections.append(detection)

        # Publikovanie detekcii
        self.detection_publisher.publish(detections_msg)

        # Vykreslenie detekcii do obrazu
        annotated_frame = result.plot()

        # Konverzia OpenCV na ROS2 Image
        annotated_msg = self.bridge.cv2_to_imgmsg(
            annotated_frame,
            encoding='bgr8'
        )

        annotated_msg.header = msg.header

        # Publikovanie obrazu
        self.image_publisher.publish(annotated_msg)


def main(args=None):

    rclpy.init(args=args)

    node = None

    try:
        node = YoloDetector()
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        if node is not None:
            node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()