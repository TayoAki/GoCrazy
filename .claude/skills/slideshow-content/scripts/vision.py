"""The parts of the video tools that need machine-learning models. Runs in the skill's own Python environment
(~/.cache/slideshow-content/venv, made by videokit.py on first use), never in the system Python.

    vision.py words <media> <out.json> [--model small] [--language en]   # every word with its start and end, in seconds
    vision.py face <video>                                               # where the face is: JSON on stdout
    vision.py matte <video> <out.mkv>                                    # a grey mask video: white where the person is

words uses faster-whisper on the CPU (the model downloads once, about 500 MB for "small"). face and matte use
MediaPipe's face detector and selfie segmentation, which ship inside the package.
"""

import argparse
import json
import subprocess
import sys

import numpy as np


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True)
    info = json.loads(out.stdout)
    s = info["streams"][0]
    w, h = s["width"], s["height"]
    rot = next((abs(int(d.get("rotation", 0))) for d in s.get("side_data_list", []) if "rotation" in d), 0)
    if rot in (90, 270):
        w, h = h, w
    return w, h, float(info["format"]["duration"])


def frames(path, width, height, fps=None, at=None):
    """Decoded RGB frames as numpy arrays, at a size and rate, or one frame at each time in `at`."""
    if at is not None:
        for t in at:
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-vf",
                                  f"scale={width}:{height}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                 capture_output=True, check=True).stdout
            if len(raw) == width * height * 3:
                yield t, np.frombuffer(raw, np.uint8).reshape(height, width, 3)
        return
    vf = f"fps={fps},scale={width}:{height}" if fps else f"scale={width}:{height}"
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            stdout=subprocess.PIPE)
    size = width * height * 3
    while True:
        raw = proc.stdout.read(size)
        if len(raw) < size:
            break
        yield None, np.frombuffer(raw, np.uint8).reshape(height, width, 3)
    proc.wait()


def words(args):
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    segments, info = model.transcribe(args.media, word_timestamps=True, vad_filter=True, language=args.language)
    out = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                out.append({"w": text, "s": round(w.start, 3), "e": round(w.end, 3)})
    json.dump(out, open(args.out, "w"), indent=0, ensure_ascii=False)
    print(json.dumps({"words": len(out), "language": info.language, "duration": round(info.duration, 2)}))


def face(args):
    """Median centre and size of the largest face over 24 frames, as fractions of the frame."""
    import mediapipe as mp
    w, h, dur = probe(args.video)
    sw, sh = 640, max(2, round(640 * h / w / 2) * 2)
    times = [dur * (k + 0.5) / 24 for k in range(24)]
    found = []
    with mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as det:
        for _, img in frames(args.video, sw, sh, at=times):
            res = det.process(img)
            if res.detections:
                b = max((d.location_data.relative_bounding_box for d in res.detections), key=lambda b: b.width * b.height)
                found.append((b.xmin + b.width / 2, b.ymin + b.height / 2, b.width, b.height))
    if not found:
        print(json.dumps({"found": 0, "of": len(times), "width": w, "height": h}))
        return
    a = np.array(found)
    print(json.dumps({"found": len(found), "of": len(times), "x": round(float(np.median(a[:, 0])), 4),
                      "y": round(float(np.median(a[:, 1])), 4), "w": round(float(np.median(a[:, 2])), 4),
                      "h": round(float(np.median(a[:, 3])), 4), "width": w, "height": h}))


def matte(args):
    """Selfie segmentation, frame by frame, with soft edges and a little smoothing over time so the edge doesn't
    shimmer. Written losslessly (FFV1, grey) so ffmpeg's alphamerge can use it as the person's alpha."""
    import mediapipe as mp
    w, h, _ = probe(args.video)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}",
                            "-r", str(args.fps), "-i", "-", "-c:v", "ffv1", "-pix_fmt", "gray", args.out],
                           stdin=subprocess.PIPE)
    prev = None
    n = 0
    with mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=0) as seg:
        for _, img in frames(args.video, w, h, fps=args.fps):
            m = seg.process(img).segmentation_mask.astype(np.float32)
            m = np.clip((m - 0.35) / 0.3, 0, 1)                        # a firm body with a soft edge
            prev = m if prev is None else 0.6 * m + 0.4 * prev        # steadier edge from frame to frame
            enc.stdin.write((prev * 255).astype(np.uint8).tobytes())
            n += 1
    enc.stdin.close()
    enc.wait()
    print(json.dumps({"frames": n}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("words")
    p.add_argument("media")
    p.add_argument("out")
    p.add_argument("--model", default="small")
    p.add_argument("--language", default=None)
    p.set_defaults(fn=words)
    p = sub.add_parser("face")
    p.add_argument("video")
    p.set_defaults(fn=face)
    p = sub.add_parser("matte")
    p.add_argument("video")
    p.add_argument("out")
    p.add_argument("--fps", type=int, default=30)
    p.set_defaults(fn=matte)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
