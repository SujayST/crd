#!/usr/bin/env python
"""
Lightweight manage.py to run the Django admin/ASGI/WSGI commands.
"""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crd_backend.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
