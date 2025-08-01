#!/usr/bin/env python

import ctypes.util
import os
from setuptools import setup
from setuptools import Extension
import platform

work_dir = os.path.dirname(os.path.realpath(__file__))
mod_dir = os.path.join(work_dir, 'src', 'confluent_kafka')
ext_dir = os.path.join(mod_dir, 'src')

# On Un*x the library is linked as -lrdkafka,
# while on windows we need the full librdkafka name.
if platform.system() == 'Windows':
    librdkafka_libname = 'librdkafka'
else:
    librdkafka_libname = 'rdkafka'

# Define the default module to build, without external dependencies.
module_defs = [
    {
        'name': 'confluent_kafka.cimpl.nodeps.cimpl',
        'libname': librdkafka_libname,
    }
]

# Check for GSSAPI support and add the appropriate module definitions.
if ctypes.util.find_library('rdkafka_sasl2_2'):
    module_defs.append(
        {
            'name': 'confluent_kafka.cimpl.sasl2_2.cimpl',
            'libname': 'rdkafka_sasl2_2',
        }
    )
if ctypes.util.find_library('rdkafka_sasl2_3'):
    module_defs.append(
        {
            'name': 'confluent_kafka.cimpl.sasl2_3.cimpl',
            'libname': 'rdkafka_sasl2_3',
        }
    )

setup(
    ext_modules=[
        Extension(
            mod_def['name'],
            libraries=[mod_def['libname']],
            sources=[
                os.path.join(ext_dir, 'confluent_kafka.c'),
                os.path.join(ext_dir, 'Producer.c'),
                os.path.join(ext_dir, 'Consumer.c'),
                os.path.join(ext_dir, 'Metadata.c'),
                os.path.join(ext_dir, 'AdminTypes.c'),
                os.path.join(ext_dir, 'Admin.c'),
            ],
        )
        for mod_def in module_defs
    ]
)
