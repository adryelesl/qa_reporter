from setuptools import setup, find_packages

setup(
    name="qa_reporter",
    version="0.1.0",
    description="A reusable QA reporting library for Robot Framework results with Jira integration.",
    author="Adryel Souza Leite",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "robotframework",
        "matplotlib",
        "requests",
        "python-dotenv"
    ],
    python_requires=">=3.6",
)
