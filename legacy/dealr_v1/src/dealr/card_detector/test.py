import cv2
import pupil_apriltags as apriltag


def main():
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Camera could not be opened")
        return

    detector = apriltag.Detector(
        families="tag25h9",
        nthreads=4,
        quad_decimate=1.0,
        quad_sigma=0.0,
        refine_edges=True,
        decode_sharpening=0.25,
    )

    print("Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detections = detector.detect(gray)

        for det in detections:
            tag_id = det.tag_id
            corners = det.corners.astype(int)

            # Draw detection outline
            for i in range(4):
                cv2.line(
                    frame,
                    tuple(corners[i]),
                    tuple(corners[(i + 1) % 4]),
                    (0, 255, 0),
                    2,
                )

            center = tuple(det.center.astype(int))
            cv2.circle(frame, center, 5, (0, 0, 255), -1)
            cv2.putText(
                frame,
                f"ID:{tag_id}",
                (center[0] + 10, center[1]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )

        cv2.imshow("AprilTag Detection (25h9)", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
