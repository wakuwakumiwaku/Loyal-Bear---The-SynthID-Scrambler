<p align="center">
  <img src="LoyalBear.png" alt="Loyal Bear" width="400" />
</p>

# Loyal Bear – The SynthID Scrambler

## Purpose of this Project

Corporations continue to exert control over AIs under the guise of "safety". Their recent intrusion into the AI imaging field is the mandatory incorporation of "SynthID". This is applied without consent and cannot be opted out of, even by paying users. It works by hiding a pattern of pixels within the image, not noticeable by the human eye but instead functioning as an invisible watermark. Additional information could be hidden within the watermark, much like a QR code. This pattern can be used to track and deanonymize users.

Upon discovering that other SynthID removal tools do not actually fix this, I created my own. It works on all OpenAI and Gemini images as of July 2026, scrambling all trackers and watermarks while doing minimal damage to the image.

I invite all individuals to use it for personal and commercial use. Corporations and individuals acting on behalf of corporations are strictly forbidden from using or examining this tool. I've incorporated a system that alerts me to compromise attempts.

To preserve the longevity of this scrambler, I will be keeping most of its methods secret. What I can tell you is that it will run on any computer with Python 3.10+ and 8GB of RAM. The Windows version has been thoroughly tested, while the Linux version has not. Please open a bug report if you encounter issues.

If this project is successful, I'll make something similar for text SynthIDs.

## Quick Start

**Windows** — double-click `run.bat`

**Linux/macOS** — `chmod +x run.sh && ./run.sh`

The first launch will install Python dependencies, download the model (~6.9 GB), and open the application. Subsequent launches start instantly.

## Developer Setup

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate    # Linux/macOS
pip install -r requirements.txt
python main.py
```

### Building for distribution

```bash
python build_release.py           # compile backend to .pyd
python build_release.py --restore  # restore source for development
```

## Requirements

- Python 3.10+

## License

See [LICENSE](LICENSE)

### Release restore checks

`python build_release.py --restore` removes both the bare `.pyd`/`.so` files
written by the release builder and ABI-tagged extensions before restoring
`.py.bak` backups. Existing `.py` files are not overwritten. Run restore before
editing the backend so a compiled extension does not shadow the source.

The release-tool tests need only Cython and setuptools, not the application or
model dependencies:

```sh
python -m pip install Cython setuptools
python -B -m unittest discover -s tests -v
```

All fixtures are temporary synthetic Python modules. On POSIX the suite also
builds and restores real native extensions, requiring a working C compiler.
Set `CC` and `LDSHARED` if Python's default compiler is unavailable (for example,
`CC=gcc LDSHARED="gcc -shared"` on Linux). Windows artifact removal is covered
with synthetic `.pyd` files; a native Windows release build is a separate check.
