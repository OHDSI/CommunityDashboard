#!/usr/bin/env python3
"""
Kill any existing ingestion processes to ensure clean slate.

Usage:
    docker-compose exec backend python /app/scripts/kill_ingestion_processes.py
"""

import os
import subprocess
import signal
import psutil

def kill_ingestion_processes():
    """Kill any running ingestion processes."""
    
    print("="*60)
    print("KILLING ANY EXISTING INGESTION PROCESSES")
    print("="*60)
    
    killed_count = 0
    
    # Find and kill Python processes related to ingestion
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    # Check if it's an ingestion-related process
                    if any(pattern in cmdline for pattern in ['ingest_', 'pipeline', 'fetch_', 'test_enriched']):
                        print(f"Found process PID {proc.info['pid']}: {cmdline[:100]}...")
                        
                        # Skip our own process
                        if proc.info['pid'] == os.getpid():
                            print("  (skipping self)")
                            continue
                        
                        # Kill the process
                        try:
                            proc.terminate()
                            proc.wait(timeout=3)
                            print(f"  ✅ Killed PID {proc.info['pid']}")
                            killed_count += 1
                        except psutil.TimeoutExpired:
                            proc.kill()
                            print(f"  ✅ Force-killed PID {proc.info['pid']}")
                            killed_count += 1
                        except Exception as e:
                            print(f"  ⚠️ Could not kill: {e}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        print(f"Error checking processes: {e}")
        print("Falling back to simpler method...")
        
        # Fallback method using ps and grep
        try:
            result = subprocess.run(
                "ps aux | grep -E 'python.*ingest_|python.*pipeline|python.*fetch' | grep -v grep | grep -v kill_ingestion",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                print("Found processes:")
                print(result.stdout)
                
                # Extract PIDs
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                            print(f"  ✅ Killed PID {pid}")
                            killed_count += 1
                        except Exception as e:
                            print(f"  ⚠️ Could not kill PID {pid}: {e}")
        except Exception as e:
            print(f"Fallback method failed: {e}")
    
    if killed_count == 0:
        print("✅ No ingestion processes found running")
    else:
        print(f"✅ Killed {killed_count} process(es)")
    
    # Try to purge Celery queues
    print("\nPurging Celery queues...")
    try:
        result = subprocess.run(
            ["celery", "-A", "app.workers.celery_app", "purge", "-f"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("  ✅ Celery queues purged")
        else:
            print("  ⚠️ Could not purge Celery queues:", result.stderr)
    except Exception as e:
        print(f"  ⚠️ Celery not accessible: {e}")
    
    # Clear lock files
    print("\nClearing lock files...")
    lock_patterns = ['/tmp/*.lock', '/app/logs/*.lock']
    for pattern in lock_patterns:
        try:
            import glob
            for lockfile in glob.glob(pattern):
                os.remove(lockfile)
                print(f"  Removed {lockfile}")
        except Exception:
            pass
    
    print("\n" + "="*60)
    print("✅ CLEAN SLATE READY FOR NEW INGESTION")
    print("="*60)
    print("\nYou can now run:")
    print("  1. Test script: python /app/scripts/test_enriched_citations.py")
    print("  2. Training data: python /app/scripts/ingest_training_data.py")
    print("  3. Multimodal: python /app/scripts/ingest_multimodal_content.py")


if __name__ == "__main__":
    kill_ingestion_processes()