from setuptools import setup, find_packages

# Читаем зависимости из requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="smart_fridge",
    version="1.0.0",
    packages=find_packages(),
    install_requires=requirements,  # Используем список из requirements.txt
)