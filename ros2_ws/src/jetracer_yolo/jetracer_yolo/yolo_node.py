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
from ultralytics import YOLO


class YoloNode(Node):

    def __init__(self):

        # Inicializacia ROS2 nody
        super().__init__('yolo_detector')

        # Konfiguracne parametre
        self.declare_parameter('model_path', '')
        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('confidence', 0.35)
        self.declare_parameter('image_size', 512)
        self.declare_parameter('device', '0')

        model_path = self.get_parameter('model_path').value
        image_topic = self.get_parameter('image_topic').value

        self.confidence = self.get_parameter('confidence').value
        self.image_size = self.get_parameter('image_size').value
        self.device = self.get_parameter('device').value

        # Kontrola existencie modelu
        if not model_path or not Path(model_path).is_file():
            raise FileNotFoundError(
                f"YOLO model neexistuje: {model_path}"
            )

        # Nacitanie natrenovaneho modelu
        self.model = YOLO(model_path)

        # Prevod medzi ROS2 Image a OpenCV
        self.bridge = CvBridge()

        # Publisher pre obraz s detekciami
        self.image_publisher = self.create_publisher(
            Image,
            '/yolo/annotated_image',
            10
        )

        # Publisher pre informacie o objektoch
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
            f"YOLO noda spustena. Model: {model_path}"
        )

    def image_callback(self, msg):

        # 1. Prevod ROS2 obrazu na OpenCV
        try:
            frame = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding='bgr8'
            )
        except CvBridgeError as error:
            self.get_logger().error(str(error))
            return

        # 2. Detekcia objektov pomocou YOLO
        result = self.model.predict(
            source=frame,
            conf=self.confidence,
            imgsz=self.image_size,
            device=self.device,
            verbose=False
        )[0]

        # 3. Priprava spravy s detekciami
        detections_msg = Detection2DArray()
        detections_msg.header = msg.header

        for box in result.boxes:

            # Trieda a skore detekcie
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())

            # Suradnice bounding boxu
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            # Vytvorenie jednej detekcie
            detection = Detection2D()
            detection.header = msg.header

            detection.bbox.center.position.x = (x1 + x2) / 2
            detection.bbox.center.position.y = (y1 + y2) / 2
            detection.bbox.center.theta = 0.0

            detection.bbox.size_x = x2 - x1
            detection.bbox.size_y = y2 - y1

            # Informacie o klasifikacii
            hypothesis = ObjectHypothesisWithPose()
            hypothesis.hypothesis.class_id = str(class_id)
            hypothesis.hypothesis.score = confidence

            detection.results.append(hypothesis)

            # Pridanie detekcie do zoznamu
            detections_msg.detections.append(detection)

        # 4. Publikovanie detekcii
        self.detection_publisher.publish(detections_msg)

        # 5. Vykreslenie bounding boxov
        annotated_frame = result.plot()

        # Prevod OpenCV obrazu na ROS2 spravu
        annotated_msg = self.bridge.cv2_to_imgmsg(
            annotated_frame,
            encoding='bgr8'
        )

        # Zachovanie casovej znacky a identifikatora kamery
        annotated_msg.header = msg.header

        # 6. Publikovanie spracovaneho obrazu
        self.image_publisher.publish(annotated_msg)


def main(args=None):

    rclpy.init(args=args)

    node = None

    try:
        node = YoloNode()
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