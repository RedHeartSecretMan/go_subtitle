import os
import pkg_resources
from setuptools import setup, find_namespace_packages

setup(
    name="go_subtitle",
    py_modules=["subtitler"],
    version="0.0.2",
    license="MIT",
    
    python_requires='>=3.6',
    packages=find_namespace_packages(),
    install_requires=[
        str(r)
        for r in pkg_resources.parse_requirements(
            open(os.path.join(os.path.dirname(__file__), "requirements.txt"))
        )
    ],
    entry_points={
        'console_scripts': ['go_subtitle=subtitler.shell:main'],
    },
    include_package_data=True,
    
    author="HaoDaXia",
    author_email = "wh18307094479@gmail.com",
    description="Generate subtitle from audio or video file",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    readme="README.md",
    url="https://github.com/RedHeartSecretMan/go_subtitle",  
)