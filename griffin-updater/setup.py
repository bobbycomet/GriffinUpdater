from setuptools import setup, find_packages

setup(
    name="griffin-updater",
    version="1.0.0",
    description="Griffin Updater - schedule-based .deb/AppImage updater with a shared app catalog",
    author="Bobby",
    packages=find_packages(include=["griffin_updater", "griffin_updater.*"]),
    include_package_data=True,
    install_requires=[
        "PyQt6>=6.6",
        "requests>=2.31",
    ],
    entry_points={
        "console_scripts": [
            "griffin-updater=griffin_updater.main:main",
            "griffin-updater-cli=griffin_updater.cli:main",
        ],
    },
    python_requires=">=3.10",
)
