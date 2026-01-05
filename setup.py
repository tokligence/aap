from setuptools import setup, find_packages

setup(
    name="aap-mvp",
    version="0.1.0",
    description="Agent Authority Protocol (AAP) MVP control-plane CLI/API",
    author="Tokligence",
    python_requires=">=3.9",
    packages=find_packages(include=["aap", "aap.*"]),
    install_requires=["pyyaml>=6.0.0"],
    extras_require={
        "api": ["fastapi>=0.110.0", "uvicorn>=0.23.0"],
        "dev": ["pytest>=7.4.0", "fastapi>=0.110.0", "uvicorn>=0.23.0"],
    },
    entry_points={"console_scripts": ["aap=aap.cli:main"]},
    include_package_data=True,
    package_data={
        "aap": [
            "policies/*.yaml",
            "evidence/**/*",
            "hooks/pre-receive",
            "auth_allowlist.txt",
            "api_tokens.txt",
        ]
    },
    keywords=["agents", "governance", "authority", "control-plane", "cli"],
    license="Apache-2.0",
)
