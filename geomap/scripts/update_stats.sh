#!/bin/bash
cd /home/gdiaz/radar
source /home/gdiaz/envs/radar/bin/activate
python3.7 manage.py update_stats
