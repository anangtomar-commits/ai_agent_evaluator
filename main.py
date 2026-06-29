import json
import sys

from extractor.extractor import extract


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_file.pdf|docx>")
        sys.exit(1)

    file_path = sys.argv[1]
    result = extract(file_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
