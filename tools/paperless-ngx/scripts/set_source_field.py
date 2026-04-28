#!/usr/bin/env python3
import os
import re
import sys


SRC_FIELD = "来源"
OPTIONS = {
    "audio": {"id": "audio", "label": "音频"},
    "image": {"id": "image", "label": "图片"},
    "document": {"id": "document", "label": "文档"},
}

AUDIO_EXTS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".wma",
    ".amr",
}
IMAGE_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".heic",
    ".tif",
    ".tiff",
    ".bmp",
}


def classify(source_path: str, original_filename: str) -> str:
    haystack = f"{source_path}\n{original_filename}".lower()
    ext = os.path.splitext(original_filename.lower())[1]

    if ext in AUDIO_EXTS or re.search(r"(^|[/_.-])(_?asr|audio|voice|tts|语音)([/_.-]|$)", haystack):
        return "audio"
    if ext in IMAGE_EXTS or re.search(r"(^|[/_.-])(image|img|ocr|scan|图片|图像)([/_.-]|$)", haystack):
        return "image"
    return "document"


def main() -> int:
    document_id = os.environ.get("DOCUMENT_ID") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not document_id:
        print("DOCUMENT_ID is missing", file=sys.stderr)
        return 1

    source_path = os.environ.get("DOCUMENT_SOURCE_PATH", "")
    original_filename = os.environ.get("DOCUMENT_ORIGINAL_FILENAME", "")

    sys.path.insert(0, "/usr/src/paperless/src")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperless.settings")

    import django

    django.setup()

    from documents.models import CustomField, CustomFieldInstance, Document

    option_key = classify(source_path, original_filename)
    options = list(OPTIONS.values())
    field, created = CustomField.objects.get_or_create(
        name=SRC_FIELD,
        defaults={
            "data_type": CustomField.FieldDataType.SELECT,
            "extra_data": {"select_options": options},
        },
    )

    if not created:
        if field.data_type != CustomField.FieldDataType.SELECT:
            print(f"Custom field {SRC_FIELD!r} exists but is not a select field", file=sys.stderr)
            return 1
        existing = {item.get("id"): item for item in field.extra_data.get("select_options", [])}
        changed = False
        for option in options:
            if option["id"] not in existing:
                field.extra_data.setdefault("select_options", []).append(option)
                changed = True
        if changed:
            field.save(update_fields=["extra_data"])

    document = Document.objects.get(pk=document_id)
    instance, _ = CustomFieldInstance.objects.get_or_create(document=document, field=field)
    instance.value_select = OPTIONS[option_key]["id"]
    instance.save(update_fields=["value_select"])

    print(f"Set {SRC_FIELD}={OPTIONS[option_key]['label']} for document {document_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
