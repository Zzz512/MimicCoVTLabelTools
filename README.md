# Hangzhou Dianzi University MIL CoVT Annotation Tool

### Get report json file
[Baiduyun download link](https://pan.baidu.com/s/1v2wt3CTd2MDnsr8ITOrn5g?pwd=hhdu)

### How to build

Below shows how to build the standalone executable on macOS, Linux and Windows.  

```bash
# Git Clone
git clone https://github.com/Zzz512/MimicCoVTLabelTools.git
cd MimicCoVTLabelTools

# Setup conda
conda create --name labelme-covt python=3.10
conda activate labelme-covt

# Build Dependency
pip install .

# Run
labelme or python ./labelme/__main__.py

# Build the standalone executable
pip install pyinstaller
pyinstaller labelme-covt.spec
dist/labelme --version
```

## Acknowledgement

This repo is the fork of [mpitid/pylabelme](https://github.com/mpitid/pylabelme).