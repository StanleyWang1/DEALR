import cv2
import pupil_apriltags as apriltag
import numpy as np

# Map AprilTag IDs to card names and values
CARD_MAP = {
    1: ("AH", 1),
    2: ("2H", 2),
    3: ("3H", 3),
    4: ("4H", 4),
    5: ("5H", 5),
    6: ("6H", 6),
    7: ("7H", 7),
    8: ("8H", 8),
    9: ("9H", 9),
    10: ("10H", 10),
    11: ("JH", 10),
    12: ("QH", 10),
    13: ("KH", 10),
}


def get_color_and_label(cards):
    if not cards:
        return (0, 255, 255), "None"  # Yellow when no cards
    total = sum(value for _, value in cards)
    color = (0, 255, 0) if total <= 21 else (0, 0, 255)  # Green or Red
    label = ", ".join(label for label, _ in cards)
    return color, label


def draw_rectangle(frame, corners1, corners2, label_text, role_text, color):
    # Compute bounds
    x_min = int(min(corners1[:, 0].min(), corners2[:, 0].min()))
    x_max = int(max(corners1[:, 0].max(), corners2[:, 0].max()))
    y_min = int(min(corners1[:, 1].min(), corners2[:, 1].min()))
    y_max = int(max(corners1[:, 1].max(), corners2[:, 1].max()))

    # Draw rectangle
    cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 2)

    # Role label (top-left)
    cv2.putText(
        frame,
        role_text,
        (x_min, y_min - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2,
        cv2.LINE_AA,
    )

    # Cards label (bottom-right)
    cv2.putText(
        frame,
        label_text,
        (x_max - 150, y_max + 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2,
        cv2.LINE_AA,
    )

    return x_min, x_max, y_min, y_max


def main():
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("❌ Error: Could not open camera.")
        return

    detector = apriltag.Detector(
        families="tag25h9",
        nthreads=4,
        quad_decimate=1.0,
        quad_sigma=0.0,
        refine_edges=True,
        decode_sharpening=0.25,
    )

    print("📷 Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detections = detector.detect(gray)

        tag_corners = {det.tag_id: det.corners for det in detections}

        # Annotate each card individually
        for det in detections:
            if det.tag_id in CARD_MAP:
                label, _ = CARD_MAP[det.tag_id]
                center = det.center.astype(int)
                cv2.putText(
                    frame,
                    label,
                    (center[0] - 20, center[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

        # Draw rectangles for PLAYER (21–22) and DEALER (23–24)
        for id1, id2, role_text in [(21, 22, "PLAYER"), (23, 24, "DEALER")]:
            if id1 in tag_corners and id2 in tag_corners:
                # Get cards inside
                cards_inside = []
                x_min = min(tag_corners[id1][:, 0].min(), tag_corners[id2][:, 0].min())
                x_max = max(tag_corners[id1][:, 0].max(), tag_corners[id2][:, 0].max())
                y_min = min(tag_corners[id1][:, 1].min(), tag_corners[id2][:, 1].min())
                y_max = max(tag_corners[id1][:, 1].max(), tag_corners[id2][:, 1].max())

                for det in detections:
                    if det.tag_id in CARD_MAP:
                        cx, cy = det.center
                        if x_min <= cx <= x_max and y_min <= cy <= y_max:
                            cards_inside.append(CARD_MAP[det.tag_id])

                color, label_text = get_color_and_label(cards_inside)

                draw_rectangle(
                    frame,
                    tag_corners[id1],
                    tag_corners[id2],
                    label_text,
                    role_text,
                    color,
                )

        cv2.imshow("AprilTag Blackjack", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
