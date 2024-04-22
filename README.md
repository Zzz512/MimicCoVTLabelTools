

### How to build

Below shows how to build the standalone executable on macOS, Linux and Windows.  

```bash
# Git Clone
git clone https://github.com/Zzz512/MimicCoVTLabelTools.git

# Setup conda
conda create --name labelme-covt python=3.10
conda activate labelme-covt

# Build Dependency
pip install .

# Run
python ./labelme/__main__.py

# Build the standalone executable
pip install pyinstaller
pyinstaller labelme-covt.spec
dist/labelme --version
```

## Acknowledgement

This repo is the fork of [mpitid/pylabelme](https://github.com/mpitid/pylabelme).