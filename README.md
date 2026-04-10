# Immich Face Tag Sync

Finds photos that carry a Google Photos person tag (e.g. `People/Paul-McCartney`) but are **not** assigned to the matching person in [Immich](https://immich.app/)'s face recognition.

Useful after migrating a Google Photos library to Immich: your photos may already have person tags from Google Takeout, but Immich's face recognition hasn't linked them to the correct person yet. This script shows you exactly which photos need attention.

## Requirements

- Python 3.10+

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

### Command-line arguments

```bash
python unmatched_faces.py \
    --tag "People/Paul-McCartney" \
    --person "Paul McCartney" \
    --url "http://192.168.1.10:2283" \
    --key "your_api_key"
```

| Argument   | Description                                              |
|------------|----------------------------------------------------------|
| `--tag`    | Google Photos tag value as it appears in Immich Tags     |
| `--person` | Person's display name in Immich (exact, case-insensitive)|
| `--url`    | Base URL of your Immich instance                         |
| `--key`    | Immich API key                                           |

### Interactive mode

Run without arguments and the script will prompt for any missing values:

```bash
python unmatched_faces.py
```

### Credential files

To avoid typing the URL and API key every run, create either or both of these files in the working directory:

- **`url.txt`** — contains the Immich base URL (e.g. `http://192.168.1.10:2283`)
- **`api.txt`** — contains the Immich API key

The script reads these automatically and will only prompt interactively if the files are absent and the corresponding argument was not passed on the command line.

## Output

The script prints a summary of tagged vs. assigned assets and lists every photo that is tagged but missing from face recognition:

```
────────────────────────────────────────────────────────────
Tagged total  : 42
In person     : 35
Missing       : 7
────────────────────────────────────────────────────────────

Photos tagged but NOT assigned to the person:

  2021-06-14  IMG_1234.jpg                              http://192.168.1.10:2283/photos/<id>
  ...
```

At the end you are offered the option to save the results to a text file named `unmatched_<Person_Name>.txt`.

## Finding the correct tag and person values

- **Tag value**: Immich → Settings → Tags. Use the full hierarchical value, e.g. `People/Paul-McCartney`.
- **Person name**: Immich → Explore → People. Use the exact display name, e.g. `Paul McCartney`.
