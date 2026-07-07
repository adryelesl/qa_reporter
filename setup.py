from setuptools import setup, find_packages

setup(
    name="qa_reporter",
    version="0.1.0",
    description="A reusable QA reporting library for Robot Framework results with Jira integration.",
    author="@adryelesl",
    package_dir={"": "src"},
    packages=["qa_reporter"],
    install_requires=[
        "robotframework",
        "matplotlib",
        "requests",
        "python-dotenv"
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "qa-reporter=qa_reporter.daily_report:main",
        ]
    },
)
