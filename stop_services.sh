#!/bin/bash
echo "Stopping Bitcoin Reused-R Scanner services..."
kill $(cat backend_pid.txt) 2>/dev/null || true
kill $(cat frontend_pid.txt) 2>/dev/null || true
echo "Services stopped."
rm -f backend_pid.txt frontend_pid.txt
