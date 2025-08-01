<<<<<<< Updated upstream:src/dealr/card_detector/video_stream.py
"""Live Card Detection Driver"""

from pathlib import Path

import cv2
from ultralytics import YOLO  # type: ignore
import zmq


def main() -> None:
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:5555")

    # Load a pretrained model
    model_path = Path("models") / "best.pt"
    model = YOLO(model_path)

    # Initialize camera (0 = default webcam)
    cap = cv2.VideoCapture(0)
=======
import cv2
from pathlib import Path
from ultralytics import YOLO
import multiprocessing as mp
import pupil_apriltags as apriltag
import numpy as np
import time


def detect_apriltags(frame_queue, tag_queue):
    detector = apriltag.Detector(
        families="tag25h9",
        nthreads=4,
        quad_decimate=1.0,
        quad_sigma=0.0,
        refine_edges=True,
        decode_sharpening=0.25,
    )

    while True:
        frame = frame_queue.get()
        if frame is None:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detections = detector.detect(gray)

        tag_data = {}
        for det in detections:
            if det.tag_id in [21, 22, 23, 24]:
                tag_data[det.tag_id] = det.corners

        tag_queue.put(tag_data)


def draw_rectangle_with_label(frame, tag_data, id1, id2, card_labels):
    if id1 in tag_data and id2 in tag_data:
        c1 = np.mean(tag_data[id1], axis=0).astype(int)
        c2 = np.mean(tag_data[id2], axis=0).astype(int)
        cv2.rectangle(frame, tuple(c1), tuple(c2), (0, 255, 0), 2)

        # Compute bottom-middle of rectangle
        bottom_center = ((c1[0] + c2[0]) // 2, max(c1[1], c2[1]) + 20)

        label_text = ", ".join(card_labels) if card_labels else "None"
        cv2.putText(
            frame,
            label_text,
            bottom_center,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )


def main():
    model_path = Path("./src/card_detector/models/best.pt")
    model = YOLO(model_path)

    cap = cv2.VideoCapture(1)
>>>>>>> Stashed changes:src/card_detector/video_stream.py
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    frame_queue = mp.Queue(maxsize=2)
    tag_queue = mp.Queue()

    tag_process = mp.Process(target=detect_apriltags, args=(frame_queue, tag_queue))
    tag_process.start()

    current_tags = {}
    prev_time = time.time()
    fps = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if not frame_queue.full():
            frame_queue.put(frame.copy())

        start = time.time()
        results = model.predict(source=frame, verbose=False)
        annotated_frame = frame.copy()

<<<<<<< Updated upstream:src/dealr/card_detector/video_stream.py
        # Draw detections on frame
        # annotated_frame = results[0].plot()

        socket.send_json(results)

        # Display result
        # cv2.imshow("Live Card Detection", annotated_frame)
=======
        detected_cards = []
        for r in results[0].boxes:
            conf = float(r.conf[0])
            if conf >= 0.5:
                xyxy = r.xyxy[0].cpu().numpy().astype(int)
                cls = int(r.cls[0])
                label = results[0].names[cls]
                detected_cards.append((label, xyxy))

                cv2.rectangle(annotated_frame, xyxy[:2], xyxy[2:], (255, 0, 0), 2)
                cv2.putText(
                    annotated_frame,
                    f"{label} {conf:.2f}",
                    (xyxy[0], xyxy[1] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 0, 0),
                    1,
                )

        # Update FPS
        end = time.time()
        fps = 1.0 / (end - prev_time)
        prev_time = end

        # Update tag data
        while not tag_queue.empty():
            current_tags = tag_queue.get()

        # Determine which cards are inside each rectangle
        cards_rect1, cards_rect2 = [], []
        if current_tags:
            if 21 in current_tags and 22 in current_tags:
                rect1_xmin = min(current_tags[21][:, 0].min(), current_tags[22][:, 0].min())
                rect1_xmax = max(current_tags[21][:, 0].max(), current_tags[22][:, 0].max())
                rect1_ymin = min(current_tags[21][:, 1].min(), current_tags[22][:, 1].min())
                rect1_ymax = max(current_tags[21][:, 1].max(), current_tags[22][:, 1].max())

                for label, xyxy in detected_cards:
                    cx, cy = (xyxy[0] + xyxy[2]) // 2, (xyxy[1] + xyxy[3]) // 2
                    if rect1_xmin <= cx <= rect1_xmax and rect1_ymin <= cy <= rect1_ymax:
                        cards_rect1.append(label)

            if 23 in current_tags and 24 in current_tags:
                rect2_xmin = min(current_tags[23][:, 0].min(), current_tags[24][:, 0].min())
                rect2_xmax = max(current_tags[23][:, 0].max(), current_tags[24][:, 0].max())
                rect2_ymin = min(current_tags[23][:, 1].min(), current_tags[24][:, 1].min())
                rect2_ymax = max(current_tags[23][:, 1].max(), current_tags[24][:, 1].max())

                for label, xyxy in detected_cards:
                    cx, cy = (xyxy[0] + xyxy[2]) // 2, (xyxy[1] + xyxy[3]) // 2
                    if rect2_xmin <= cx <= rect2_xmax and rect2_ymin <= cy <= rect2_ymax:
                        cards_rect2.append(label)

            draw_rectangle_with_label(annotated_frame, current_tags, 21, 22, cards_rect1)
            draw_rectangle_with_label(annotated_frame, current_tags, 23, 24, cards_rect2)

        # Show FPS at top-right
        h, w = annotated_frame.shape[:2]
        cv2.putText(
            annotated_frame,
            f"FPS: {fps:.1f}",
            (w - 150, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.imshow("Live Card Detection", annotated_frame)
>>>>>>> Stashed changes:src/card_detector/video_stream.py

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    frame_queue.put(None)
    tag_process.join()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
