from setuptools import setup, find_packages

setup(
    name="manhwa-compressor",
    version="0.1.0",
    description="High-speed Manhwa and Comic Compression Engine (CBZ & PDF)",
    packages=find_packages(),
    install_requires=[
        "Pillow>=10.0.0",
        "numpy>=1.24.0",
        "opencv-python>=4.8.0",
        "pymupdf>=1.23.0",
    ],
    entry_points={
        "console_scripts": [
            "manhwa-compress=src.cli:main",
        ],
    },
    python_requires=">=3.8",
)
