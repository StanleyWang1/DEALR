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
    if not cap.isOpened():
        print("❌ Error: Could not open camera.")
        return

    print("📷 Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Failed to grab frame.")
            break

        # Run YOLO inference
        results = model.predict(source=frame, verbose=False)

        # Draw detections on frame
        # annotated_frame = results[0].plot()

        socket.send_json(results)

        # Display result
        # cv2.imshow("Live Card Detection", annotated_frame)

        # Quit on 'q'
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
