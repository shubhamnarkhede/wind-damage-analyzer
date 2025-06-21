import json
import uuid
from datetime import datetime
import boto3
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

rekognition = boto3.client("rekognition")

AREA_KEYWORDS = {
    "roof": ["roof", "shingle", "ridge"],
    "siding": ["siding", "wall", "panel"],
    "garage": ["garage"],
    "window": ["window"],
    "door": ["door"],
    "fence": ["fence"],
}

SEVERITY_THRESHOLDS = [0, 60, 75, 85, 92, 100]  # 0–4


def get_image_bytes(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"[ERROR] Could not download image from {url}: {e}")
        return None


def analyze_image(image_bytes):
    if not image_bytes:
        return None, "error", 0, 0, None

    response = rekognition.detect_labels(
        Image={"Bytes": image_bytes},
        MaxLabels=20,
        MinConfidence=50
    )
    labels = response.get("Labels", [])
    quality = 100  # Default quality

    # Debug: Print all detected labels
    # print(f"[DEBUG] Detected labels: {[label['Name'] for label in labels]}")

    wind_damage = False
    area = None
    severity = 0
    notes = ""

    for label in labels:
        lname = label["Name"].lower()
        if "wind" in lname or "damage" in lname or "debris" in lname or "shingle" in lname:
            wind_damage = True
            conf = int(label["Confidence"])
            for i, t in enumerate(SEVERITY_THRESHOLDS):
                if conf < t:
                    severity = i - 1
                    break
                severity = 4
            notes = label["Name"]
            # print(f"[DEBUG] Wind damage detected: {label['Name']} (confidence: {conf}, severity: {severity})")
        for area_name, keywords in AREA_KEYWORDS.items():
            if any(k in lname for k in keywords):
                area = area_name
                # print(f"[DEBUG] Area detected: {area_name} from label: {label['Name']}")

    if not wind_damage or not area:
        # print(f"[DEBUG] Image discarded: wind_damage={wind_damage}, area={area}")
        return None, "unrelated", 0, 0, None

    # print(f"[DEBUG] Image processed successfully: area={area}, severity={severity}")
    return area, "ok", severity, quality, notes


def process_image(url):
    img_bytes = get_image_bytes(url)
    area, status, severity, quality, notes = analyze_image(img_bytes)
    return {
        "url": url,
        "area": area,
        "status": status,
        "severity": severity,
        "quality": quality,
        "notes": notes
    }


def lambda_handler(event, context):
    try:
        body = event.get('body')
        if isinstance(body, str):
            body = json.loads(body)
        images = body.get('images', [])
        claim_id = body.get('claim_id')
        loss_type = body.get('loss_type')

        if not images:
            return {
                'statusCode': 422,
                'body': json.dumps({'error': 'images list is empty'})
            }

        # Multithreaded image processing
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(process_image, url): url for url in images}
            for future in as_completed(futures):
                results.append(future.result())

        analyzed = 0
        discarded = 0
        image_qualities = {}
        image_severities = {}
        image_areas = {}
        image_notes = {}
        area_counts = {}
        area_severity_sum = {}
        area_quality_sum = {}
        area_images = {}
        data_gaps = set()
        all_qualities = []
        all_severities = []
        all_quality_weighted = []
        rep_images = {}

        for result in results:
            url = result["url"]
            area = result["area"]
            status = result["status"]
            severity = result["severity"]
            quality = result["quality"]
            notes = result["notes"]

            if status != "ok":
                discarded += 1
                continue

            analyzed += 1

            if area not in area_images or quality > area_quality_sum.get(area, 0):
                area_images[area] = [url]
                rep_images[area] = url
                area_quality_sum[area] = quality

            area_counts[area] = area_counts.get(area, 0) + 1
            area_severity_sum[area] = area_severity_sum.get(area, 0) + severity

            all_qualities.append(quality)
            all_severities.append(severity)
            all_quality_weighted.append(severity * quality)

            image_areas[url] = area
            image_severities[url] = severity
            image_qualities[url] = quality
            image_notes[url] = notes

        areas = []
        for area in area_counts:
            count = area_counts[area]
            sev_sum = area_severity_sum[area]
            avg_sev = sev_sum / count if count else 0
            confirmed = sum(
                1 for url in area_images[area]
                if image_severities.get(url, 0) >= 2
            ) >= 2
            areas.append({
                "area": area,
                "damage_confirmed": confirmed,
                "primary_peril": "wind",
                "count": count,
                "avg_severity": round(avg_sev, 2),
                "representative_images": area_images[area],
                "notes": image_notes.get(rep_images[area], "")
            })

        if "attic" not in area_counts:
            data_gaps.add("No attic photos")

        clusters = len(area_counts)
        overall_damage_severity = 0.0
        if all_quality_weighted and all_qualities:
            overall_damage_severity = sum(all_quality_weighted) / sum(all_qualities)

        # Calculate confidence based on actual results
        if analyzed > 0:
            confidence = min(0.95, (analyzed / len(images)) * 0.9 + 0.1)
        else:
            confidence = 0.1  # Low confidence when no images analyzed

        response = {
            "claim_id": claim_id,
            "source_images": {
                "total": len(images),
                "analyzed": analyzed + discarded,
                "discarded_low_quality": discarded,
                "clusters": clusters
            },
            "overall_damage_severity": round(overall_damage_severity, 2),
            "areas": areas,
            "data_gaps": list(data_gaps),
            "confidence": confidence,
            "generated_at": datetime.utcnow().isoformat() + 'Z'
        }

        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }

    except Exception as e:
        correlation_id = str(uuid.uuid4())
        print(f"[ERROR] {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error', 'correlation_id': correlation_id})
        }
