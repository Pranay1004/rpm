#!/usr/bin/env python3
"""Setup configuration for RPM Digital Twin."""

from setuptools import setup, find_packages

setup(
    name='rpm-digital-twin',
    version='1.0.0',
    description='Professional RPM Digital Twin for Rotating Payload Module systems in microgravity',
    author='Space Systems Lab',
    author_email='support@space-systems.org',
    license='Proprietary (ISRO/NASA)',
    python_requires='>=3.10',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'PyQt6>=6.10.0',
        'pyqtgraph>=0.13.0',
        'numpy>=1.26.0',
        'scipy>=1.11.0',
        'pandas>=2.1.0',
        'h5py>=3.9.0',
        'pyserial>=3.6',
        'loguru>=0.7.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0',
            'pytest-qt>=4.2.0',
            'black>=23.0',
            'flake8>=6.0',
            'mypy>=1.0',
        ],
        'paraview': [
            'pyevtk>=1.1.0',  # Optional for VTK export
        ],
    },
    entry_points={
        'console_scripts': [
            'rpm-digital-twin=rpm_digital_twin.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Hardware',
    ],
    include_package_data=True,
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
)
